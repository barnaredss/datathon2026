"""Evidencia de la estrategia: escalera de referencias, horizonte, Pareto, semana y horas.

Uso (desde la raiz del repo):
    ./.venv/Scripts/python.exe -m analysis.strategy [--recompute]
Etapa 1: simula todo y guarda cada numero en analysis/cache/strategy_results.json.
Etapa 2: dibuja las figuras est_*.png y escribe analysis/strategy_findings.md a partir del JSON.
"""
import json
import sys
import time

import numpy as np
import pandas as pd

from tools.evaluate import (ROOT, load_hourly, pseudo_test, load_agent, run_agent,
                            perfect_foresight, precise_score, CampusBatteryEnv)

CACHE = ROOT / "analysis" / "cache" / "strategy_results.json"
FINDINGS = ROOT / "analysis" / "strategy_findings.md"
ANNUAL = 8760.0 / 5993.0
HORIZONS = [1, 2, 4, 6, 8, 12, 18, 24]
LAMBDAS = [0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.2593, 0.35, 0.5, 0.75, 1, 1.5, 2, 3, 5]
ETA = 0.9 ** 0.5


# ----------------------------------------------------------------------------- etapa 1
def stage1():
    df = load_hourly()
    dfs = {"train": df, "pseudo": pseudo_test(df)}
    base = load_agent(ROOT / "agent" / "agent.py")
    tmpl = load_agent(ROOT / "starter_kit" / "agent.py")

    def variant(**kw):
        return type("V", (base,), kw)

    class PriceOnly(base):
        def _signal(self, obs):
            return self.SCALE * np.asarray(obs["preus_properes_24h"], dtype=float)

    def horizon(h):
        class Hz(base):
            def _signal(self, obs):
                return base._signal(self, obs)[:h]
        return Hz

    def summary(r, penal=True):
        infr = int(r["infr"])
        return {"score": r["score"], "dco2": r["dco2"], "dcost": r["dcost"], "infr": infr,
                "real": max(0.0, r["score"] - 0.2 * infr), "secs": r["secs"]}

    res = {"ladder": {}, "horizon": {}, "pareto": {}, "load_knowledge": {}, "stats": {}}
    t0 = time.time()
    for dn, d in dfs.items():
        lad = {"none": {"score": 0.0, "real": 0.0, "infr": 0}}
        lad["template"] = summary(run_agent(tmpl, d))
        lad["price_only"] = summary(run_agent(PriceOnly, d))
        lad["co2_only"] = summary(run_agent(variant(LAMBDA_PRICE=0.0), d))
        r = run_agent(base, d)
        lad["mpc"] = summary(r)
        lad["perfect"] = {"score": perfect_foresight(d)}
        res["ladder"][dn] = lad
        print(dn, "ladder done", round(time.time() - t0), "s", flush=True)

        env = r["env"]
        a = np.asarray(env.actions)
        days = len(d) / 24.0
        disch = np.maximum(-a, 0).sum()
        charge = np.maximum(a, 0).sum()
        ev = env.evaluate_results()
        res["stats"][dn] = {
            "n": len(d), "days": days, "kwh_discharged_per_day": disch / days,
            "kwh_charged_per_day": charge / days,
            "cycles_per_day": disch / ETA / 2000.0 / days,
            "kg": ev["co2_estalviat_kg"], "eur": ev["cost_estalviat_eur"],
            "kg_base": ev["co2_baseline_kg"], "eur_base": ev["cost_baseline_eur"],
            "secs": r["secs"], "infr": int(r["infr"]), "fallbacks": r["fallbacks"],
        }
        # perfil horario de potencia (valores medios), total y por estacion
        hours = d.index.hour.values
        month = d.index.month.values
        seas = {"invierno": [12, 1, 2], "primavera": [3, 4, 5], "verano": [6, 7, 8], "otono": [9, 10, 11]}
        prof = {"todo": [float(a[hours == h].mean()) for h in range(24)]}
        for s, ms in seas.items():
            m = np.isin(month, ms)
            prof[s] = [float(a[m & (hours == h)].mean()) if (m & (hours == h)).any() else None
                       for h in range(24)]
        res["stats"][dn]["hour_profile"] = prof
        if dn == "pseudo":
            lam = base.LAMBDA_PRICE
            nb = len(d) // 168
            tot = np.array([np.abs(a[i * 168:(i + 1) * 168]).sum() for i in range(nb)])
            k = int(np.argsort(np.abs(tot - np.median(tot)))[0])
            sl = slice(k * 168, (k + 1) * 168)
            soc = np.asarray(env.soc_series)
            res["week"] = {
                "block": k, "lambda": lam,
                "time": [str(t) for t in d.index[sl]],
                "price": d.precio_eur_per_kwh.values[sl].tolist(),
                "co2": d.co2_kg_per_kwh.values[sl].tolist(),
                "action": a[sl].tolist(), "soc": soc[sl].tolist(),
            }

    # horizonte (pseudo-test)
    for h in HORIZONS:
        res["horizon"][str(h)] = summary(run_agent(horizon(h), dfs["pseudo"]))
    print("horizon done", round(time.time() - t0), "s", flush=True)

    # Pareto (pseudo-test)
    for lam in LAMBDAS:
        r = run_agent(variant(LAMBDA_PRICE=float(lam)), dfs["pseudo"])
        res["pareto"][str(lam)] = summary(r)
    print("pareto done", round(time.time() - t0), "s", flush=True)

    # valor del conocimiento de la demanda: cap de descarga hora actual
    class TrueLoad(base):
        def _net_load_estimate(self, obs):
            return self._cur

    class NoCap(base):
        def _net_load_estimate(self, obs):
            return self.P_MAX_KW

    for dn, d in dfs.items():
        net = (d.load_kw - d.pv_kw).values
        out = {"v1": res["ladder"][dn]["mpc"]["score"]}
        for name, cls in [("true", TrueLoad), ("nocap", NoCap)]:
            env = CampusBatteryEnv(d)
            obs = env.reset()
            ag = cls()
            done = False
            while not done:
                ag._cur = max(0.0, float(net[env.t]))
                obs, done = env.step(ag.act(obs))
            out[name] = precise_score(d, np.asarray(env.grid))[0]
            out[name + "_infr"] = int(env.clipped + env.violations)
        res["load_knowledge"][dn] = out
    print("load knowledge done", round(time.time() - t0), "s", flush=True)

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


