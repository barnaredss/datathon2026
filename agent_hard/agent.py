"""
agent.py — Repte UPC Sostenible (Datathon 2026) · MODO DIFÍCIL
Batería de 6.000 kWh / ±1.500 kW, fotovoltaica x12 y solo 3 horas de precio y CO2 conocidas.

Idea
----
El Score (70·dCO2 + 30·dCoste) es lineal en la energía importada de red, así que se reduce a
minimizar  sum_t  w_t · importación_t   con una única señal  w_t = CO2_t + LAMBDA · precio_t.
En el modo difícil faltan tres cosas que hay que PREVER a 24 h:
  1. la señal w_t más allá de las 3 horas conocidas (perfil mensual por tipo de día, reescalado al
     nivel observado, y mezclado con la misma hora del día anterior);
  2. la demanda del campus (última medida escalada con el perfil semanal);
  3. la solar (perfil mensual por hora multiplicado por la "claridad" observada en las últimas horas).
Con esas previsiones resolvemos cada hora un programa lineal exacto sobre 24 h (carga, descarga,
nivel de batería, importación de red con excedente solar gratuito) y aplicamos solo la primera hora.
Nunca se descarga por encima de la demanda neta estimada: lo que sobra se vierte a red sin crédito.
Todos los perfiles salen del año de entrenamiento oficial (data/train); no hay datos externos.
"""

from datetime import datetime, timedelta

import numpy as np

try:
    from scipy.optimize import linprog
    _HAVE_LP = True
except Exception:  # sin scipy: política de respaldo
    _HAVE_LP = False

PROFILES = None  # __PROFILES__


