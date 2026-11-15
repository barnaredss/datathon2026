"""Modo difícil: escalera de mejoras, descomposición con oráculos y despacho por hora.

Todo sobre el pseudo-test (10 semanas, 1.680 h) con perfiles y modelos ajustados SIN esas semanas.
Genera figures/hard_escalera.png, figures/hard_horas.png y analysis/cache/hard_results.json.

Uso:  ./.venv/Scripts/python.exe -m analysis.hard_study [--recompute]
"""
import json
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog

from analysis.style import apply, COLORS, save
from tools.hard import datasets, load_module, run_agent, perfect_foresight, HardEnv, precise_score, ROOT, PV_SCALE, ETA

warnings.filterwarnings("ignore")
CACHE = ROOT / "analysis" / "cache" / "hard_results.json"


def compute():
    mod = load_module(ROOT / "agent_hard" / "agent.py")
    sets, _ = datasets()
    _, d, prof = sets[1]
    mod.PROFILES = prof
    A = mod.BatteryAgent
    pr, co = d.precio_eur_per_kwh.values, d.co2_kg_per_kwh.values
    net = (d.load_kw - PV_SCALE * d.pv_kw).values
    pvx = PV_SCALE * d.pv_kw.values
    N = len(d)

    class OSig(A):
        def _signal(self, m):
            idx = np.minimum(np.arange(self.n, self.n + m), N - 1)
            return self.SCALE * (co[idx] + self.lam * pr[idx])

    class ONet0(A):
        NEWSVENDOR = False; DISCHARGE_MARGIN = 1.0; PV_UNCERT = 0.0

        def _net_load(self, m):
            x = super()._net_load(m)
            x[0] = net[self.n]; self._pv0 = pvx[self.n]
            return x

    class OBoth(OSig, ONet0):
        pass

    out = {"n_hours": N}
    out["pf"] = perfect_foresight(d)
    # plantilla oficial (pensada para 2.000 kWh / 500 kW) en el entorno difícil
    tmpl = load_module(ROOT / "starter_kit" / "agent.py").BatteryAgent
    r = run_agent(tmpl, d); out["plantilla"] = r["score"]; out["plantilla_infr"] = int(r["infr"])
    steps = [("perfiles", dict(USE_RIDGE=False, USE_PV_GBM=False, NEWSVENDOR=False, DISCHARGE_MARGIN=1.0, PV_UNCERT=0.0, PV_FACTOR=1.0)),
             ("regresion", dict(USE_PV_GBM=False, NEWSVENDOR=False, DISCHARGE_MARGIN=1.0, PV_UNCERT=0.0, PV_FACTOR=1.0)),
             ("prudencia", dict(USE_PV_GBM=False)),
             ("nuestro", dict())]
    for name, kw in steps:
        r = run_agent(type("V", (A,), kw), d)
        out[name] = r["score"]; out[name + "_infr"] = int(r["infr"])
        if name == "nuestro":
            out["dco2"], out["dcost"], out["exports_kwh"] = r["dco2"], r["dcost"], r["exports"]
            out["secs_2016"] = r["secs"] * 2016 / N
            act = np.asarray(r["env"].actions)
    for name, cls in (("o_senal", OSig), ("o_neta", ONet0), ("o_ambas", OBoth)):
        out[name] = run_agent(cls, d)["score"]
    # plan con información perfecta (acciones por hora)
    n = N; b = np.maximum(net, 0)
    w = 0.7 * co / ((b * co).sum() / b.sum()) + 0.3 * pr / ((b * pr).sum() / b.sum())
    eye = sparse.identity(n, format="csr"); zero = sparse.csr_matrix((n, n))
    lag = sparse.diags([np.ones(n), -np.ones(n - 1)], [0, -1], format="csr")
    b_eq = np.zeros(n); b_eq[0] = 3000.0
    res = linprog(np.concatenate([np.zeros(2 * n), w, np.zeros(n)]), A_ub=sparse.hstack([eye, -eye, -eye, zero]), b_ub=-net,
                  A_eq=sparse.hstack([-ETA * eye, eye / ETA, zero, lag]), b_eq=b_eq,
                  bounds=[(0, 1500)] * (2 * n) + [(0, None)] * n + [(0, 6000)] * n, method="highs")
    apf = res.x[:n] - res.x[n:2 * n]
    h = d.index.hour.values
    out["by_hour"] = {"agent": pd.Series(act).groupby(h).mean().round(1).tolist(),
                      "pf": pd.Series(apf).groupby(h).mean().round(1).tolist(),
                      "net": pd.Series(net).groupby(h).mean().round(1).tolist()}
    out["surplus_kwh"] = float(np.maximum(-net, 0).sum())
    out["share_hours_surplus"] = float((net < 0).mean())
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def es(x, nd=2):
    return ("%.*f" % (nd, x)).replace(".", ",")