# ----------------------------------------------------------------------------- etapa 2
def plots(res):
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    from analysis.style import apply, COLORS, save
    apply()
    L = res["ladder"]

    # 1. escalera ---------------------------------------------------------------
    rows = [("Sin batería", "none", "base"), ("Plantilla oficial (con penalización)", "template_real", "base"),
            ("Plantilla oficial (antes de penalizar)", "template", "base"),
            ("Solo precio", "price_only", "precio"), ("Solo CO2", "co2_only", "co2"),
            ("Nuestro MPC (LP 24 h)", "mpc", "nuestro"), ("Información perfecta (cota)", "perfect", "optimo")]

    def val(dn, key):
        if key == "template_real":
            return L[dn]["template"]["real"]
        return L[dn][key]["score"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = np.arange(len(rows))[::-1]
    hgt = 0.38
    for j, (dn, lbl, hatch) in enumerate([("train", "train completo (5993 h)", ""), ("pseudo", "pseudo-test (1680 h)", "//")]):
        for i, (name, key, col) in enumerate(rows):
            v = val(dn, key)
            ax.barh(y[i] + (0.2 if j == 0 else -0.2), v, hgt, color=COLORS[col], hatch=hatch,
                    edgecolor="white", alpha=0.95, label=lbl if i == 0 else None)
            pct = 100 * v / L[dn]["perfect"]["score"]
            ax.text(v + 0.06, y[i] + (0.2 if j == 0 else -0.2), f"{v:.2f}  ({pct:.1f} %)", va="center", fontsize=7.5)
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.set_xlim(0, 8.2)
    ax.set_xlabel("Score (entre paréntesis: % del óptimo con información perfecta)")
    ax.set_title("Nuestro MPC: 99,8–100 % del óptimo teórico", fontsize=13)
    ax.legend(loc="upper right", fontsize=8)
    save(fig, "est_escalera")

    # 2. horizonte --------------------------------------------------------------
    hs = HORIZONS
    sc = [res["horizon"][str(h)]["score"] for h in hs]
    pf = L["pseudo"]["perfect"]["score"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(hs, sc, "o-", color=COLORS["nuestro"], lw=2, label="MPC con H horas de previsión")
    ax.axhline(pf, color=COLORS["optimo"], ls="--", label=f"Información perfecta ({pf:.4f})")
    for h, s in zip(hs, sc):
        ax.annotate(f"{s:.3f}", (h, s), textcoords="offset points", xytext=(22, -4) if h <= 8 else (0, -14 if h < 24 else 8),
                    ha="center", fontsize=8)
    ax.set_xticks(hs)
    ax.set_xlabel("Horizonte conocido H (horas)")
    ax.set_ylabel("Score (pseudo-test)")
    ax.set_ylim(min(sc) - 0.25, pf + 0.15)
    ax.set_title("Con 24 h de previsión casi no queda nada por ganar")
    ax.legend(loc="lower right")
    save(fig, "est_horizonte")

    # 3. Pareto -----------------------------------------------------------------
    P = res["pareto"]
    lams = [float(k) for k in P]
    xc = np.array([P[k]["dcost"] for k in P])
    yc = np.array([P[k]["dco2"] for k in P])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ours = P["0.2593"]
    xs = np.linspace(xc.min() - 0.5, xc.max() + 0.5, 50)
    for off, ls in [(0, "-"), (-1, ":"), (-2, ":")]:
        s = ours["score"] + off
        ax.plot(xs, (s - 0.3 * xs) / 0.7, color=COLORS["base"], ls=ls, lw=1)
        yl = (s - 0.3 * (xs[-1] - 0.05)) / 0.7
        if yc.min() - 0.5 < yl < yc.max() + 0.5:
            ax.text(xs[-1] - 0.05, yl + 0.07, f"score {s:.2f}", ha="right", fontsize=7.5, color="#555")
    ax.plot(xc, yc, "o-", color=COLORS["senal"], lw=1.8, label="barrido de λ")
    for lam, x, y_ in zip(lams, xc, yc):
        if lam in (0, 0.05, 0.1, 1, 5):
            ax.annotate(f"λ={lam:g}", (x, y_), textcoords="offset points", xytext=(-34, -4) if lam == 5 else (6, 5), fontsize=8)
    ax.plot(ours["dcost"], ours["dco2"], "*", ms=17, color=COLORS["nuestro"], mec="k", zorder=5,
            label=f"nuestro λ=0,2593 (score {ours['score']:.2f})")
    ax.set_xlabel("Ahorro de coste ΔCoste (%)")
    ax.set_ylabel("Reducción de CO2 ΔCO2 (%)")
    ax.set_xlim(xs[0], xs[-1])
    ax.set_ylim(yc.min() - 0.5, yc.max() + 0.5)
    ax.set_title("Nuestro λ cae en el máximo de la fórmula 70/30")
    ax.legend(loc="lower left", fontsize=8)
    save(fig, "est_pareto")

    # 4. semana -----------------------------------------------------------------
    W = res["week"]
    t = pd.to_datetime(W["time"])
    pr, co, a, soc = (np.array(W[k]) for k in ("price", "co2", "action", "soc"))
    w = co + W["lambda"] * pr
    fig, axs = plt.subplots(3, 1, figsize=(8, 4.5), sharex=True)
    axs[0].plot(t, pr, color=COLORS["precio"], lw=1.4)
    axs[0].set_ylabel("Precio €/kWh", color=COLORS["precio"], fontsize=9)
    a0 = axs[0].twinx()
    a0.plot(t, co, color=COLORS["co2"], lw=1.4)
    a0.set_ylabel("CO2 kg/kWh", color=COLORS["co2"], fontsize=9)
    a0.grid(False)
    a0.spines["right"].set_visible(True)
    axs[1].plot(t, w, color=COLORS["senal"], lw=1.4)
    axs[1].set_ylabel("w = CO2 + λ·precio", fontsize=9)
    for ax_ in (axs[1], axs[2]):
        for i in range(len(t)):
            if a[i] > 1:
                ax_.axvspan(t[i], t[i] + pd.Timedelta(hours=1), color=COLORS["carga"], alpha=0.22, lw=0)
            elif a[i] < -1:
                ax_.axvspan(t[i], t[i] + pd.Timedelta(hours=1), color=COLORS["descarga"], alpha=0.22, lw=0)
    axs[1].plot([], [], color=COLORS["carga"], lw=6, alpha=0.4, label="carga")
    axs[1].plot([], [], color=COLORS["descarga"], lw=6, alpha=0.4, label="descarga")
    axs[1].legend(loc="upper right", ncol=2, fontsize=8)
    axs[2].plot(t, soc, color="k", lw=1.4)
    axs[2].set_ylabel("SOC kWh", fontsize=9)
    axs[2].set_ylim(0, 2050)
    a2 = axs[2].twinx()
    a2.bar(t, a, width=1 / 24, color=np.where(a >= 0, COLORS["carga"], COLORS["descarga"]), alpha=0.8, align="edge")
    a2.set_ylabel("Potencia kW", fontsize=9)
    a2.set_ylim(-600, 600)
    a2.grid(False)
    a2.spines["right"].set_visible(True)
    axs[2].xaxis.set_major_locator(mdates.DayLocator())
    axs[2].xaxis.set_major_formatter(mdates.DateFormatter("%a %d/%m"))
    for tl in axs[2].get_xticklabels():
        tl.set_fontsize(8)
    fig.suptitle("Carga en horas baratas y limpias, descarga en las caras y sucias", fontweight="bold", fontsize=13)
    save(fig, "est_semana")

    # 5. horas ------------------------------------------------------------------
    prof = res["stats"]["train"]["hour_profile"]
    fig, axs = plt.subplots(1, 2, figsize=(8, 4.5), sharey=True, gridspec_kw={"width_ratios": [1, 1.25]})
    h = np.arange(24)
    m = np.array(prof["todo"])
    axs[0].bar(h, m, color=np.where(m >= 0, COLORS["carga"], COLORS["descarga"]))
    axs[0].set_title("Media anual", fontsize=11)
    axs[0].set_xlabel("Hora del día")
    axs[0].set_ylabel("Potencia media de la batería (kW)\n(+ carga, − descarga)")
    axs[0].axhline(0, color="k", lw=0.8)
    cols = {"invierno": "#0072B2", "primavera": "#009E73", "verano": "#D55E00", "otono": "#CC79A7"}
    for s, c in cols.items():
        v = [np.nan if x is None else x for x in prof[s]]
        axs[1].plot(h, v, color=c, lw=1.8, label=s.replace("otono", "otoño"))
    axs[1].axhline(0, color="k", lw=0.8)
    axs[1].set_title("Por estación", fontsize=11)
    axs[1].set_xlabel("Hora del día")
    axs[1].legend(fontsize=8, ncol=1, loc="upper left")
    for ax_ in axs:
        ax_.set_xticks(range(0, 24, 3))
    fig.suptitle("Cargamos de madrugada y mediodía, descargamos por la tarde-noche", fontweight="bold", fontsize=13)
    save(fig, "est_horas")


def write_findings(res):
    L, H, P, S, K = res["ladder"], res["horizon"], res["pareto"], res["stats"], res["load_knowledge"]
    tr, ps = S["train"], S["pseudo"]
    f4 = lambda v: f"{v:.4f}"
    pct = lambda dn, v: 100 * v / L[dn]["perfect"]["score"]
    best_h = max(H.values(), key=lambda r: r["score"])["score"]
    lines = ["# Hallazgos de estrategia (T5)", "",
             "Fuente: `analysis/strategy.py`, números en `analysis/cache/strategy_results.json`.", "",
             "## 1. Escalera de referencias (est_escalera.png)  train completo | pseudo-test"]
    for name, key in [("Sin batería", "none"), ("Plantilla oficial, antes de penalizar", "template"),
                      ("Solo precio", "price_only"), ("Solo CO2", "co2_only"), ("Nuestro MPC", "mpc"),
                      ("Información perfecta", "perfect")]:
        row = []
        for dn in ("train", "pseudo"):
            v = L[dn][key]["score"]
            row.append(f"{f4(v)} ({pct(dn, v):.2f} % del óptimo)")
        lines.append(f"- {name}: " + " | ".join(row))
    lines.append("- Plantilla oficial con penalización (0,20 por infracción): "
                 + " | ".join(f"{f4(L[d]['template']['real'])} con {L[d]['template']['infr']} infracciones"
                              for d in ("train", "pseudo")))
    lines += ["", "## 2. Valor del horizonte (est_horizonte.png, pseudo-test)",
              "- " + "; ".join(f"H={h}: {f4(H[str(h)]['score'])}" for h in HORIZONS),
              f"- Cota de información perfecta: {f4(L['pseudo']['perfect']['score'])}. "
              f"H=24 deja {f4(L['pseudo']['perfect']['score'] - H['24']['score'])} puntos por ganar; "
              f"H=1 pierde {f4(H['24']['score'] - H['1']['score'])} respecto a H=24.",
              "", "## 3. Frontera CO2–coste (est_pareto.png, pseudo-test)"]
    for k in ("0", "0.1", "0.2593", "1", "5"):
        r = P[k]
        lines.append(f"- λ={float(k):g}: ΔCO2 {r['dco2']:.3f} %, ΔCoste {r['dcost']:.3f} %, score {f4(r['score'])}")
    lines.append("- Scores del resto: " + "; ".join(f"λ={float(k):g}: {f4(r['score'])}" for k, r in P.items()
                                                    if k not in ("0", "0.1", "0.2593", "1", "5")))
    bestk = max(P, key=lambda k: P[k]["score"])
    lines.append(f"- Mejor score del barrido: λ={float(bestk):g} ({f4(P[bestk]['score'])}); "
                 f"el nuestro (0,2593) da {f4(P['0.2593']['score'])}.")
    w = res["week"]
    lines += ["", "## 4. Semana de ejemplo (est_semana.png)",
              f"- Bloque {w['block'] + 1} del pseudo-test, del {w['time'][0][:10]} al {w['time'][-1][:10]}, "
              "elegido por ser el más cercano a la mediana de actividad de la batería.",
              "", "## 5. Perfil horario (est_horas.png, train completo)"]
    p = np.array(tr["hour_profile"]["todo"])
    ch = [h for h in range(24) if p[h] > 20]
    dc = [h for h in range(24) if p[h] < -20]
    lines.append(f"- Horas con carga media > 20 kW: {ch}; con descarga media < -20 kW: {dc}.")
    lines.append(f"- Pico medio de carga {p.max():.0f} kW a las {int(p.argmax())} h; "
                 f"pico medio de descarga {p.min():.0f} kW a las {int(p.argmin())} h.")
    lines += ["", "## 6. Números para la presentación"]
    lines.append(f"- Ciclos equivalentes por día: {tr['cycles_per_day']:.3f} (train), {ps['cycles_per_day']:.3f} (pseudo-test).")
    lines.append(f"- kWh entregados al campus por día: {tr['kwh_discharged_per_day']:.0f} (train); "
                 f"cargados desde red: {tr['kwh_charged_per_day']:.0f}.")
    lines.append(f"- Train completo (5993 h): {tr['kg']:.1f} kg CO2 evitados, {tr['eur']:.2f} € ahorrados.")
    lines.append(f"- Anualizado (x 8760/5993): {tr['kg'] * ANNUAL:.0f} kg CO2/año = {tr['kg'] * ANNUAL / 1000:.2f} t, "
                 f"{tr['eur'] * ANNUAL:.0f} €/año.")
    lines.append(f"- Tiempo de ejecución: {tr['secs']:.1f} s en 5993 h (~{tr['secs'] * 2016 / 5993:.1f} s por 2016 h); "
                 f"infracciones {tr['infr']} (train), {ps['infr']} (pseudo-test); respaldos usados {tr['fallbacks']}.")
    lines.append("- Resultado real en el leaderboard (mitad pública, 1008 h): score 6,43; ΔCO2 5,96 %; ΔCoste 7,52 %; "
                 "4282,5 kg CO2; 8934,63 €; 0 infracciones. Mejor puntuación pública de cualquier equipo: 6,43.")
    lines.append("- Valor de conocer la demanda actual (tope de descarga de la hora actual), score:")
    for dn, nm in (("train", "train"), ("pseudo", "pseudo-test")):
        k = K[dn]
        lines.append(f"  - {nm}: v1 (última hora medida) {f4(k['v1'])}; demanda real {f4(k['true'])} "
                     f"(+{k['true'] - k['v1']:.4f}); sin tope (500 kW) {f4(k['nocap'])} "
                     f"({k['nocap'] - k['v1']:+.4f}, infracciones {k['nocap_infr']}).")
    lines += ["", "## Mensajes para el jurado",
              f"- Alcanzamos el {pct('train', L['train']['mpc']['score']):.2f} % del óptimo con información perfecta "
              "de todo el año, con solo 24 h de previsión oficial y 0 infracciones.",
              f"- La señal única CO2 + λ·precio supera claramente a usar solo precio "
              f"({f4(L['pseudo']['price_only']['score'])}) o solo CO2 ({f4(L['pseudo']['co2_only']['score'])}) en pseudo-test.",
              "- Predecir demanda o solar aporta como máximo: conocer la demanda real de la hora cambia el score en "
              f"{K['train']['true'] - K['train']['v1']:+.4f}."]
    FINDINGS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("findings lines:", len(lines))


def main():
    if "--recompute" in sys.argv or not CACHE.exists():
        res = stage1()
    else:
        res = json.loads(CACHE.read_text(encoding="utf-8"))
    plots(res)
    write_findings(res)
    print("ok")


if __name__ == "__main__":
    main()
