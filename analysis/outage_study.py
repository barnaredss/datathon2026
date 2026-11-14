"""Robustez ante averías del contador: ¿qué pasa si una semana del test no tiene datos de demanda?

En los datos de entrenamiento falta todo noviembre en los cuatro ficheros de sensores y hay
15 horas con demanda 0 por caída del medidor. Si el test oculto contiene una semana así, una
batería que descarga sin demanda vierte a red (sin ningún crédito) y una que carga "para luego"
gasta energía que no puede entregar. Este script compara v1 (sin protección) y v2 (agente actual)
contra la cota de información perfecta en escenarios sintéticos.

Uso:  ./.venv/Scripts/python.exe -m analysis.outage_study
"""
from tools.evaluate import load_hourly, pseudo_test, load_agent, run_agent, perfect_foresight, ROOT

V1 = load_agent(ROOT / "submissions" / "v1_lp_mpc" / "agent.py")
V2 = load_agent(ROOT / "agent" / "agent.py")

full = load_hourly()
pt = pseudo_test(full)
cols = pt.columns.get_indexer(["load_kw", "pv_kw"])


def show(name, d):
    pf = perfect_foresight(d)
    r1, r2 = run_agent(V1, d), run_agent(V2, d)
    print("%-26s PF %.4f | v1 %.4f (gap %.4f) | v2 %.4f (gap %.4f) | infr %d/%d" % (
        name, pf, r1["score"], pf - r1["score"], r2["score"], pf - r2["score"], r1["infr"], r2["infr"]), flush=True)


if __name__ == "__main__":
    show("pseudo-test (normal)", pt)
    for blocks in [[2], [5], [0], [9], [2, 9]]:
        d = pt.copy()
        for b in blocks:
            d.iloc[b * 168:(b + 1) * 168, cols] = 0.0
        show("semanas sin datos %s" % blocks, d)
    d = pt.copy()
    d.iloc[4 * 168 + 30:4 * 168 + 100, cols] = 0.0
    show("averia 70 h en semana 4", d)
    d = pt.copy()
    d.iloc[3 * 168:4 * 168, cols[0]] = 200.0
    show("semana 3 con demanda 200 kW", d)
    show("train completo", full)
