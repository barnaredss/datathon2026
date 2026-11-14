"""T6 - Estudio what-if para UPC Sostenible (train completo, 5.993 h).

Uso (desde la raiz):  ./.venv/Scripts/python.exe -m analysis.whatif [--recompute]
Calcula con un LP de información perfecta parametrizado y guarda todo en
analysis/cache/whatif_results.json; las figuras se dibujan desde ese JSON.
"""
import json
import sys

import numpy as np
from scipy import sparse
from scipy.optimize import linprog

from tools.evaluate import load_hourly, precise_score, ROOT, ETA, CampusBatteryEnv

CACHE = ROOT / "analysis" / "cache" / "whatif_results.json"
TODAY = dict(cap=2000.0, power=500.0, eff=0.9, pv=1.0, alpha=0.7)


def solve(df, cap=2000.0, power=500.0, eff=0.9, pv=1.0, alpha=0.7):
    """LP de información perfecta (igual que perfect_foresight) con parametros."""
    eta = eff ** 0.5
    net = (df.load_kw - pv * df.pv_kw).values
    n = len(df)
    b = np.maximum(net, 0.0)
    pr, co = df.precio_eur_per_kwh.values, df.co2_kg_per_kwh.values
    w = alpha * co / ((b * co).sum() / b.sum()) + (1 - alpha) * pr / ((b * pr).sum() / b.sum())
    eye = sparse.identity(n, format="csr")
    zero = sparse.csr_matrix((n, n))
    lag = sparse.diags([np.ones(n), -np.ones(n - 1)], [0, -1], format="csr")
    b_eq = np.zeros(n)
    b_eq[0] = 0.5 * cap
    res = linprog(np.concatenate([np.zeros(2 * n), w, np.zeros(n)]),
                  A_ub=sparse.hstack([eye, -eye, -eye, zero]), b_ub=-net,
                  A_eq=sparse.hstack([-eta * eye, eye / eta, zero, lag]), b_eq=b_eq,
                  bounds=[(0, power)] * (2 * n) + [(0, None)] * n + [(0, cap)] * n, method="highs")
    assert res.status == 0, res.message
    grid = res.x[2 * n:3 * n]
    ch = res.x[:n]
    dis = res.x[n:2 * n]
    return dict(grid=grid, b=b, ch=ch, dis=dis, pr=pr, co=co)


def metrics(df, r, n_h):
    ann = 8760.0 / n_h
    b, g, pr, co = r["b"], r["grid"], r["pr"], r["co"]
    co_b, co_g = (b * co).sum(), (g * co).sum()
    c_b, c_g = (b * pr).sum(), (g * pr).sum()
    return dict(dco2_pct=100 * (1 - co_g / co_b), dcost_pct=100 * (1 - c_g / c_b),
                kg_year=(co_b - co_g) * ann, eur_year=(c_b - c_g) * ann,
                co2_base_kg=co_b, cost_base_eur=c_b,
                score=0.7 * 100 * (1 - co_g / co_b) + 0.3 * 100 * (1 - c_g / c_b))


def run(df, **kw):
    p = dict(TODAY)
    p.update(kw)
    r = solve(df, **p)
    m = metrics(df, r, len(df))
    m.update(p)
    return m, r


# ---------------- operador: horario fijo sobre el entorno oficial ----------------
def clamp(action, soc, cap=2000.0, pmax=500.0, eps=1e-4):
    max_c = max(0.0, min(pmax, (cap - soc) / ETA - eps))
    max_d = max(0.0, min(pmax, soc * ETA - eps))
    return float(min(max_c, max(-max_d, action)))


def simulate_schedule(df, rule):
    env = CampusBatteryEnv(df)
    obs = env.reset()
    done = False
    while not done:
        ts = obs["timestamp"]
        a = clamp(rule(ts.hour, ts.month) * 500.0, obs["soc_kwh"])
        obs, done = env.step(a)
    s, dco2, dcost = precise_score(df, np.asarray(env.grid))
    return dict(score=s, dco2=dco2, dcost=dcost, infr=int(env.clipped + env.violations))


def make_rule(ch, dis, ch_s=None, dis_s=None, summer=(5, 6, 7, 8, 9)):
    def rule(h, m):
        c, d = (ch_s, dis_s) if (ch_s is not None and m in summer) else (ch, dis)
        if h in c:
            return 1.0
        if h in d:
            return -1.0
        return 0.0
    return rule


