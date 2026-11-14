"""Local evaluation harness (the regression gate before every submission).

Usage:
    python tools/evaluate.py                 # evaluates agent/agent.py
    python tools/evaluate.py path/to/agent.py

Reports, for two datasets, the agent score (4 decimals), the perfect-foresight LP upper
bound, the gap, infractions and runtime:
  * train-full  : all train hours concatenated (5993 h)
  * pseudo-test : last 168 contiguous hours of each train month, concatenated -> same
                  structure as the hidden test (weekly blocks with month-long time jumps)
"""
import sys
import time
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter_kit"))
from environment import CampusBatteryEnv  # noqa: E402

ETA = 0.9 ** 0.5


def load_hourly():
    return pd.read_csv(ROOT / "data" / "hourly_train.csv", parse_dates=["Fecha"]).set_index("Fecha")


def pseudo_test(df):
    parts = []
    for _, g in df.groupby(df.index.to_period("M")):
        g = g.iloc[-168:]
        if len(g) == 168 and (g.index[-1] - g.index[0]) == pd.Timedelta(hours=167):
            parts.append(g)
    return pd.concat(parts)


def load_agent(path):
    spec = importlib.util.spec_from_file_location("agent_under_test", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.BatteryAgent


def precise_score(df, grid):
    net = (df.load_kw - df.pv_kw).values
    b = np.maximum(net, 0.0)
    pr, co = df.precio_eur_per_kwh.values, df.co2_kg_per_kwh.values
    dco2 = 1 - (grid * co).sum() / (b * co).sum()
    dcost = 1 - (grid * pr).sum() / (b * pr).sum()
    return 100 * (0.7 * dco2 + 0.3 * dcost), 100 * dco2, 100 * dcost


def run_agent(agent_cls, df):
    env = CampusBatteryEnv(df)
    obs = env.reset()
    agent = agent_cls()
    done = False
    t0 = time.time()
    while not done:
        obs, done = env.step(agent.act(obs))
    secs = time.time() - t0
    s, dco2, dcost = precise_score(df, np.asarray(env.grid))
    return {"score": s, "dco2": dco2, "dcost": dcost, "infr": env.clipped + env.violations,
            "secs": secs, "fallbacks": getattr(agent, "n_fallback", None), "env": env}


def perfect_foresight(df):
    """Upper bound: LP with full knowledge of the whole series (exact weights of this dataset)."""
    net = (df.load_kw - df.pv_kw).values
    n = len(df)
    b = np.maximum(net, 0.0)
    pr, co = df.precio_eur_per_kwh.values, df.co2_kg_per_kwh.values
    w = 0.7 * co / ((b * co).sum() / b.sum()) + 0.3 * pr / ((b * pr).sum() / b.sum())
    eye = sparse.identity(n, format="csr")
    zero = sparse.csr_matrix((n, n))
    lag = sparse.diags([np.ones(n), -np.ones(n - 1)], [0, -1], format="csr")
    b_eq = np.zeros(n)
    b_eq[0] = 1000.0
    res = linprog(np.concatenate([np.zeros(2 * n), w, np.zeros(n)]),
                  A_ub=sparse.hstack([eye, -eye, -eye, zero]), b_ub=-net,
                  A_eq=sparse.hstack([-ETA * eye, eye / ETA, zero, lag]), b_eq=b_eq,
                  bounds=[(0, 500)] * (2 * n) + [(0, None)] * n + [(0, 2000)] * n, method="highs")
    return precise_score(df, res.x[2 * n:3 * n])[0]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "agent" / "agent.py"
    agent_cls = load_agent(path.resolve())
    df = load_hourly()
    print(f"agent: {path}")
    for name, d in [("train-full", df), ("pseudo-test", pseudo_test(df))]:
        r = run_agent(agent_cls, d)
        pf = perfect_foresight(d)
        per2016 = r["secs"] * 2016 / len(d)
        print(f"{name:11s} n={len(d):5d} score={r['score']:.4f} (dCO2 {r['dco2']:.3f}% dCost {r['dcost']:.3f}%) "
              f"PF={pf:.4f} gap={pf - r['score']:.4f} infr={r['infr']} fallbacks={r['fallbacks']} "
              f"time={r['secs']:.1f}s (~{per2016:.1f}s per 2016 steps)")


if __name__ == "__main__":
    main()
