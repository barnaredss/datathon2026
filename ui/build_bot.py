"""Builds ui/bot.html: the "Volta" bot page, with three example weeks simulated by the hard-mode agent.

Usage: ./.venv/Scripts/python.exe -m ui.build_bot
Data: official training data only (data/train), hard-mode simulator from tools/hard.py, agent hard_v6.
"""
import json
import warnings

import numpy as np
import pandas as pd

from tools.hard import load_hard, load_module, run_agent, precise_score, perfect_foresight, ROOT, PV_SCALE

warnings.filterwarnings("ignore")

WEEKS = [
    ("mayo", "Mayo · mucho sol", "2026-05-18"),
    ("pascua", "Semana Santa · campus a medio gas", "2026-04-01"),
    ("diciembre", "Diciembre · poco sol", "2025-12-18"),
]
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def week_payload(df, start, mod):
    idx = pd.date_range(start, periods=168, freq="h")
    d = df.loc[idx]
    r = run_agent(mod.BatteryAgent, d, n_total=168)
    env = r["env"]
    act = np.asarray(env.actions, dtype=float)
    soc = np.asarray(env.soc_series, dtype=float)
    grid = np.asarray(env.grid, dtype=float)
    load = d.load_kw.values
    pv = PV_SCALE * d.pv_kw.values
    net = load - pv
    base = np.maximum(net, 0)
    pr, co = d.precio_eur_per_kwh.values, d.co2_kg_per_kwh.values
    lam = float(mod.PROFILES["lambda"])
    w = co + lam * pr
    surplus = np.maximum(-net, 0)
    stored = np.minimum(np.maximum(act, 0), surplus)
    pf = perfect_foresight(d)
    hours = []
    for i, t in enumerate(idx):
        hours.append({
            "d": DIAS[t.weekday()], "dd": t.strftime("%d/%m"), "h": t.hour,
            "load": round(float(load[i])), "pv": round(float(pv[i])), "net": round(float(net[i])),
            "p": round(float(pr[i]), 4), "c": round(float(co[i]), 4), "w": round(float(w[i]), 4),
            "a": round(float(act[i])), "soc": round(float(soc[i])), "g": round(float(grid[i])),
            "co2": round(float((base[i] - grid[i]) * co[i]), 2), "eur": round(float((base[i] - grid[i]) * pr[i]), 2),
            "sol": round(float(stored[i])),
        })
    return {"hours": hours, "score": round(r["score"], 2), "pf": round(pf, 2), "infr": int(r["infr"]),
            "kg": round(float(((base - grid) * co).sum())), "eur": round(float(((base - grid) * pr).sum())),
            "solar_mwh": round(float(stored.sum()) / 1000, 1), "surplus_mwh": round(float(surplus.sum()) / 1000, 1)}


def main():
    df = load_hard()
    mod = load_module(ROOT / "submissions" / "hard_v6" / "agent.py")
    data = {"weeks": [], "lambda": float(mod.PROFILES["lambda"])}
    for key, label, start in WEEKS:
        p = week_payload(df, start, mod)
        p.update({"key": key, "label": label})
        data["weeks"].append(p)
        print("%-10s score %.2f (PF %.2f) kg %d eur %d solar %.1f MWh" % (key, p["score"], p["pf"], p["kg"], p["eur"], p["solar_mwh"]))
    src = (ROOT / "ui" / "bot_src.html").read_text(encoding="utf-8")
    assert src.count("/*__DATA__*/") == 1
    out = src.replace("/*__DATA__*/", "const DATA = " + json.dumps(data, separators=(",", ":"), ensure_ascii=False) + ";")
    (ROOT / "ui" / "bot.html").write_text(out, encoding="utf-8", newline="\n")
    print("wrote ui/bot.html (%.0f KB)" % (len(out.encode("utf-8")) / 1024))
    nl = chr(10)
    head = nl.join(['<!doctype html>', '<html lang="es">', '<head>', '<meta charset="utf-8">',
                    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
                    '<style>body{margin:0}</style>', '</head>', '<body>', ''])
    tail = nl.join(['', '</body>', '</html>', ''])
    (ROOT / "ui" / "bot_local.html").write_text(head + out + tail, encoding="utf-8", newline=nl)
    print("wrote ui/bot_local.html (open it in any browser, works offline except fonts)")


if __name__ == "__main__":
    main()