def compute():
    df = load_hourly()
    n_h = len(df)
    out = {"n_hours": n_h, "ann_factor": 8760.0 / n_h}
    m0, _ = run(df)
    out["today"] = m0
    out["sanity_pf_score"] = m0["score"]

    # 1. dimensionado
    caps = [500, 1000, 2000, 4000, 8000]
    pows = [250, 500, 1000, 2000]
    out["sizing"] = [run(df, cap=c, power=p) [0] for c in caps for p in pows]
    out["sizing_caps"], out["sizing_pows"] = caps, pows
    d_cap = 200.0
    d_pow = 50.0
    mc, _ = run(df, cap=2000 + d_cap)
    mp, _ = run(df, power=500 + d_pow)
    out["marg"] = dict(
        eur_per_kwh=(mc["eur_year"] - m0["eur_year"]) / d_cap, kg_per_kwh=(mc["kg_year"] - m0["kg_year"]) / d_cap,
        score_per_kwh=(mc["score"] - m0["score"]) / d_cap,
        eur_per_kw=(mp["eur_year"] - m0["eur_year"]) / d_pow, kg_per_kw=(mp["kg_year"] - m0["kg_year"]) / d_pow,
        score_per_kw=(mp["score"] - m0["score"]) / d_pow)

    # 2. rendimiento
    out["eff"] = [run(df, eff=e)[0] for e in [0.80, 0.85, 0.90, 0.92, 0.95, 0.98]]

    # 3. solar
    sol = []
    pvmask = df.pv_kw.values > 0
    ratio = (df.load_kw.values[pvmask] / df.pv_kw.values[pvmask])
    out["pv_surplus_scale"] = float(ratio.min())
    base1 = np.maximum(df.load_kw.values - df.pv_kw.values, 0)
    pr, co = df.precio_eur_per_kwh.values, df.co2_kg_per_kwh.values
    ann = 8760.0 / n_h
    nopv_cost = (df.load_kw.values * pr).sum()
    nopv_co2 = (df.load_kw.values * co).sum()
    for s in [1, 2, 3, 5, 8, 10, 15, 20]:
        m, r = run(df, pv=s)
        net = df.load_kw.values - s * df.pv_kw.values
        m["surplus_hours"] = int((net < 0).sum())
        m["surplus_kwh_year"] = float(-net[net < 0].sum() * ann)
        m["pv_energy_share_pct"] = float(100 * (s * df.pv_kw.values).sum() / df.load_kw.values.sum())
        m["wasted_share_pct"] = float(100 * (-net[net < 0].sum()) / (s * df.pv_kw.values).sum())
        # ahorro combinado FV + batería frente a campus sin FV ni batería (misma red de referencia)
        g = r["grid"]
        m["combo_eur_year"] = float((nopv_cost - (g * pr).sum()) * ann)
        m["combo_kg_year"] = float((nopv_co2 - (g * co).sum()) * ann)
        m["pvonly_eur_year"] = float((nopv_cost - (np.maximum(net, 0) * pr).sum()) * ann)
        m["pvonly_kg_year"] = float((nopv_co2 - (np.maximum(net, 0) * co).sum()) * ann)
        sol.append(m)
    out["solar"] = sol

    # 4. pesos
    out["alpha"] = [run(df, alpha=a)[0] for a in [0.0, 0.3, 0.5, 0.7, 1.0]]
    cb, kb = m0["cost_base_eur"], m0["co2_base_kg"]
    lam = (0.3 / 0.7) * kb / cb
    out["lambda_kg_per_eur"] = lam
    out["implicit_eur_per_kg"] = 1 / lam
    out["implicit_eur_per_t"] = 1000 / lam

    # 5. regla del operador
    r = lambda a, b: set(range(a, b + 1))
    winter = (10, 11, 12, 1, 2, 3)

    def seasonal(h, m):
        c, d = (r(12, 16), r(18, 21)) if m in winter else (r(12, 16), r(20, 23))
        return 1.0 if h in c else (-1.0 if h in d else 0.0)

    sched = {
        "A carga 13-17 y 1-4; descarga 7-9 y 19-22": make_rule(r(13, 17) | r(1, 4), r(7, 9) | r(19, 22)),
        "B carga 11-16; descarga 18-23": make_rule(r(11, 16), r(18, 23)),
        "C carga 12-16; descarga 20-23": make_rule(r(12, 16), r(20, 23)),
        "D carga 12-16 y 3-4; descarga 6-8 y 20-23": make_rule(r(12, 16) | r(3, 4), r(6, 8) | r(20, 23)),
        "E carga 12-16; descarga 18-21 oct-mar, 20-23 abr-sep": seasonal,
    }
    sched = {k: (v if callable(v) else v) for k, v in sched.items()}
    op = {}
    for k, rule in sched.items():
        op[k] = simulate_schedule(df, rule)
        op[k]["pct_opt"] = 100 * op[k]["score"] / m0["score"]
        print("  op", k[:2], f"{op[k]['score']:.4f} {op[k]['pct_opt']:.1f}% infr={op[k]['infr']}")
    out["operator"] = op
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def figures(R):
    import matplotlib.pyplot as plt
    from analysis.style import apply, COLORS, save
    apply()
    T = R["today"]
    caps, pows = R["sizing_caps"], R["sizing_pows"]
    S = {(m["cap"], m["power"]): m for m in R["sizing"]}
    mg = R["marg"]

    # --- dimensionado
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.8))
    for a, key, lab, div, fmt in [(ax[0], "eur_year", "Ahorro EUR/año (miles)", 1e3, "{:.0f}"),
                                  (ax[1], "kg_year", "CO2 evitado t/año", 1e3, "{:.0f}")]:
        Z = np.array([[S[(c, p)][key] / div for c in caps] for p in pows])
        im = a.imshow(Z, origin="lower", cmap="YlGn", aspect="auto")
        a.grid(False)
        a.set_xticks(range(len(caps)), [str(c) for c in caps])
        a.set_yticks(range(len(pows)), [str(p) for p in pows])
        a.set_xlabel("Capacidad (kWh)")
        a.set_ylabel("Potencia (kW)")
        a.set_title(lab, fontsize=11)
        for i in range(len(pows)):
            for j in range(len(caps)):
                a.text(j, i, fmt.format(Z[i, j]), ha="center", va="center", fontsize=9)
        ci, pi = caps.index(2000), pows.index(500)
        a.add_patch(plt.Rectangle((ci - .5, pi - .5), 1, 1, fill=False, ec=COLORS["descarga"], lw=3))
        a.spines[:].set_visible(False)
    fig.suptitle(R["titles"]["dim"], fontsize=14, fontweight="bold")
    fig.text(0.5, 0.01, "Recuadro naranja = batería actual (2000 kWh, 500 kW, 90 %, FV x1). Train completo, información perfecta.",
             ha="center", fontsize=9)
    save(fig, "whatif_dimensionado")

    # --- rendimiento
    E = R["eff"]
    x = [100 * m["eff"] for m in E]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(x, [m["eur_year"] / 1e3 for m in E], "o-", color=COLORS["precio"], label="EUR/año (miles)")
    ax.set_xlabel("Rendimiento ida y vuelta (%)")
    ax.set_ylabel("Ahorro (miles EUR/año)", color=COLORS["precio"])
    ax2 = ax.twinx()
    ax2.plot(x, [m["kg_year"] / 1e3 for m in E], "s-", color=COLORS["co2"])
    ax2.set_ylabel("CO2 evitado (t/año)", color=COLORS["co2"])
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax.axvline(90, color=COLORS["descarga"], ls="--")
    ax.annotate("Hoy: 90 %", (90, ax.get_ylim()[0]), xytext=(4, 10), textcoords="offset points",
                color=COLORS["descarga"])
    ax.set_title(R["titles"]["eff"])
    save(fig, "whatif_rendimiento")

    # --- solar
    SO = R["solar"]
    xs = [m["pv"] for m in SO]
    fig, ax = plt.subplots(1, 2, figsize=(10, 4.5))
    ax[0].plot(xs, [m["eur_year"] / 1e3 for m in SO], "o-", color=COLORS["precio"], label="EUR (miles)")
    ax[0].set_ylabel("Valor de la batería (miles EUR/año)", color=COLORS["precio"])
    ax[0].set_xlabel("Factor de escala de la FV (x)")
    a2 = ax[0].twinx()
    a2.plot(xs, [m["kg_year"] / 1e3 for m in SO], "s-", color=COLORS["co2"])
    a2.set_ylabel("CO2 evitado por la batería (t/año)", color=COLORS["co2"])
    a2.grid(False)
    a2.spines["right"].set_visible(True)
    ax[0].axvline(1, color=COLORS["descarga"], ls="--")
    ax[0].set_title("Valor de la batería", fontsize=11)
    ax[1].bar(range(len(xs)), [m["surplus_kwh_year"] / 1e3 for m in SO], color=COLORS["solar"], ec="#888")
    ax[1].set_xticks(range(len(xs)), [f"x{int(s)}" for s in xs])
    ax[1].set_ylabel("Excedente FV a mediodía (MWh/año)")
    ax[1].set_xlabel("Factor de escala de la FV")
    ax[1].set_title("Excedente que se pierde (no se paga)", fontsize=11)
    ax[1].patches[0].set_edgecolor(COLORS["descarga"])
    ax[1].patches[0].set_linewidth(3)
    fig.suptitle(R["titles"]["pv"], fontsize=14, fontweight="bold")
    fig.text(0.5, 0.01, "Naranja = FV actual (x1). El excedente aparece desde x%s." % es(R["pv_surplus_scale"], 2),
             ha="center", fontsize=9)
    save(fig, "whatif_solar")

    # --- pesos
    A = R["alpha"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot([m["kg_year"] / 1e3 for m in A], [m["eur_year"] / 1e3 for m in A], "o-", color=COLORS["senal"])
    for m in A:
        ax.annotate(f"alfa={m['alpha']:.1f}", (m["kg_year"] / 1e3, m["eur_year"] / 1e3), xytext=(6, 6),
                    textcoords="offset points", fontsize=9)
    t = [m for m in A if abs(m["alpha"] - 0.7) < 1e-9][0]
    ax.plot(t["kg_year"] / 1e3, t["eur_year"] / 1e3, "o", ms=14, mfc="none", mec=COLORS["descarga"], mew=3,
            label="Fórmula oficial 70/30 (hoy)")
    ax.set_xlabel("CO2 evitado (t/año)")
    ax.set_ylabel("Ahorro (miles EUR/año)")
    ax.legend(loc="lower left")
    ax.set_title(R["titles"]["alpha"])
    save(fig, "whatif_pesos")

    # --- operador
    OP = R["operator"]
    names = list(OP)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    vals = [OP[k]["pct_opt"] for k in names]
    cols = [COLORS["carga"] if v == max(vals) else COLORS["base"] for v in vals]
    ax.barh([k[2:].replace("; ", chr(10)) for k in names], vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(v + .5, i, f"{es(v, 1)} %", va="center", fontsize=9)
    ax.axvline(100, color=COLORS["optimo"], ls="--")
    ax.text(99.5, -.42, "Óptimo (100 %)", ha="right", color=COLORS["optimo"], fontsize=9)
    ax.set_xlim(0, 112)
    ax.set_xlabel("% del óptimo (batería actual, 0 infracciones)")
    ax.invert_yaxis()
    ax.set_title(R["titles"]["op"])
    save(fig, "whatif_operador")


def es(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def make_titles(R):
    A = {m["alpha"]: m for m in R["alpha"]}
    up = (A[0.7]["eur_year"] - A[1.0]["eur_year"]) / ((A[1.0]["kg_year"] - A[0.7]["kg_year"]) / 1000)
    E = R["eff"]
    pt = (E[-1]["eur_year"] - E[2]["eur_year"]) / (100 * (E[-1]["eff"] - E[2]["eff"]))
    best = max(v["pct_opt"] for v in R["operator"].values())
    return dict(
        dim="Energía y potencia se necesitan: juntas, +98 %",
        eff="+1 punto de rendimiento = +%s EUR/año" % es(pt),
        pv="La FV solo sobra a partir de x%s" % es(R["pv_surplus_scale"], 2),
        alpha="De alfa 0,7 a 1: %s EUR por t de CO2" % es(up),
        op="Un horario fijo logra el %s %% del óptimo" % es(best))


def main():
    R = None
    if CACHE.exists() and "--recompute" not in sys.argv:
        R = json.loads(CACHE.read_text(encoding="utf-8"))
    if R is None:
        R = compute()
    print(f"sanity PF today = {R['today']['score']:.4f} (esperado 5.6753)")
    mg = R["marg"]
    print("marg:", {k: round(v, 4) for k, v in mg.items()})
    print("implicito EUR/t:", round(R["implicit_eur_per_t"], 1), "pv surplus scale:", round(R["pv_surplus_scale"], 2))
    if "--nofig" not in sys.argv:
        R["titles"] = make_titles(R)
        figures(R)


if __name__ == "__main__":
    main()
