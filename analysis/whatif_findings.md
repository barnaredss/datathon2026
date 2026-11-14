# Hallazgos what-if para UPC Sostenible (T6)

Fuente: `analysis/whatif.py`; números en `analysis/cache/whatif_results.json`. Train completo (5.993 h), LP de
información perfecta parametrizado, batería inicial al 50 %, exportar no da nada. Anualizado con x 8760/5993.
Comprobación: batería actual (2000 kWh, 500 kW, 90 %, FV x1, alfa 0,7) = 5,6753, igual que `tools/evaluate.py`.
Hoy: ΔCO2 5,271 %, ΔCoste 6,619 %, 42,5 t CO2/año y 90.905 EUR/año (base: 551,8 t CO2 y 939.634 EUR en 5.993 h).

## 1. Dimensionado (whatif_dimensionado.png)
- Ahorro (miles EUR/año) a 500 kW: 500 kWh 32; 1000 kWh 56; 2000 kWh 91 (hoy); 4000 kWh 111; 8000 kWh 116.
- A 2000 kWh: 250 kW 55; 500 kW 91; 1000 kW 112; 2000 kW 118. CO2 evitado (t/año) a 2000 kWh: 36, 43, 47, 48.
- Duplicar solo la energía (4000 kWh, 500 kW): +19,9 mil EUR (+22 %), +28,8 t CO2. Duplicar solo la potencia
  (2000 kWh, 1000 kW): +21,4 mil EUR (+23 %), +4,4 t CO2. Duplicar ambas (4000 kWh, 1000 kW): 180,5 mil EUR (+98 %).
- Valor marginal local en la batería actual (+200 kWh o +50 kW): el siguiente kWh vale 19,0 EUR/año y 17,5 kg CO2/año;
  el siguiente kW vale 79,3 EUR/año y 13,7 kg CO2/año (en score: +0,0019 por kWh, +0,0029 por kW).
- Lectura: energía y potencia son complementarias. Duplicar solo una da ≈ +22 % en euros; duplicar las dos, +98 %.
  En CO2 (el 70 % del Score) pesa mucho más la energía: +28,8 t al duplicar los kWh frente a +4,4 t al duplicar los kW.
  Los marginales (79 EUR por kW, 19 EUR por kWh) no son comparables entre sí sin conocer el coste de cada unidad.
  Con 250 kW se pierde el 39 % del ahorro; con 8000 kWh a 500 kW la potencia satura (116 mil EUR, solo +28 %).
- Payback (supuesto ilustrativo, no es dato oficial): a 300-500 EUR/kWh instalado, 2000 kWh cuestan 0,6-1,0 M EUR
  y se amortizan en 6,6-11 años solo con este ahorro.

## 2. Rendimiento (whatif_rendimiento.png)
- Rendimiento ida y vuelta -> EUR/año | t CO2/año: 80 %: 72.891 | 34,8; 85 %: 81.743 | 38,5; 90 % (hoy): 90.905 | 42,5;
  92 %: 94.835 | 44,2; 95 %: 100.175 | 47,0; 98 %: 106.260 | 50,1.
- Cada punto de rendimiento vale unos 1.850-1.900 EUR/año y 0,9 t CO2/año. De 90 % a 98 %: +15.355 EUR (+16,9 %).

## 3. Energía solar (whatif_solar.png)
- La FV actual es el 2,4 % de la energía. El primer excedente aparece al escalar la FV por encima de x4,25
  (a ese factor la FV es ≈ 10 % de la energía; con x5 hay 16 h con excedente, 1,0 MWh/año).
- Valor de la batería (EUR/año | t CO2/año): x1 90.905 | 42,5; x3 90.981 | 42,5; x5 90.951 | 42,5; x8 93.662 | 45,0;
  x10 96.961 | 47,8; x15 109.107 | 56,4; x20 123.127 | 64,8. Sin excedente la batería no gana nada con más FV.
