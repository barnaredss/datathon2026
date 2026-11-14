"""Hard Mode ("Mode Difícil") local harness.

Hard mode = battery 6,000 kWh / ±1,500 kW, PV x12, only 3 h of price/CO2 in obs, weather of the
last hour in obs["noves_dades_5min"], obs["cap_max_kwh"], obs["power_max_kw"].

Usage:
    python -m tools.hard build            # data/hourly_hard.csv (hourly_train + hourly weather)
    python -m tools.hard                  # evaluate agent_hard/agent.py (train-full + pseudo-test)
    python -m tools.hard path/to/agent.py

API: load_hard(), pseudo_test(df), compute_profiles(df, pk), HardEnv, run_agent(module_or_cls, df,
profiles=None), perfect_foresight(df), precise_score(df, grid), load_module(path).
Profiles used on pseudo-test are computed WITHOUT the pseudo-test rows (out of sample).
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

PV_SCALE = 12.0
SPEC_HARD = {"capacity_kwh": 6000.0, "power_kw": 1500.0, "efficiency": 0.90, "soc_init": 0.50,
             "soc_min": 0.0, "soc_max": 1.0, "dt_hours": 1.0, "forecast_horizon": 3}
ETA = 0.9 ** 0.5
METEO = {"Atersa - IRRADIANCIA (W/m2)": "irr", "Atersa - TEMPERATURA AMBIENTE (SENSOR 1) (ºC)": "tamb",
         "Atersa - TEMPERATURA PANEL (SENSOR 1) (ºC)": "tpanel", "Atersa - VELOCIDAD VIENTO (SENSOR 1) (m/s)": "wind"}


def build():
    base = pd.read_csv(ROOT / "data" / "hourly_train.csv", parse_dates=["Fecha"]).set_index("Fecha")
    m = pd.read_csv(ROOT / "data" / "train" / "meteo.csv", usecols=["Fecha"] + list(METEO), parse_dates=["Fecha"])
    m = m.set_index("Fecha").rename(columns=METEO).resample("1h").mean()
    df = base.join(m, how="left")
    df[list(METEO.values())] = df[list(METEO.values())].ffill().fillna(0.0)
    df.to_csv(ROOT / "data" / "hourly_hard.csv")
    print(f"hourly_hard.csv: {len(df)} h, weather NaN left: {int(df.isna().sum().sum())}")


def load_hard():
    return pd.read_csv(ROOT / "data" / "hourly_hard.csv", parse_dates=["Fecha"]).set_index("Fecha")


def load_price_co2():
    return pd.read_csv(ROOT / "data" / "hourly_price_co2.csv", parse_dates=["Fecha"]).set_index("Fecha")


def pseudo_test(df):
    parts = []
    for _, g in df.groupby(df.index.to_period("M")):
        g = g.iloc[-168:]
        if len(g) == 168 and (g.index[-1] - g.index[0]) == pd.Timedelta(hours=167):
            parts.append(g)
    return pd.concat(parts)


def compute_profiles(df, pk):
    """Climatology the agent embeds. df: hourly load/pv rows; pk: hourly price/co2 rows."""
    out = {}
    for name, col in (("price", "precio_eur_per_kwh"), ("co2", "co2_kg_per_kwh")):
        arr = np.full((12, 2, 24), np.nan)
        g = pk[col].groupby([pk.index.month, (pk.index.dayofweek >= 5).astype(int), pk.index.hour]).mean()
        for (mo, dt, h), v in g.items():
            arr[mo - 1, dt, h] = v
        hour_mean = np.nanmean(arr, axis=(0, 1))
        for mo in range(12):
            for dt in range(2):
                bad = np.isnan(arr[mo, dt])
                alt = arr[mo, 1 - dt]
                arr[mo, dt, bad] = np.where(np.isnan(alt[bad]), hour_mean[bad], alt[bad])
        out[name] = np.round(arr, 5).tolist()
    pv = np.full((12, 24), np.nan)
    for (mo, h), v in df["pv_kw"].groupby([df.index.month, df.index.hour]).mean().items():
        pv[mo - 1, h] = v
    lm = np.full(12, np.nan)
    for mo, v in df["load_kw"].groupby(df.index.month).mean().items():
        lm[mo - 1] = v
    for mo in range(12):                      # months without sensor data: average of neighbours
        if np.isnan(lm[mo]):
            a, b = (mo - 1) % 12, (mo + 1) % 12
            pv[mo] = (pv[a] + pv[b]) / 2
            lm[mo] = (lm[a] + lm[b]) / 2
    out["pv"] = np.round(pv, 2).tolist()
    out["load_month"] = np.round(lm, 1).tolist()
    wk = df["load_kw"].groupby(df.index.dayofweek * 24 + df.index.hour).mean().reindex(range(168)).interpolate()
    out["load_week"] = np.round(wk.values, 1).tolist()
    b = np.maximum(df["load_kw"] - PV_SCALE * df["pv_kw"], 0.0)
    out["lambda"] = round(float((0.3 / 0.7) * (b * df["co2_kg_per_kwh"]).sum() / (b * df["precio_eur_per_kwh"]).sum()), 4)
    out["ridge"] = fit_signal_ridge(pk, out)
    pre = {}                                  # last 48 h of each month: history for the day before a test week
    for _, g in pk.groupby(pk.index.to_period("M")):
        for ts, row in g.iloc[-48:].iterrows():
            has = ts in df.index
            pre[ts.strftime("%Y-%m-%d %H")] = [round(float(row.precio_eur_per_kwh), 5), round(float(row.co2_kg_per_kwh), 5),
                                               round(float(df.at[ts, "load_kw"]), 1) if has else None,
                                               round(float(df.at[ts, "pv_kw"]), 2) if has else None] + (
                [round(float(df.at[ts, c]), 2) for c in ("irr", "tpanel", "tamb", "wind")] if has else [None] * 4)
    out["prehist"] = pre
    out["pv_gbm"] = fit_pv_gbm(df, out)
    return out


RIDGE_FEATS = ["k", "hod", "wkend", "mo", "hod0", "pos", "p2", "p1", "p0", "p6", "p24",
               "c2", "c1", "c0", "c6", "c24", "py", "cy", "dpy", "dcy", "py2", "cy2"]


def signal_samples(pk, prof):
    """Samples (origin n, lead k=3..23) of price/CO2 RATIOS to climatology, built inside contiguous blocks.
    The agent rebuilds exactly these features online (see agent_hard/agent.py::_ridge_features)."""
    P, C = np.array(prof["price"]), np.array(prof["co2"])
    idx = pk.index
    mo, dt, hod = idx.month.values - 1, (idx.dayofweek.values >= 5).astype(int), idx.hour.values
    rp = pk.precio_eur_per_kwh.values / P[mo, dt, hod]
    rc = pk.co2_kg_per_kwh.values / C[mo, dt, hod]
    gap = np.r_[True, (np.diff(idx.values).astype("timedelta64[h]").astype(int) != 1)]
    blk = np.cumsum(gap)
    pos = np.arange(len(idx)) - np.flatnonzero(gap)[blk - 1]
    X, yp, yc = [], [], []
    for n in range(len(idx) - 2):
        if blk[n + 2] != blk[n]:
            continue
        b0 = n - pos[n]
        lo6, lo24 = max(n - 3, b0), max(n - 21, b0)
        p6, p24 = rp[lo6:n + 3].mean(), rp[lo24:n + 3].mean()
        c6, c24 = rc[lo6:n + 3].mean(), rc[lo24:n + 3].mean()
        d_ok = pos[n + 2] >= 24
        dpy = rp[n + 2] - rp[n + 2 - 24] if d_ok else 0.0
        dcy = rc[n + 2] - rc[n + 2 - 24] if d_ok else 0.0
        for k in range(3, 24):
            r = n + k
            if r >= len(idx) or blk[r] != blk[n]:
                break
            y1, y2 = pos[r] >= 24, pos[r] >= 48
            X.append([k, hod[r], dt[r], mo[r], hod[n], min(pos[n], 48),
                      rp[n + 2], rp[n + 1], rp[n], p6, p24, rc[n + 2], rc[n + 1], rc[n], c6, c24,
                      rp[r - 24] if y1 else p24, rc[r - 24] if y1 else c24, dpy, dcy,
                      rp[r - 48] if y2 else p24, rc[r - 48] if y2 else c24])
            yp.append(rp[r])
            yc.append(rc[r])
    return np.asarray(X), np.asarray(yp), np.asarray(yc)


def fit_signal_ridge(pk, prof, alpha=3.0):
    from sklearn.linear_model import Ridge
    X, yp, yc = signal_samples(pk, prof)
    out = {"coef_p": [], "icpt_p": [], "coef_c": [], "icpt_c": []}
    for k in range(3, 24):
        a = X[:, 0] == k
        for tgt, name in ((yp, "p"), (yc, "c")):
            m = Ridge(alpha=alpha).fit(X[a], tgt[a])
            out["coef_" + name].append(np.round(m.coef_, 6).tolist())
            out["icpt_" + name].append(round(float(m.intercept_), 6))
    return out


class HardEnv(CampusBatteryEnv):
    def __init__(self, df):
        self._meteo = df[["irr", "tamb", "tpanel", "wind"]].values
        d = df[["load_kw", "pv_kw", "precio_eur_per_kwh", "co2_kg_per_kwh"]].copy()
        d["pv_kw"] = d["pv_kw"] * PV_SCALE
        super().__init__(d, spec=dict(SPEC_HARD))

    def _get_obs(self):
        obs = super()._get_obs()
        if obs is None:
            return None
        obs["preus_properes_24h"] = obs["preus_properes_24h"][:3]
        obs["co2_properes_24h"] = obs["co2_properes_24h"][:3]
        i = self.t - 1 if self.t > 0 else self.t
        irr, tamb, tpanel, wind = (float(x) for x in self._meteo[i])
        obs["noves_dades_5min"].update({"irradiancia_wm2": irr, "temp_ambient_c": tamb,
                                        "temp_panel_c": tpanel, "vent_ms": wind})
        obs["cap_max_kwh"] = float(self.cap)
        obs["power_max_kw"] = float(self.power)
        return obs


def precise_score(df, grid):
    net = (df.load_kw - PV_SCALE * df.pv_kw).values
    b = np.maximum(net, 0.0)
    pr, co = df.precio_eur_per_kwh.values, df.co2_kg_per_kwh.values
    dco2 = 1 - (grid * co).sum() / (b * co).sum()
    dcost = 1 - (grid * pr).sum() / (b * pr).sum()
    return 100 * (0.7 * dco2 + 0.3 * dcost), 100 * dco2, 100 * dcost


def load_module(path):
    spec = importlib.util.spec_from_file_location("hard_agent_under_test", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_agent(agent_cls, df, n_total=None):
    env = HardEnv(df)
    obs = env.reset()
    agent = agent_cls()
    if hasattr(agent, "N_TOTAL"):
        agent.N_TOTAL = len(df) if n_total is None else n_total
    done = False
    t0 = time.time()
    while not done:
        obs, done = env.step(agent.act(obs))
    secs = time.time() - t0
    s, dco2, dcost = precise_score(df, np.asarray(env.grid))
    return {"score": s, "dco2": dco2, "dcost": dcost, "infr": env.clipped + env.violations, "secs": secs,
            "fallbacks": getattr(agent, "n_fallback", None), "env": env, "exports": float(np.sum(env.exports))}


def perfect_foresight(df, cap=6000.0, power=1500.0, return_grid=False):
    net = (df.load_kw - PV_SCALE * df.pv_kw).values
    n = len(df)
    b = np.maximum(net, 0.0)
    pr, co = df.precio_eur_per_kwh.values, df.co2_kg_per_kwh.values
    w = 0.7 * co / ((b * co).sum() / b.sum()) + 0.3 * pr / ((b * pr).sum() / b.sum())
    eye = sparse.identity(n, format="csr")
    zero = sparse.csr_matrix((n, n))
    lag = sparse.diags([np.ones(n), -np.ones(n - 1)], [0, -1], format="csr")
    b_eq = np.zeros(n)
    b_eq[0] = cap / 2
    res = linprog(np.concatenate([np.zeros(2 * n), w, np.zeros(n)]),
                  A_ub=sparse.hstack([eye, -eye, -eye, zero]), b_ub=-net,
                  A_eq=sparse.hstack([-ETA * eye, eye / ETA, zero, lag]), b_eq=b_eq,
                  bounds=[(0, power)] * (2 * n) + [(0, None)] * n + [(0, cap)] * n, method="highs")
    g = res.x[2 * n:3 * n]
    return (precise_score(df, g)[0], g) if return_grid else precise_score(df, g)[0]


def datasets():
    """[(name, df, profiles)] — pseudo-test profiles are out of sample."""
    df, pk = load_hard(), load_price_co2()
    pt = pseudo_test(df)
    months = sorted({(t.year, t.month) for t in pt.index})
    pk_rest = pk.drop(pk.index.intersection(pt.index))
    return [("train-full", df, compute_profiles(df, pk)),
            ("pseudo-test", pt, compute_profiles(df.drop(pt.index), pk_rest))], months


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        return build()
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "agent_hard" / "agent.py"
    mod = load_module(path.resolve())
    sets, _ = datasets()
    print(f"agent: {path}")
    for name, d, prof in sets[::-1]:
        mod.PROFILES = prof
        r = run_agent(mod.BatteryAgent, d)
        pf = perfect_foresight(d)
        print(f"{name:11s} n={len(d):5d} score={r['score']:.3f} (dCO2 {r['dco2']:.2f}% dCost {r['dcost']:.2f}%) "
              f"PF={pf:.3f} ({100 * r['score'] / pf:.1f}%) infr={r['infr']} fallbacks={r['fallbacks']} "
              f"exports={r['exports']:.0f} kWh time={r['secs']:.1f}s (~{r['secs'] * 2016 / len(d):.1f}s/2016)", flush=True)



PV_GBM_FEATS = ["pv1", "pv2", "pv24", "pvp", "pvp1", "cl1", "cl2", "irr1", "irr2", "tp1", "ta1", "wind1",
                "rc0", "rc1", "hod", "mo", "pers"]


def pv_nowcast_samples(df, prof):
    """Features for the CURRENT-hour solar nowcast (missing = -1). The agent rebuilds them online
    in agent_hard/agent.py::_pv_nowcast; keep both in sync."""
    PV, C = np.array(prof["pv"]), np.array(prof["co2"])
    idx = df.index
    mo, hod = idx.month.values - 1, idx.hour.values
    dt = (idx.dayofweek.values >= 5).astype(int)
    pvp = PV[mo, hod] * PV_SCALE
    pv = df.pv_kw.values * PV_SCALE
    rc = df.co2_kg_per_kwh.values / C[mo, dt, hod]
    gap = np.r_[True, (np.diff(idx.values).astype("timedelta64[h]").astype(int) != 1)]
    blk = np.cumsum(gap)

    def lag(a, k):
        out = np.full(len(a), np.nan)
        out[k:] = a[:-k]
        out[~np.r_[np.zeros(k, bool), blk[k:] == blk[:-k]]] = np.nan
        return out

    rc1 = np.r_[rc[1:], np.nan]
    rc1[np.r_[blk[1:] != blk[:-1], True]] = np.nan
    F = pd.DataFrame({"pv1": lag(pv, 1), "pv2": lag(pv, 2), "pv24": lag(pv, 24), "pvp": pvp, "pvp1": lag(pvp, 1),
                      "irr1": lag(df.irr.values, 1), "irr2": lag(df.irr.values, 2), "tp1": lag(df.tpanel.values, 1),
                      "ta1": lag(df.tamb.values, 1), "wind1": lag(df.wind.values, 1), "rc0": rc, "rc1": rc1,
                      "hod": hod.astype(float), "mo": mo.astype(float)})
    pvp2 = lag(pvp, 2)
    F["cl1"] = (F.pv1 / F.pvp1).clip(0, 2.5).where(F.pvp1 > 60)
    F["cl2"] = (F.pv2 / pvp2).clip(0, 2.5).where(pvp2 > 60)
    F["pers"] = F.pvp * F.cl1.fillna(1.0)
    ok = ((pvp > 30) & F.pv1.notna()).values
    return F[PV_GBM_FEATS].fillna(-1.0).values, pv, ok


def _flatten_tree(node, feat, thr, left, right, val):
    i = len(feat)
    feat.append(-1); thr.append(0.0); left.append(-1); right.append(-1); val.append(0.0)
    if "leaf_value" in node:
        val[i] = round(float(node["leaf_value"]), 5)
        return i
    assert node["decision_type"] == "<="
    feat[i] = int(node["split_feature"]); thr[i] = float(node["threshold"])
    left[i] = _flatten_tree(node["left_child"], feat, thr, left, right, val)
    right[i] = _flatten_tree(node["right_child"], feat, thr, left, right, val)
    return i


def gbm_predict(trees, x):
    s = 0.0
    for feat, thr, left, right, val in trees:
        i = 0
        while feat[i] >= 0:
            i = left[i] if x[feat[i]] <= thr[i] else right[i]
        s += val[i]
    return s


def fit_pv_gbm(df, prof, rounds=150, leaves=16, lr=0.08):
    import lightgbm as lgb
    X, y, ok = pv_nowcast_samples(df, prof)
    m = lgb.train(dict(objective="l1", learning_rate=lr, num_leaves=leaves, min_data_in_leaf=25, feature_fraction=0.8,
                       lambda_l2=1.0, verbose=-1, seed=7, deterministic=True, force_row_wise=True),
                  lgb.Dataset(X[ok], y[ok]), num_boost_round=rounds)
    trees = []
    for t in m.dump_model()["tree_info"]:
        arrs = ([], [], [], [], [])
        _flatten_tree(t["tree_structure"], *arrs)
        trees.append([list(a) for a in arrs])
    chk = X[ok][:300]
    diff = max(abs(gbm_predict(trees, r) - v) for r, v in zip(chk, m.predict(chk)))
    assert diff < 0.05, "hand-rolled tree evaluation disagrees with lightgbm: %.4f" % diff
    return trees


if __name__ == "__main__":
    main()
