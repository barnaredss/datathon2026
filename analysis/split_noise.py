"""Ruido del reparto público/privado: ¿cuánto se mueve el score de MEDIA semana al mover lambda?

El leaderboard público puntúa solo el 50 % de las horas de cada semana, pero la batería se simula
sobre todas. Si un cambio mínimo en el peso lambda desplaza una carga a una hora "privada" y su
descarga a una hora "pública", la mitad pública mejora y la privada empeora en la misma medida,
aunque el score del test completo no cambie. Este script lo mide sobre el pseudo-test con varios
repartos posibles (no conocemos el real).

Uso:  ./.venv/Scripts/python.exe -m analysis.split_noise
"""
import numpy as np

from tools.evaluate import load_hourly, pseudo_test, load_agent, run_agent, precise_score, ROOT

if __name__ == "__main__":
    A = load_agent(ROOT / "agent" / "agent.py")
    pt = pseudo_test(load_hourly())
    n = len(pt)
    pos = np.arange(n) % 168
    rng = np.random.default_rng(0)
    masks = {
        "completo": np.ones(n, bool),
        "1a mitad sem.": pos < 84,
        "2a mitad sem.": pos >= 84,
        "dias pares": (pos // 24) % 2 == 0,
        "dias impares": (pos // 24) % 2 == 1,
        "horas al azar": rng.random(n) < 0.5,
    }
    print("%-8s" % "lambda" + "".join("%15s" % k for k in masks))
    for lam in [0.18, 0.21, 0.23, 0.2517, 0.2593, 0.27, 0.29, 0.32, 0.36]:
        V = type("V", (A,), {"LAMBDA_PRICE": lam})
        g = np.asarray(run_agent(V, pt)["env"].grid)
        print("%-8.4f" % lam + "".join("%15.4f" % precise_score(pt[m], g[m])[0] for m in masks.values()), flush=True)