- Excedente perdido (no se paga): x8 55,6 MWh/año (3,0 % de la FV); x10 145,7 MWh (6,3 %); x15 574,9 MWh (16,5 %);
  x20 1.261,6 MWh (27,2 %). La batería guarda parte de él gratis, por eso su valor sube un 3 % a x8 y un 35 % a x20.
- Ahorro combinado FV + batería frente a no tener ni FV ni batería: x1 115,5 mil EUR; x10 334,9 mil; x20 513,7 mil.

## 4. Pesos CO2 / coste (whatif_pesos.png)
- Alfa -> ΔCO2 % | ΔCoste % | t CO2/año | EUR/año: 0: 2,452 | 8,113 | 19,8 | 111.423; 0,3: 4,078 | 7,841 | 32,9 | 107.697;
  0,5: 4,774 | 7,373 | 38,5 | 101.261; 0,7 (oficial): 5,271 | 6,619 | 42,5 | 90.905; 1: 5,669 | 3,940 | 45,7 | 54.108.
- Marginal (EUR perdidos por cada t de CO2 evitada extra): 0 -> 0,3: 284; 0,3 -> 0,5: 1.147; 0,5 -> 0,7: 2.585;
  0,7 -> 1: 11.465 EUR/t. La curva es cóncava: el último CO2 es cada vez más caro.
- Precio del carbono implícito en el 70/30 (bases de train): lambda = (0,3/0,7) x 551.822,5 kg / 939.634,2 EUR =
  0,2517 kg/EUR; 1/lambda = 3,973 EUR/kg = 3.973 EUR/t CO2 (con el 0,2593 calibrado en el leaderboard: 3.857 EUR/t).

## 5. Regla del operador (whatif_operador.png, bucle sobre `CampusBatteryEnv` con el clamp del agente, 0 infracciones)
- A carga 13-17 y 1-4 / descarga 7-9 y 19-22: 2,8153 (49,6 % del óptimo). B carga 11-16 / descarga 18-23: 3,3603 (59,2 %).
- C carga 12-16 / descarga 20-23: 4,1626 (73,3 %). D carga 12-16 y 3-4 / descarga 6-8 y 20-23: 4,1040 (72,3 %).
- E (mejor): carga 12-16 todo el año; descarga 18-21 de octubre a marzo y 20-23 de abril a septiembre:
  4,4945 (79,2 % del óptimo, ΔCO2 4,199 %, ΔCoste 5,183 %). Horarios ajustados sobre train (en muestra).
- Regla para el responsable: "Cargar a máxima potencia de 12 a 16 h; descargar a máxima potencia en las 4 horas
  de la tarde-noche (18-21 h en invierno, 20-23 h en verano); el resto del día, quieta."
- El 21 % restante exige mirar los precios y el CO2 del día: ahí está el valor del MPC (99,85 % del óptimo).

## Recomendaciones para UPC Sostenible
- Dimensionado: crecer en energía y potencia a la vez (4000 kWh y 1000 kW duplican el ahorro: 180 mil EUR/año).
  Si solo se amplía una, en euros da igual (≈ +20 mil EUR/año cada una), pero para el CO2 conviene la energía
  (+28,8 t/año frente a +4,4 t). Solo 8000 kWh a 500 kW no pasa de 116 mil EUR: la potencia satura.
- Rendimiento: cada punto de rendimiento vale ≈ 1.900 EUR/año; exigirlo en la compra (98 % frente a 90 %: +15 mil EUR/año).
- Más FV: con la FV actual (x1) la batería no mejora; solo a partir de x4,25 hay excedente a mediodía y la batería
  lo aprovecha (+3 % a x8). Si se amplía la FV, hacerlo junto con más batería para no tirar excedente.
- Pesos 70/30: equivalen a pagar ≈ 3.973 EUR por t de CO2. Subir alfa a 1 cuesta ≈ 11.465 EUR por cada t extra,
  por eso 0,7 queda en el codo; el último CO2 es caro y la fórmula oficial ya lo equilibra.
