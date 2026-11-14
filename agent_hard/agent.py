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
    from scipy.special import ndtri
    _HAVE_LP = True
except Exception:  # sin scipy: política de respaldo
    _HAVE_LP = False

PROFILES = None  # __PROFILES__


class BatteryAgent:
    ETA = 0.9 ** 0.5
    EPS = 1e-4
    ETA_PLAN = 0.9 ** 0.5   # rendimiento usado al planificar (menor = exige más margen para ciclar)
    SCALE = 10.0            # lleva la señal a O(1) para el solver
    PV_SCALE = 12.0         # el perfil solar de entrenamiento se multiplica por 12
    H = 24                  # horizonte de planificación (horas)
    N_TOTAL = 2016          # horas del test: permite vaciar la batería al final
    BLOCK_HOURS = 168       # el test son semanas completas
    SHRINK = 1.0            # <1 comprime la previsión de la señal hacia su media (horas no conocidas)
    LAMBDA_MULT = 1.0       # multiplicador del peso del precio
    USE_PV_GBM = True       # previsión de la solar de la hora actual con árboles
    PV_K0_FACTOR = 1.05     # factor sobre esa previsión
    NEWSVENDOR = True       # ajusta la consigna de la hora actual a la incertidumbre de la demanda neta
    NV_DISCHARGE = True
    NV_CHARGE = False
    Z_MARGINAL = 0.5        # margen (en sigmas) al descargar en una hora marginal
    SIG0 = 60.0             # desviación típica (kW) del error de demanda neta de la hora actual, de día
    SIG_NIGHT = 5.0         # ídem de noche (el contador repite el valor nocturno)
    SIG_PV = 0.25           # parte del error proporcional a la solar prevista
    USE_RIDGE = True        # previsión de precio y CO2 por regresión (si no, perfil reescalado)
    PV_UNCERT = 0.3         # fracción de la solar prevista que se resta al tope de descarga actual
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
        self.lam = float(p["lambda"]) * self.LAMBDA_MULT
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
        self.hist_start = 0         # primera fila con historia utilizable (puede ser anterior a la semana)
        self.prehist = p.get("prehist") or {}
        self.met = {}               # meteo de cada fila: (irradiancia, T panel, T ambiente, viento)
        g = p.get("pv_gbm") if self.USE_PV_GBM else None
        self.gbm = [tuple(tuple(a) for a in t) for t in g] if g else None
        self._new_block = False
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
        self._new_block = new_block
        if new_block:
            self.block_start = self.n
            self.hist_start = self.n
            self.block_month = ts.month
        self.ts = ts

    def _load_prehist(self):
        """Al empezar una semana de test, recupera las 48 h anteriores del año de entrenamiento.

        Las semanas de test son la última de cada mes y el entrenamiento llega hasta el día anterior,
        así que "ayer" y "anteayer" son datos oficiales conocidos (precio, CO2, demanda y solar).
        """
        j = 1
        while j <= 48:
            v = self.prehist.get((self.ts - timedelta(hours=j)).strftime("%Y-%m-%d %H"))
            if v is None:
                break
            row = self.n - j
            self.price[row], self.co2[row] = float(v[0]), float(v[1])
            if v[2] is None:
                self.load.pop(row, None); self.pv.pop(row, None)
            else:
                self.load[row], self.pv[row] = float(v[2]), float(v[3]) * self.PV_SCALE
            if len(v) >= 8 and v[4] is not None:
                self.met[row] = (float(v[4]), float(v[5]), float(v[6]), float(v[7]))
            else:
                self.met.pop(row, None)
            j += 1
        self.hist_start = self.n - (j - 1)

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
        for r in range(max(self.hist_start, self.n - self.LEVEL_WINDOW + 3), min(self.n + 3, end)):
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
        n, b0 = self.n, self.hist_start
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
        if self.SHRINK != 1.0 and m > 3:
            mean = float(w.mean())
            for k in range(m):
                if (n + k) not in self.price:
                    w[k] = mean + self.SHRINK * (w[k] - mean)
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
            if j in self.price and j < end and y >= self.hist_start and y in self.price:
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
                    if y >= self.hist_start and y in self.price:
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
        for r in range(self.n - 1, max(self.hist_start, self.n - 30) - 1, -1):
            if r in self.pv and used < 6:
                t = self.ts + timedelta(hours=r - self.n)
                prof = self.p_pv[self.block_month - 1][t.hour] * self.PV_SCALE
                if prof > 60.0:
                    num += self.pv[r]; den += prof; used += 1
                    if r == self.n - 1:
                        last = min(2.0, max(0.05, self.pv[r] / prof))
        avg = min(1.8, max(0.15, num / den)) if den > 0 else 1.0
        return avg, last

    def _pv_nowcast(self):
        """Solar de la hora actual (kW) con un modelo de árboles entrenado con el año oficial.

        Variables: producción de las dos últimas horas y de ayer a la misma hora, perfil mensual,
        claridad observada, irradiancia y temperaturas de la última hora, y el CO2 de la red de esta
        hora y la siguiente respecto a su perfil (red más limpia de lo normal = más sol). Los árboles
        se evalúan aquí mismo, sin depender de ninguna librería de modelos.
        """
        n, hs = self.n, self.hist_start
        if n - 1 < hs or (n - 1) not in self.pv:
            return None
        mo = self.block_month - 1

        def prof(j):
            return self.p_pv[mo][(self.ts + timedelta(hours=j - n)).hour] * self.PV_SCALE

        def get(d, j, i=None):
            if j < hs or j not in d:
                return -1.0
            return d[j] if i is None else d[j][i]

        pvp = prof(n)
        if pvp <= 30.0:
            return None
        pv1, pv2, pv24 = get(self.pv, n - 1), get(self.pv, n - 2), get(self.pv, n - 24)
        pvp1, pvp2 = prof(n - 1), prof(n - 2)
        cl1 = min(2.5, max(0.0, pv1 / pvp1)) if pvp1 > 60.0 else -1.0
        cl2 = min(2.5, max(0.0, pv2 / pvp2)) if (pvp2 > 60.0 and pv2 >= 0.0) else -1.0
        pers = pvp * (cl1 if cl1 >= 0.0 else 1.0)
        rc0 = self._ratio(n)[1] if n in self.co2 else -1.0
        rc1 = self._ratio(n + 1)[1] if ((n + 1) in self.co2 and n + 1 < self._block_end()) else -1.0
        x = (pv1, pv2, pv24, pvp, pvp1, cl1, cl2, get(self.met, n - 1, 0), get(self.met, n - 2, 0),
             get(self.met, n - 1, 1), get(self.met, n - 1, 2), get(self.met, n - 1, 3),
             rc0, rc1, float(self.ts.hour), float(mo), pers)
        s = 0.0
        for feat, thr, left, right, val in self.gbm:
            i = 0
            while feat[i] >= 0:
                i = left[i] if x[feat[i]] <= thr[i] else right[i]
            s += val[i]
        return max(0.0, s)

    def _net_load(self, m):
        """Previsión de demanda neta (demanda - solar) de las filas n .. n+m-1, en kW."""
        end = self._block_end()
        clear_avg, clear_last = self._clearness()
        last = self.n - 1 if self.n > 0 else 0
        have_last = last in self.load and (last >= self.hist_start or self.n == 0)
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
                if self.BETA_LOAD > 0 and y >= self.hist_start and y in self.load:
                    load = (1 - self.BETA_LOAD) * load + self.BETA_LOAD * self.load[y]
            else:
                load = clim
            clear = clear_avg
            if clear_last is not None:      # la nubosidad de la última hora persiste y se va diluyendo
                a = self.PV_ALPHA ** k
                clear = a * clear_last + (1 - a) * clear_avg
            pv = self.p_pv[mo][h] * self.PV_SCALE * (clear if r < end else 1.0) * self.PV_FACTOR
            if k == 0 and self.gbm is not None:
                now = self._pv_nowcast()
                if now is not None:
                    pv = now * self.PV_K0_FACTOR
            net[k] = load - pv
            if k == 0:
                self._pv0 = pv
        return net

    # ------------------------------------------------------------------ optimización
    def _matrices(self, m):
        if m not in self._lp:
            eye, zero = np.eye(m), np.zeros((m, m))
            a_eq = np.concatenate([-self.ETA_PLAN * eye, eye / self.ETA_PLAN, zero, eye - np.eye(m, k=-1)], axis=1)
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
            if "irradiancia_wm2" in nd:
                self.met[row] = (float(nd["irradiancia_wm2"]), float(nd.get("temp_panel_c", -1.0)),
                                 float(nd.get("temp_ambient_c", -1.0)), float(nd.get("vent_ms", -1.0)))
        if self._new_block:
            self._load_prehist()

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
        if last >= self.hist_start and last in self.load:
            net0 = min(net0, self.load[last] - self.pv[last])
        d_cap = np.minimum(self.pmax, np.maximum(0.0, net))
        # margen mayor cuanto más sol se espera: la solar es lo más incierto de la hora actual
        d_cap[0] = min(self.pmax, max(0.0, net0 * self.DISCHARGE_MARGIN - self.PV_UNCERT * self._pv0))
        if self.NEWSVENDOR and self.NV_DISCHARGE:
            d_cap[0] = min(self.pmax, max(0.0, net[0]))

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
        if self.NEWSVENDOR:
            return self._newsvendor(action, res, w[0], net[0], d_cap[0], m)
        # Excedente solar previsto: cargar algo más de lo estimado (si sobra sol y no se carga, se pierde;
        # si falta sol, se importa a la señal baja del mediodía)
        if net[0] < self.SURPLUS_BUFFER and action >= 0:
            action = max(action, min(self.pmax, max(0.0, -net[0]) * self.SURPLUS_BOOST + self.SURPLUS_BUFFER))
        return action

    def _newsvendor(self, a_lp, res, w0, n_hat, d_cap0, m):
        """Consigna de la hora actual con demanda neta incierta (problema del vendedor de periódicos).

        La consigna es fija durante la hora, pero la demanda neta real no se conoce. Descargar de más
        se vierte a red y se pierde; descargar de menos deja energía sin usar. Si mu es el valor del kWh
        almacenado (dual del LP) y w0 la señal de esta hora, lo óptimo es descargar hasta el cuantil
        1 - mu/(eta*w0) de la demanda neta, y absorber excedente solar hasta el cuantil mu*eta/w0.
        """
        try:
            mu = max(0.0, -float(res.eqlin.marginals[1])) if m > 1 else 0.0
        except Exception:
            return a_lp
        h = self.ts.hour
        night = self._pv0 < 1.0 and (h >= 22 or h <= 5)
        sigma = (self.SIG_NIGHT if night else self.SIG0) + self.SIG_PV * self._pv0
        if w0 <= 0:
            return a_lp
        if a_lp < -1e-6:                                   # el LP descarga
            if not self.NV_DISCHARGE:
                return a_lp
            ratio = mu / (self.ETA * w0)
            if -a_lp >= d_cap0 - 1e-6:                     # limitado por la demanda: cuantil óptimo
                q = min(0.999, max(0.001, 1.0 - ratio))
                return -min(self.pmax, max(0.0, n_hat + sigma * float(ndtri(q))))
            return -min(-a_lp, max(0.0, n_hat - self.Z_MARGINAL * sigma))   # limitado por energía
        if not self.NV_CHARGE:
            return a_lp
        ratio_c = mu * self.ETA / w0
        if ratio_c >= 1.0:                                 # compensa cargar de red: decide el LP
            return a_lp
        c_nv = -n_hat + sigma * float(ndtri(min(0.999, max(0.001, ratio_c))))
        if a_lp > max(0.0, -n_hat) + 1e-6:                 # el LP ya carga más que el excedente
            return max(a_lp, min(self.pmax, c_nv))
        return max(0.0, min(self.pmax, c_nv))              # absorber excedente incierto

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