def plot(R):
    apply()
    import matplotlib.pyplot as plt
    pf = R["pf"]
    rows = [("Plantilla oficial", R["plantilla"], COLORS["base"]),
            ("Perfiles medios (sin modelos)", R["perfiles"], COLORS["base"]),
            ("+ regresión de precio y CO2", R["regresion"], COLORS["precio"]),
            ("+ prudencia al descargar", R["prudencia"], COLORS["precio"]),
            ("+ previsión solar de la hora (nuestro)", R["nuestro"], COLORS["nuestro"]),
            ("Si conociéramos precio y CO2 a 24 h", R["o_senal"], COLORS["optimo"]),
            ("Si conociéramos la demanda neta de la hora", R["o_neta"], COLORS["optimo"]),
            ("Si conociéramos ambas", R["o_ambas"], COLORS["optimo"]),
            ("Información perfecta (cota)", pf, COLORS["optimo"])]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = np.arange(len(rows))[::-1]
    ax.barh(y, [r[1] for r in rows], color=[r[2] for r in rows], height=0.7)
    for yi, (_, v, _) in zip(y, rows):
        ax.text(v + 0.15, yi, "%s  (%s %%)" % (es(v), es(100 * v / pf, 1)), va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=8)
    ax.set_xlim(0, pf * 1.22); ax.set_xlabel("Score en semanas tipo test (entre paréntesis: % de la cota)")
    ax.set_title("Modo difícil: 93 % de la cota solo con previsiones", fontsize=13)
    ax.grid(axis="y", visible=False)
    save(fig, "hard_escalera")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    hrs = np.arange(24)
    ax.bar(hrs - 0.2, R["by_hour"]["pf"], width=0.4, color=COLORS["optimo"], label="Información perfecta")
    ax.bar(hrs + 0.2, R["by_hour"]["agent"], width=0.4, color=COLORS["nuestro"], label="Nuestro agente (solo previsiones)")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(range(0, 24, 3)); ax.set_xlabel("Hora del día")
    ax.set_ylabel("Potencia media de la batería (kW)\n(+ carga, − descarga)")
    ax.set_title("El agente opera casi como si conociera el futuro", fontsize=13)
    ax.legend(loc="upper left", fontsize=8)
    save(fig, "hard_horas")


if __name__ == "__main__":
    R = compute() if ("--recompute" in sys.argv or not CACHE.exists()) else json.loads(CACHE.read_text(encoding="utf-8"))
    plot(R)
    print("PF %.3f | plantilla %.3f | perfiles %.3f | regresion %.3f | prudencia %.3f | nuestro %.3f | o_senal %.3f | o_neta %.3f | o_ambas %.3f" % (
        R["pf"], R["plantilla"], R["perfiles"], R["regresion"], R["prudencia"], R["nuestro"], R["o_senal"], R["o_neta"], R["o_ambas"]))
    print("infr nuestro %d | exports %.0f kWh of surplus %.0f | hours with surplus %.1f%% | %.1f s per 2016 h" % (
        R["nuestro_infr"], R["exports_kwh"], R["surplus_kwh"], 100 * R["share_hours_surplus"], R["secs_2016"]))
