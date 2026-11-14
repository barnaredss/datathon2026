"""Auditoría de datos y figuras EDA (T4). Ejecutar: python -m analysis.eda"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from analysis.style import apply, COLORS, save

apply()
D = "data/train/"
LAM = 0.2593
S = {}  # estadisticas para el informe
MES = ["Sep", "Oct", "Nov", "Dic", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago"]

h = pd.read_csv("data/hourly_train.csv", parse_dates=[0], index_col=0)
pk = pd.read_csv("data/hourly_price_co2.csv", parse_dates=[0], index_col=0)
col = "Contador - POTENCIA ACTIVA EXPORTADA (kW)"
c = pd.read_csv(D + "contador.csv", parse_dates=["Fecha"], usecols=["Fecha", col]).set_index("Fecha")[col]

# ---- 1. Cobertura
S["filas_5min"] = len(c)
S["dup"] = int(c.index.duplicated().sum())
gap = c.index.to_series().diff()
S["gaps_7d"] = int(((gap > pd.Timedelta("6D")) & (gap < pd.Timedelta("8D"))).sum())
S["gaps_cortos"] = [(str(i)[:16], str(v)) for i, v in gap[(gap > pd.Timedelta("10min")) & (gap < pd.Timedelta("1D"))].items()]
nov = {}
for f in ["contador", "inversor", "meteo", "entradas_salidas"]:
    q = pd.read_csv(D + f + ".csv", usecols=["Fecha"], parse_dates=["Fecha"]).Fecha
    nov[f] = int(((q >= "2025-11-01") & (q < "2025-12-01")).sum())
S["nov_filas"] = nov
S["dias_mes"] = {str(k): v for k, v in h.groupby(h.index.to_period("M")).apply(lambda x: x.index.normalize().nunique()).items()}
S["horas_h"] = len(h)
S["horas_pk"] = len(pk)
zero = c[c >= 0]
S["zero_5min"] = len(zero)
S["zero_dias"] = {str(k.date()): v for k, v in zero.index.normalize().value_counts().sort_index().items()}
S["zero_horas_hourly"] = int((h.load_kw <= 0).sum())
S["zero_h_dias"] = sorted(set(str(x.date()) for x in h.index[h.load_kw <= 0]))

# ---- 2. Noche congelada
r = (c != c.shift()).cumsum()
tt = c.index.to_series()
g = pd.DataFrame({"n": c.groupby(r).size(), "t0": tt.groupby(r).first(), "t1": tt.groupby(r).last(), "v": c.groupby(r).first()})
noche = g[(g.n >= 90) & (g.n <= 110) & (g.v < 0)]
S["noches"] = len(noche)
S["dias_total"] = c.index.normalize().nunique()
S["noche_ini"] = noche.t0.dt.strftime("%H:%M").value_counts().head(2).to_dict()
S["noche_fin"] = noche.t1.dt.strftime("%H:%M").value_counts().head(2).to_dict()
S["noche_media_n"] = float(noche.n.mean())
nr = c[(c.index.hour < 6)]
S["valores_unicos_noche_dia"] = float(nr.groupby(nr.index.date).nunique().mean())
S["valores_unicos_total"] = int(c.nunique())
S["frac_entera"] = float((c % 1 == 0).mean())
dh = c[(c.index.hour >= 8) & (c.index.hour < 20)]
S["valores_unicos_dia_dia"] = float(dh.groupby(dh.index.date).nunique().mean())
cl = (-c).clip(0, 5000)
S["filas_congeladas_pct"] = float(g[(g.n >= 12)].n.sum() / len(c) * 100)
hm = h.load_kw.groupby(h.index.hour).mean()
S["media_h0_5"] = float(hm.loc[0:5].mean()); S["media_h23"] = float(hm.loc[23]); S["media_h6"] = float(hm.loc[6])
S["h_unicos_h3"] = int(h.load_kw[h.index.hour == 3].nunique()); S["dias_h"] = int(h.index.normalize().nunique())
sal = []
for t in noche.t1:
    nx = t + pd.Timedelta("5min")
    if nx in cl.index:
        sal.append(abs(cl[nx] - cl[t]))
S["salto_0600_medio"] = float(np.mean(sal))
S["var_5min_dia_medio"] = float(cl[(cl.index.hour >= 8) & (cl.index.hour < 20)].diff().abs().mean())

# ---- 3. Escala
pvm, ldm = h.pv_kw.mean(), h.load_kw.mean()
S["load_media"] = float(ldm); S["load_pico"] = float(h.load_kw.max()); S["load_min"] = float(h.load_kw.min())
S["pv_media"] = float(pvm); S["pv_pico"] = float(h.pv_kw.max()); S["pv_share"] = float(pvm / ldm * 100)
net = h.load_kw - h.pv_kw
S["net_lt500"] = float((net < 500).mean() * 100); S["net_lt0"] = float((net < 0).mean() * 100)
S["net_min"] = float(net.min())
pvh = h.pv_kw.groupby(h.index.hour).mean()
S["pv_hora_pico"] = int(pvh.idxmax()); S["pv_share_mediodia"] = float(pvh.max() / hm.loc[pvh.idxmax()] * 100)
fig, ax = plt.subplots()
ax.fill_between(hm.index, hm.values, color=COLORS["demanda"], alpha=0.15)
ax.plot(hm.index, hm.values, color=COLORS["demanda"], lw=2.2, label=f"Demanda (media {ldm:,.0f} kW)".replace(",", "."))
ax.fill_between(pvh.index, pvh.values, color=COLORS["solar"], alpha=0.7)
ax.plot(pvh.index, pvh.values, color="#B8A400", lw=2.2, label=f"Fotovoltaica (media {pvm:.0f} kW, {S['pv_share']:.1f} %)")
ax.axhline(500, color=COLORS["descarga"], ls="--", lw=1.2)
ax.text(0.3, 520, "Potencia de la batería (500 kW)", color=COLORS["descarga"], fontsize=9)
ax.set_xlabel("Hora del día"); ax.set_ylabel("Potencia media (kW)"); ax.set_xlim(0, 23); ax.set_ylim(0, 1400)
ax.set_title(f"La FV es solo el {S['pv_share']:.1f} % de la demanda: la carga manda".replace(".", ","))
ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.93)); save(fig, "eda_escala"); plt.close(fig)

# ---- 4. Señales
pk["hora"] = pk.index.hour
pk["mes"] = pk.index.to_period("M")
meses = [m for m in sorted(pk.mes.unique()) if (pk.mes == m).sum() > 100]


def hm_(v):
    return pk.pivot_table(index="hora", columns="mes", values=v, aggfunc="mean")[meses]


fig, axs = plt.subplots(1, 2, figsize=(8, 4.5))
for ax, v, nm, cm in [(axs[0], "precio_eur_per_kwh", "Precio (€/kWh)", "YlOrBr"), (axs[1], "co2_kg_per_kwh", "CO₂ (kg/kWh)", "PuBu")]:
    M = hm_(v)
    im = ax.imshow(M.values, aspect="auto", origin="lower", cmap=cm)
    ax.set_xticks(range(len(meses)))
    ax.set_xticklabels([MES[(m.month - 9) % 12] for m in meses], fontsize=7)
    ax.set_yticks(range(0, 24, 4)); ax.set_xlabel("Mes (sep 2025 – ago 2026)"); ax.grid(False)
    ax.set_title(nm, fontsize=11); fig.colorbar(im, ax=ax, shrink=0.85)
axs[0].set_ylabel("Hora del día")
fig.suptitle("Precio y CO₂ siguen patrones horarios distintos", fontsize=14, fontweight="bold")
save(fig, "eda_heatmaps"); plt.close(fig)
S["precio_media"] = float(pk.precio_eur_per_kwh.mean()); S["co2_media"] = float(pk.co2_kg_per_kwh.mean())
S["precio_min"] = float(pk.precio_eur_per_kwh.min()); S["precio_max"] = float(pk.precio_eur_per_kwh.max())
S["precio_neg"] = int((pk.precio_eur_per_kwh < 0).sum())
S["co2_min"] = float(pk.co2_kg_per_kwh.min()); S["co2_max"] = float(pk.co2_kg_per_kwh.max())
S["corr_all"] = float(pk.precio_eur_per_kwh.corr(pk.co2_kg_per_kwh))
cm_ = pk.groupby("mes").apply(lambda x: x.precio_eur_per_kwh.corr(x.co2_kg_per_kwh) if len(x) > 100 else np.nan).dropna()
S["corr_mes_min"] = float(cm_.min()); S["corr_mes_max"] = float(cm_.max()); S["corr_mes_neg"] = int((cm_ < 0).sum())
S["corr_mes"] = {str(k): round(float(v), 2) for k, v in cm_.items()}
pp = pk.groupby("hora").precio_eur_per_kwh.mean(); cc = pk.groupby("hora").co2_kg_per_kwh.mean()
S["precio_hora_min"] = (int(pp.idxmin()), float(pp.min())); S["precio_hora_max"] = (int(pp.idxmax()), float(pp.max()))
S["co2_hora_min"] = (int(cc.idxmin()), float(cc.min())); S["co2_hora_max"] = (int(cc.idxmax()), float(cc.max()))
S["precio_ratio"] = float(pp.max() / pp.min()); S["co2_ratio"] = float(cc.max() / cc.min())
n = lambda x: (x - x.min()) / (x.max() - x.min())
fig, ax = plt.subplots()
ax.plot(pp.index, n(pp), color=COLORS["precio"], lw=2.5, label="Precio")
ax.plot(cc.index, n(cc), color=COLORS["co2"], lw=2.5, label="CO₂")
ax.set_xlabel("Hora del día"); ax.set_ylabel("Valor medio normalizado (0–1)"); ax.set_xlim(0, 23)
ax.set_title(f"Mínimo de CO₂ a las {S['co2_hora_min'][0]} h; mínimo de precio a las {S['precio_hora_min'][0]} h")
ax.legend(loc="lower right"); save(fig, "eda_perfiles"); plt.close(fig)

zp = (pk.precio_eur_per_kwh - pk.precio_eur_per_kwh.mean()) / pk.precio_eur_per_kwh.std()
zc = (pk.co2_kg_per_kwh - pk.co2_kg_per_kwh.mean()) / pk.co2_kg_per_kwh.std()
dif = (zp - zc).groupby(pk.hora).mean()
S["dif_max"] = (int(dif.idxmax()), float(dif.max())); S["dif_min"] = (int(dif.idxmin()), float(dif.min()))
S["barato_sucio_pct"] = float(((zp < -0.5) & (zc > 0.5)).mean() * 100)
S["caro_limpio_pct"] = float(((zp > 0.5) & (zc < -0.5)).mean() * 100)
S["dif_top"] = [int(x) for x in dif.sort_values().index[:3]], [int(x) for x in dif.sort_values().index[-3:]]
fig, axs = plt.subplots(1, 2, figsize=(8, 4.5), gridspec_kw={"width_ratios": [1, 1.15]})
ax = axs[0]
ax.hexbin(pk.precio_eur_per_kwh, pk.co2_kg_per_kwh, gridsize=30, cmap="Blues", mincnt=1, bins="log")
ax.set_xlabel("Precio (€/kWh)"); ax.set_ylabel("CO₂ (kg/kWh)"); ax.set_title(f"Correlación global r = {S['corr_all']:.2f}", fontsize=11)
ax = axs[1]
cols_ = [COLORS["precio"] if v > 0 else COLORS["co2"] for v in dif.values]
ax.bar(dif.index, dif.values, color=cols_)
ax.set_xlabel("Hora del día"); ax.set_ylabel("Precio − CO₂ (z-score medio)")
ax.set_title("Naranja: pesa más el precio · Azul: pesa más el CO₂", fontsize=8)
fig.suptitle("Precio y CO₂ no ordenan las horas igual: hay que combinarlos", fontsize=12, fontweight="bold")
save(fig, "eda_precio_vs_co2"); plt.close(fig)

# ---- 5. Calendario
h = h.copy(); hh = h.copy(); hh["hora"] = hh.index.hour; hh["fin"] = hh.index.dayofweek >= 5; hh["mes"] = hh.index.to_period("M")
wk = hh[~hh.fin].groupby("hora").load_kw.mean(); we = hh[hh.fin].groupby("hora").load_kw.mean()
S["load_lab"] = float(hh[~hh.fin].load_kw.mean()); S["load_fin"] = float(hh[hh.fin].load_kw.mean())
S["fin_pct"] = float((S["load_fin"] / S["load_lab"] - 1) * 100)
S["pico_lab"] = (int(wk.idxmax()), float(wk.max())); S["pico_fin"] = (int(we.idxmax()), float(we.max()))
mm = hh.groupby("mes").load_kw.mean()
S["load_mes"] = {str(k): round(float(v)) for k, v in mm.items()}
dd = h.load_kw.groupby(h.index.normalize()).mean()
S["dia_max"] = (str(dd.idxmax().date()), float(dd.max())); S["dia_min"] = (str(dd[dd > 100].idxmin().date()), float(dd[dd > 100].min()))
ago = dd[(dd.index.month == 8)]; ot = dd[(dd.index.month.isin([6, 7]))]
S["agosto_dias"] = len(ago); S["agosto_media"] = float(ago.mean()); S["junjul_media"] = float(ot.mean())
fig, axs = plt.subplots(1, 2, figsize=(8, 4.5), gridspec_kw={"width_ratios": [1.1, 1]})
ax = axs[0]
ax.plot(wk.index, wk.values, color=COLORS["demanda"], lw=2.2, label="Laborable")
ax.plot(we.index, we.values, color=COLORS["descarga"], lw=2.2, label="Fin de semana")
ax.set_xlabel("Hora del día"); ax.set_ylabel("Demanda media (kW)"); ax.legend(); ax.set_ylim(0, None)
ax = axs[1]
lab = [MES[(m.month - 9) % 12] for m in mm.index]
ax.bar(lab, mm.values, color=[COLORS["descarga"] if x == "Ago" else COLORS["demanda"] for x in lab])
ax.set_ylabel("Demanda media (kW)"); ax.tick_params(axis="x", labelsize=8)
fig.suptitle(f"Fin de semana {abs(S['fin_pct']):.0f} % menos demanda; agosto {abs(S['agosto_media']/S['junjul_media']-1)*100:.0f} % menos que jun–jul", fontsize=11, fontweight="bold")
save(fig, "eda_calendario"); plt.close(fig)

# ---- 6. Margen diario
pk["w"] = pk.co2_kg_per_kwh + LAM * pk.precio_eur_per_kwh
day = pk.groupby(pk.index.normalize()).w
cnt = day.count()
sp = (day.max() - day.min() / 0.9)[cnt == 24]
sp = sp[sp.index < "2026-09-01"]
S["spread_n"] = len(sp); S["spread_med"] = float(sp.median()); S["spread_p10"] = float(sp.quantile(.1)); S["spread_p90"] = float(sp.quantile(.9))
S["w_media"] = float(pk.w.mean()); S["spread_rel"] = float(sp.median() / pk.w.mean() * 100)
S["spread_neg"] = int((sp <= 0).sum())
spm = sp.groupby(sp.index.to_period("M")).median()
S["spread_mes"] = {str(k): round(float(v), 3) for k, v in spm.items()}
S["spread_mes_max"] = (str(spm.idxmax()), float(spm.max())); S["spread_mes_min"] = (str(spm.idxmin()), float(spm.min()))
ms = sorted(sp.index.to_period("M").unique())
fig, ax = plt.subplots()
data = [sp[sp.index.to_period("M") == m].values for m in ms]
bp = ax.boxplot(data, patch_artist=True, widths=0.6, showfliers=False, medianprops=dict(color="black"))
for b in bp["boxes"]:
    b.set_facecolor(COLORS["senal"]); b.set_alpha(0.7)
ax.set_xticklabels([MES[(m.month - 9) % 12] for m in ms]); ax.set_ylabel("Margen diario  máx(w) − mín(w)/0,9")
ax.axhline(0, color="k", lw=0.8)
ax.set_title(f"Margen diario mediano {S['spread_med']:.2f} ({S['spread_rel']:.0f} % de la señal media)".replace(".", ","))
save(fig, "eda_margen"); plt.close(fig)

for k, v in S.items():
    print(k, "=", v)
