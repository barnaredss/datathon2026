"""Semanas de baja demanda: ¿cuánto se pierde si el campus no puede absorber la descarga?

Las semanas del test son la última de cada mes e incluyen festivos (25-31 dic, 25-31 ago). Si la
demanda neta baja de 500 kW, descargar a potencia máxima vierte el exceso a red, sin ningún crédito.
Escenarios sintéticos sobre el pseudo-test: se escala la demanda de una o varias semanas.
Compara v2 (persistencia simple) y v3 (agente actual, perfil semanal) con la cota de información
perfecta. Nota: el perfil semanal de v3 se calcula con todo el entrenamiento, que incluye estas
semanas; con un perfil calculado sin ellas los resultados son prácticamente iguales.

Uso:  ./.venv/Scripts/python.exe -m analysis.lowload_study
"""
from tools.evaluate import load_hourly, pseudo_test, load_agent, run_agent, perfect_foresight, ROOT

V2 = load_agent(ROOT / "submissions" / "v2_meter_guard" / "agent.py")
V3 = load_agent(ROOT / "agent" / "agent.py")

pt = pseudo_test(load_hourly())
L, PV = pt.columns.get_indexer(["load_kw", "pv_kw"])


def scaled(blocks, f, tail=None):
    d = pt.copy()
    for b in blocks:
        a, e = b * 168, (b + 1) * 168
        if tail:
            a = e - tail
        d.iloc[a:e, L] = d.iloc[a:e, L] * f
        if f == 0:
            d.iloc[a:e, PV] = 0.0
    return d


def show(name, d):
    pf = perfect_foresight(d)
    r2, r3 = run_agent(V2, d), run_agent(V3, d)
    print("%-34s cota %.4f | v2 %.4f (gap %.4f) | v3 %.4f (gap %.4f) | infr %d/%d" % (
        name, pf, r2["score"], pf - r2["score"], r3["score"], pf - r3["score"], r2["infr"], r3["infr"]), flush=True)


if __name__ == "__main__":
    show("normal", pt)
    show("todas las semanas x0,80", scaled(range(10), 0.80))
    show("todas las semanas x0,65", scaled(range(10), 0.65))
    show("todas las semanas x0,50", scaled(range(10), 0.50))
    show("semana 4 x0,45", scaled([3], 0.45))
    show("semana 4 x0,35", scaled([3], 0.35))
    show("ultima semana x0,40", scaled([9], 0.40))
    show("semana 3 sin datos", scaled([2], 0.0))
    show("ultimas 72 h sin datos", scaled([9], 0.0, tail=72))
