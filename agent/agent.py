"""
agent.py — Repte UPC Sostenible (Datathon 2026)
Control óptimo de la batería del campus mediante MPC (Model Predictive Control) con
Programación Lineal sobre el horizonte de 24 h que el simulador nos da a conocer.

Idea central
------------
El Score oficial es   70 * dCO2(%) + 30 * dCoste(%)   respecto al campus sin batería.
Como los dos denominadores (CO2 y coste del caso base) son constantes, maximizar el Score
equivale a minimizar la energía importada de red ponderada por UNA sola señal horaria:

    w_t = co2_t + LAMBDA_PRICE * precio_t          (kg CO2-equivalente por kWh)
    LAMBDA_PRICE = (0.30 / 0.70) * (CO2_base / Coste_base)

A cada hora resolvemos un LP exacto (carga, descarga y SOC de las próximas horas conocidas)
y aplicamos solo la primera consigna (horizonte deslizante). La demanda neta del campus es
> 500 kW el 99,5 % de las horas, así que la batería nunca vierte a red y no hace falta
predecir consumo ni solar: basta con arbitrar bien la señal w_t.
"""

import numpy as np

try:
    from scipy.optimize import linprog
    _HAVE_LP = True
except Exception:  # entorno sin scipy: se usa la política de respaldo
    _HAVE_LP = False


class BatteryAgent:
    # --- Física de la batería (battery_spec.json) ---
    CAP_KWH = 2000.0
    P_MAX_KW = 500.0
    ETA = 0.9 ** 0.5          # rendimiento de carga = rendimiento de descarga
    EPS = 1e-4                # margen de seguridad para garantizar 0 infracciones

    # --- Parámetros de la estrategia ---
    LAMBDA_PRICE = 0.2593     # kg CO2-eq por euro (peso relativo del precio frente al CO2)
    SCALE = 10.0              # lleva la señal a O(1) para las tolerancias del solver
    TERMINAL_VALUE = 0.0      # valor del kWh almacenado al final del horizonte (señal escalada)

    def __init__(self):
        self._lp_cache = {}   # matrices del LP por longitud de horizonte
        self.n_steps = 0
        self.n_fallback = 0

    # ------------------------------------------------------------------ utilidades
    def _signal(self, obs):
        """Señal compuesta w_t para las horas conocidas (índice 0 = hora actual)."""
        prices = obs.get("preus_properes_24h")
        co2 = obs.get("co2_properes_24h")
        if prices is None or co2 is None or len(prices) == 0 or len(co2) == 0:
            prices, co2 = [obs["preu_actual"]], [obs["co2_actual"]]
        m = min(len(prices), len(co2))
        p = np.asarray(prices[:m], dtype=float)
        c = np.asarray(co2[:m], dtype=float)
        w = self.SCALE * (c + self.LAMBDA_PRICE * p)
        return np.nan_to_num(w, nan=float(np.nanmean(w)) if np.isfinite(w).any() else 1.0)

    def _net_load_estimate(self, obs):
        """Demanda neta esperada (kW) de la hora actual: persistencia de la última hora medida."""
        try:
            d = obs["noves_dades_5min"]
            net = float(d["ultim_consum_kw"]) - float(d["ultima_solar_kw"])
            return net if net == net else self.P_MAX_KW
        except Exception:
            return self.P_MAX_KW

    def _matrices(self, m):
        """Dinámica del SOC: s_k - s_{k-1} - eta*c_k + d_k/eta = 0  (s_{-1} = SOC actual)."""
        if m not in self._lp_cache:
            eye = np.eye(m)
            a_eq = np.concatenate([-self.ETA * eye, eye / self.ETA, eye - np.eye(m, k=-1)], axis=1)
            self._lp_cache[m] = a_eq
        return self._lp_cache[m]

    # ------------------------------------------------------------------ política
    def _plan(self, obs):
        w = self._signal(obs)
        m = len(w)
        soc = float(obs["soc_kwh"])
        a_eq = self._matrices(m)
        b_eq = np.zeros(m)
        b_eq[0] = soc
        cost = np.concatenate([w, -w, np.zeros(m)])
        # Solo damos valor terminal si el horizonte está completo (no al final de la simulación)
        if m >= 24:
            cost[-1] = -self.TERMINAL_VALUE
        d0_max = min(self.P_MAX_KW, max(0.0, self._net_load_estimate(obs)))  # no verter a red
        bounds = [(0.0, self.P_MAX_KW)] * m + [(0.0, d0_max)] + [(0.0, self.P_MAX_KW)] * (m - 1) \
            + [(0.0, self.CAP_KWH)] * m
        res = linprog(cost, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")
        if res.x is None or res.status != 0:
            raise RuntimeError("LP sin solución")
        return float(res.x[0] - res.x[m])

    def _fallback(self, obs):
        """Política de respaldo sin solver: cargar en el cuartil barato/limpio, descargar en el caro/sucio."""
        w = self._signal(obs)
        lo, hi = np.quantile(w, 0.25), np.quantile(w, 0.75)
        if w[0] <= lo and hi * 0.9 > w[0]:
            return self.P_MAX_KW
        if w[0] >= hi and w[0] * 0.9 > lo:
            return -min(self.P_MAX_KW, max(0.0, self._net_load_estimate(obs)))
        return 0.0

    def _clamp(self, action, obs):
        """Límites físicos exactos del simulador -> 0 infracciones."""
        soc = float(obs["soc_kwh"])
        max_c = max(0.0, min(self.P_MAX_KW, (self.CAP_KWH - soc) / self.ETA - self.EPS))
        max_d = max(0.0, min(self.P_MAX_KW, soc * self.ETA - self.EPS))
        if action != action:  # NaN
            action = 0.0
        action = float(min(max_c, max(-max_d, action)))
        return 0.0 if abs(action) < 1e-6 else action

    def act(self, obs: dict) -> float:
        self.n_steps += 1
        try:
            if not _HAVE_LP:
                raise RuntimeError("scipy no disponible")
            action = self._plan(obs)
        except Exception:
            self.n_fallback += 1
            try:
                action = self._fallback(obs)
            except Exception:
                action = 0.0
        return self._clamp(action, obs)