class BatteryAgent:
    ETA = 0.9 ** 0.5
    EPS = 1e-4
    SCALE = 10.0            # lleva la señal a O(1) para el solver
    PV_SCALE = 12.0         # el perfil solar de entrenamiento se multiplica por 12
    H = 24                  # horizonte de planificación (horas)
    N_TOTAL = 2016          # horas del test: permite vaciar la batería al final
    BLOCK_HOURS = 168       # el test son semanas completas
    USE_RIDGE = True        # previsión de precio y CO2 por regresión (si no, perfil reescalado)
    SURPLUS_BUFFER = 0.0    # kW extra de carga cuando se prevé excedente solar en la hora actual
    BETA_SIGNAL = 0.5       # peso de "misma hora de ayer" en la previsión de precio y CO2
    GAMMA = 0.0             # cuánto del cambio hoy-ayer ya observado se traslada a las horas siguientes
    DECAY = 1.0             # atenuación por hora de ese traslado
    PV_ALPHA = 0.0          # persistencia horaria de la nubosidad de la última hora (0 = no usar)
    SURPLUS_BOOST = 1.0     # factor sobre el excedente solar estimado al cargar en la hora actual
    BETA_LOAD = 0.0         # peso de "misma hora de ayer" en la previsión de demanda
    LEVEL_WINDOW = 24       # horas usadas para reescalar el perfil de precio y CO2
    DISCHARGE_MARGIN = 0.97 # factor sobre la demanda neta estimada de la hora actual
    PV_FACTOR = 1.1         # factor sobre la previsión solar (<1 = prudente)
    TERMINAL_VALUE = 0.0    # valor del kWh almacenado al final del horizonte (señal escalada)

    def __init__(self):
        p = PROFILES
        self.lam = float(p["lambda"])
        self.p_price = np.asarray(p["price"], dtype=float)     # [mes][laborable/finde][hora]
        self.p_co2 = np.asarray(p["co2"], dtype=float)
        self.p_pv = np.asarray(p["pv"], dtype=float)           # [mes][hora], kW sin escalar
        self.p_load = np.asarray(p["load_week"], dtype=float)  # [día*24 + hora]
        self.p_load_month = np.asarray(p["load_month"], dtype=float)
        rg = p.get("ridge")
        self.use_ridge = bool(rg) and self.USE_RIDGE
        if self.use_ridge:
            self.r_coef_p = np.asarray(rg["coef_p"], dtype=float)
            self.r_icpt_p = np.asarray(rg["icpt_p"], dtype=float)
            self.r_coef_c = np.asarray(rg["coef_c"], dtype=float)
            self.r_icpt_c = np.asarray(rg["icpt_c"], dtype=float)
        self.n = -1                 # índice de fila (hora) actual
        self.block_start = 0        # fila en la que empezó la semana actual
        self.block_month = 1
        self.ts = None
        self.price, self.co2, self.load, self.pv = {}, {}, {}, {}
        self.cap, self.pmax = 6000.0, 1500.0
        self._lp = {}
        self.n_fallback = 0

    # ------------------------------------------------------------------ reloj
    def _clock(self, obs):
        ts = obs.get("timestamp")
        try:
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.strip())
            if not isinstance(ts, datetime):
                raise ValueError
        except Exception:   # reloj no utilizable: lo reconstruimos con hora y día de la semana
            ts = datetime(2026, 6, 1) + timedelta(days=int(obs.get("day_of_week", 0)), hours=int(obs.get("hour", 0)))
        new_block = self.n == 0
        if self.ts is not None:
            gap = (ts - self.ts).total_seconds() / 3600.0
            new_block = gap > 2.5 or gap < 0.0
        if new_block:
            self.block_start = self.n
            self.block_month = ts.month
        self.ts = ts

    def _block_end(self):
        """Primera fila de la semana siguiente. Si la semana dura más de lo previsto, se alarga."""
        e = self.block_start + self.BLOCK_HOURS
        while e <= self.n:
            e += self.BLOCK_HOURS
        return e

    def _attrs(self, r):
        """(mes 0-11, tipo de día 0/1, hora, índice semanal) de la fila r >= n."""
        t = self.ts + timedelta(hours=r - self.n)
        month = self.block_month
        if r >= self._block_end():   # fila de la semana siguiente (un mes después)
            month = month % 12 + 1
        return month - 1, int(t.weekday() >= 5), t.hour, t.weekday() * 24 + t.hour

    # ------------------------------------------------------------------ previsiones
    def _levels(self):
        """Nivel observado / perfil, para precio y CO2, en las últimas horas conocidas de la semana."""
        end = self._block_end()
        sp = sc = cp = cc = 0.0
        for r in range(max(self.block_start, self.n - self.LEVEL_WINDOW + 3), min(self.n + 3, end)):
            if r in self.price:
                t = self.ts + timedelta(hours=r - self.n)
                mo, dt, h = self.block_month - 1, int(t.weekday() >= 5), t.hour
                sp += self.price[r]; cp += self.p_price[mo][dt][h]
                sc += self.co2[r]; cc += self.p_co2[mo][dt][h]
        return (sp / cp if cp > 0 else 1.0), (sc / cc if cc > 0 else 1.0)

    def _ratio(self, j):
        """Precio y CO2 de la fila j (conocida, de esta semana) divididos por su perfil."""
        t = self.ts + timedelta(hours=j - self.n)
        mo, dt, h = self.block_month - 1, int(t.weekday() >= 5), t.hour
        return self.price[j] / self.p_price[mo][dt][h], self.co2[j] / self.p_co2[mo][dt][h]

    def _signal_ridge(self, m):
        """Previsión de precio y CO2 por regresión lineal (una por cada hora de adelanto, 3..23 h).

        Variables: nivel relativo al perfil de las 3 horas conocidas, medias de las últimas 6 y 24 h,
        misma hora de ayer y de anteayer, y el cambio hoy-ayer ya observado. Los coeficientes se
        ajustaron con el año de entrenamiento (tools/hard.py::fit_signal_ridge).
        """
        n, b0 = self.n, self.block_start
        end = self._block_end()
        known = [j for j in (n, n + 1, n + 2) if j in self.price and j < end]
        top = known[-1]                              # última fila conocida dentro de la semana
        rat = {j: self._ratio(j) for j in range(max(b0, n - 21), top + 1) if j in self.price}
        seq = [rat[j] for j in sorted(rat)]
        p_all = [x[0] for x in seq]; c_all = [x[1] for x in seq]
        k3 = [rat[j] for j in (top, max(top - 1, n), n)] if top >= n else [seq[-1]] * 3
        p2, p1, p0 = (x[0] for x in k3)
        c2, c1, c0 = (x[1] for x in k3)
        p6, c6 = float(np.mean(p_all[-6:])), float(np.mean(c_all[-6:]))
        p24, c24 = float(np.mean(p_all[-24:])), float(np.mean(c_all[-24:]))
        dpy = dcy = 0.0
        if top - 24 >= b0 and (top - 24) in self.price:
            ry = self._ratio(top - 24)
            dpy, dcy = rat[top][0] - ry[0], rat[top][1] - ry[1]
        pos = min(n - b0, 48)
        w = np.empty(m)
        for k in range(m):
            r = n + k
            if r in self.price:
                p, c = self.price[r], self.co2[r]
            else:
                mo, dt, h, _ = self._attrs(r)
                p, c = self.p_price[mo][dt][h], self.p_co2[mo][dt][h]
                if r < end and 3 <= k <= 23:
                    py, cy = (self._ratio(r - 24) if (r - 24 >= b0 and (r - 24) in self.price) else (p24, c24))
                    py2, cy2 = (self._ratio(r - 48) if (r - 48 >= b0 and (r - 48) in self.price) else (p24, c24))
                    f = np.array([k, h, dt, mo, self.ts.hour, pos, p2, p1, p0, p6, p24,
                                  c2, c1, c0, c6, c24, py, cy, dpy, dcy, py2, cy2])
                    i = k - 3
                    p *= min(3.0, max(0.1, float(self.r_coef_p[i] @ f) + self.r_icpt_p[i]))
                    c *= min(3.0, max(0.1, float(self.r_coef_c[i] @ f) + self.r_icpt_c[i]))
                elif r < end:
                    p, c = p * p6, c * c6
            w[k] = self.SCALE * (c + self.lam * p)
        return w

    def _signal(self, m):
        if self.use_ridge:
            return self._signal_ridge(m)
        lp, lc = self._levels()
        end = self._block_end()
        # Cambio de hoy respecto a ayer en las horas ya conocidas (precio y CO2)
        dp = dc = 0.0
        cnt = 0
        for j in range(self.n, self.n + 3):
            y = j - 24
            if j in self.price and j < end and y >= self.block_start and y in self.price:
                dp += self.price[j] - self.price[y]; dc += self.co2[j] - self.co2[y]; cnt += 1
        if cnt:
            dp, dc = dp / cnt, dc / cnt
        w = np.empty(m)
        for k in range(m):
            r = self.n + k
            if r in self.price:
                p, c = self.price[r], self.co2[r]
            else:
                mo, dt, h, _ = self._attrs(r)
                p, c = self.p_price[mo][dt][h], self.p_co2[mo][dt][h]
                if r < end:
                    p, c = p * lp, c * lc
                    y = r - 24
                    if y >= self.block_start and y in self.price:
                        b = self.BETA_SIGNAL
                        g = self.GAMMA * self.DECAY ** (k - 2)
                        p = (1 - b) * p + b * max(0.0, self.price[y] + g * dp)
                        c = (1 - b) * c + b * max(0.0, self.co2[y] + g * dc)
            w[k] = self.SCALE * (c + self.lam * p)
        return w

    def _clearness(self):
        """Producción observada / perfil: (media de las últimas horas de sol, última hora de sol o None)."""
        num = den = 0.0
        used = 0
        last = None
        for r in range(self.n - 1, max(self.block_start, self.n - 30) - 1, -1):
            if r in self.pv and used < 6:
                t = self.ts + timedelta(hours=r - self.n)
                prof = self.p_pv[self.block_month - 1][t.hour] * self.PV_SCALE
                if prof > 60.0:
                    num += self.pv[r]; den += prof; used += 1
                    if r == self.n - 1:
                        last = min(2.0, max(0.05, self.pv[r] / prof))
        avg = min(1.8, max(0.15, num / den)) if den > 0 else 1.0
        return avg, last

    def _net_load(self, m):
        """Previsión de demanda neta (demanda - solar) de las filas n .. n+m-1, en kW."""
        end = self._block_end()
        clear_avg, clear_last = self._clearness()
        last = self.n - 1 if self.n > 0 else 0
        have_last = last in self.load and (last >= self.block_start or self.n == 0)
        mean_week = float(self.p_load.mean())
        net = np.empty(m)
        for k in range(m):
            r = self.n + k
            mo, _, h, widx = self._attrs(r)
            clim = self.p_load_month[mo] * self.p_load[widx] / mean_week
            if r < end and have_last:
                tl = self.ts + timedelta(hours=last - self.n)
                ref = self.p_load[tl.weekday() * 24 + tl.hour]
                load = self.load[last] * self.p_load[widx] / ref
                y = r - 24
                if self.BETA_LOAD > 0 and y >= self.block_start and y in self.load:
                    load = (1 - self.BETA_LOAD) * load + self.BETA_LOAD * self.load[y]
            else:
                load = clim
            clear = clear_avg
            if clear_last is not None:      # la nubosidad de la última hora persiste y se va diluyendo
                a = self.PV_ALPHA ** k
                clear = a * clear_last + (1 - a) * clear_avg
            pv = self.p_pv[mo][h] * self.PV_SCALE * (clear if r < end else 1.0) * self.PV_FACTOR
            net[k] = load - pv
        return net

    # ------------------------------------------------------------------ optimización
    def _matrices(self, m):
        if m not in self._lp:
            eye, zero = np.eye(m), np.zeros((m, m))
            a_eq = np.concatenate([-self.ETA * eye, eye / self.ETA, zero, eye - np.eye(m, k=-1)], axis=1)
            a_ub = np.concatenate([eye, -eye, -eye, zero], axis=1)   # c - d - g <= -net
            self._lp[m] = (a_eq, a_ub)
        return self._lp[m]

    def _decide(self, obs):
        n = self.n
        self._clock(obs)
        self.cap = float(obs.get("cap_max_kwh", self.cap))
        self.pmax = float(obs.get("power_max_kw", self.pmax))
        pr, co = obs["preus_properes_24h"], obs["co2_properes_24h"]
        known = min(len(pr), len(co))
        for j in range(known):
            self.price[n + j], self.co2[n + j] = float(pr[j]), float(co[j])
        nd = obs.get("noves_dades_5min") or {}
        if "ultim_consum_kw" in nd:
            row = n - 1 if n > 0 else 0
            self.load[row] = float(nd["ultim_consum_kw"])
            self.pv[row] = float(nd.get("ultima_solar_kw", 0.0))

        m = self.H
        if known < 3:                       # el simulador avisa del final: quedan `known` horas
            m = max(1, known)
        elif self.N_TOTAL - n >= 1:
            m = max(1, min(self.H, self.N_TOTAL - n))
        w = self._signal(m)
        net = self._net_load(m)
        # Hora actual: prudencia al descargar (verter a red se pierde entero)
        last = n - 1
        net0 = net[0]
        if last >= self.block_start and last in self.load:
            net0 = min(net0, self.load[last] - self.pv[last])
        d_cap = np.minimum(self.pmax, np.maximum(0.0, net))
        d_cap[0] = min(self.pmax, max(0.0, net0 * self.DISCHARGE_MARGIN))

        soc = float(obs["soc_kwh"])
        a_eq, a_ub = self._matrices(m)
        b_eq = np.zeros(m)
        b_eq[0] = soc
        cost = np.concatenate([np.zeros(2 * m), w, np.zeros(m)])
        cost[-1] = -self.TERMINAL_VALUE
        bounds = [(0.0, self.pmax)] * m + [(0.0, float(x)) for x in d_cap] + [(0.0, None)] * m + [(0.0, self.cap)] * m
        res = linprog(cost, A_ub=a_ub, b_ub=-net, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")
        if res.x is None or res.status != 0:
            raise RuntimeError("LP sin solución")
        action = float(res.x[0] - res.x[m])
        # Excedente solar previsto: cargar algo más de lo estimado (si sobra sol y no se carga, se pierde;
        # si falta sol, se importa a la señal baja del mediodía)
        if net[0] < self.SURPLUS_BUFFER and action >= 0:
            action = max(action, min(self.pmax, max(0.0, -net[0]) * self.SURPLUS_BOOST + self.SURPLUS_BUFFER))
        return action

    def _fallback(self, obs):
        """Sin solver: cargar al mediodía, descargar por la tarde-noche sin superar la demanda neta."""
        h = int(obs.get("hour", 12))
        nd = obs.get("noves_dades_5min") or {}
        net = float(nd.get("ultim_consum_kw", 0.0)) - float(nd.get("ultima_solar_kw", 0.0))
        if 10 <= h <= 16:
            return self.pmax
        if h >= 18 or h <= 8:
            return -min(self.pmax, max(0.0, 0.9 * net))
        return 0.0

    def _clamp(self, action, obs):
        soc = float(obs["soc_kwh"])
        cap = float(obs.get("cap_max_kwh", self.cap))
        pmax = float(obs.get("power_max_kw", self.pmax))
        max_c = max(0.0, min(pmax, (cap - soc) / self.ETA - self.EPS))
        max_d = max(0.0, min(pmax, soc * self.ETA - self.EPS))
        if action != action:
            action = 0.0
        action = float(min(max_c, max(-max_d, action)))
        return 0.0 if abs(action) < 1e-6 else action

    def act(self, obs: dict) -> float:
        self.n += 1
        try:
            if not _HAVE_LP:
                raise RuntimeError("scipy no disponible")
            action = self._decide(obs)
        except Exception:
            self.n_fallback += 1
            try:
                action = self._fallback(obs)
            except Exception:
                action = 0.0
        return self._clamp(action, obs)
