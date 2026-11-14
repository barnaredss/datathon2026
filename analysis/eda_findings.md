# Hallazgos de la auditoría de datos (T4)

Fuente: `data/train/*.csv`, tablas horarias `data/hourly_train.csv` (5.993 h) y `data/hourly_price_co2.csv` (6.768 h). Script: `analysis/eda.py`.

## 1. Cobertura y calidad
1. El contador tiene 74.210 filas de 5 min, sin timestamps duplicados. Faltan 11 bloques de exactamente 7 días: la última semana de cada mes (la que se reserva para el test). Quedan 21-24 días por mes en el entrenamiento.
2. Noviembre 2025 no tiene carga porque los cuatro ficheros de sensores (contador, inversor, meteo, entradas_salidas) solo tienen 1 fila en ese mes (hueco de 30 días). Precio y CO2 sí cubren noviembre (552 h): 6.768 h frente a 5.993 h con carga.
3. El inversor termina el 16-ago-2026 (el contador sigue hasta el 24-ago): agosto solo tiene 16 días con FV y carga (379 h).
4. Dos huecos cortos: 2,5 h el 17-jun-2026 (17:25) y 5,6 h el 4-ago-2026 (12:40).
5. Hay 197 lecturas de 5 min con potencia 0 (la carga se recorta a 0): 167 son una caída del contador del 17-jun 17:25 al 18-jun (~14 h); 22 el 6-ago (07:35-09:20); 5 el 20-ene; 1 el 16-ene; 2 el 5-ago. En la tabla horaria: 15 horas con carga 0 (17-jun, 18-jun, 6-ago). Son averías del medidor, no consumo real; no afectan a la estrategia pero sesgan la media de agosto (~1 %).

## 2. La carga nocturna está congelada (dato sospechoso)
6. En 246 de 260 días el contador mantiene EXACTAMENTE el mismo valor durante unas 96 lecturas seguidas (22:05 → 06:00, 8 h): 0,996 valores distintos por noche (0-6 h) frente a 110 valores distintos en 8-20 h. Esas filas congeladas son el 33,5 % del total.
7. Por eso la media horaria de las horas 0-5 es idéntica (972,968 kW): cada noche aporta un único valor a las 6 horas. No es un artefacto de `build_hourly.py`: el dato bruto ya viene plano (192 valores distintos en la hora 3 de 250 días, uno por noche). La hora 23 (975,7 kW) también es casi idéntica; la hora 22 se desvía por la primera lectura.
8. El salto al reanudarse la lectura a las 06:05 es de 142 kW de media frente a 44 kW de variación típica entre lecturas diurnas. Interpretación: el medidor deja de actualizarse de noche (valor repetido o imputado, probablemente integra en el contador de curva de carga). Los valores son enteros (99,996 %), con solo 1.899 niveles distintos en todo el año.
9. Consecuencia: el consumo nocturno real es desconocido y la estrategia no debe fiarse de la "última carga" observada de noche. Aun así, la carga neta es siempre > 500 kW en 22-6 h (~975 kW), por lo que no hay riesgo de vertido.

## 3. Escala
10. Demanda media 1.123 kW, pico horario 2.503 kW; FV media 26,5 kW, pico horario 144 kW: la FV es el 2,36 % de la energía (7,0 % de la demanda en su hora punta, 13 h).
11. Carga neta < 500 kW solo en el 0,52 % de las horas; neta < 0 en el 0,00 % (mínimo 0). Figura `eda_escala.png`. La batería (500 kW) nunca llega a verter.

## 4. Señales de precio y CO2
12. Precio medio 0,139 €/kWh (rango 0,003-0,399; ninguna hora negativa). CO2 medio 0,0852 kg/kWh (0,028-0,222). Figuras `eda_heatmaps.png`, `eda_perfiles.png`.
13. El precio es mínimo a las 14 h (0,076 €/kWh) y máximo a las 21 h (0,235; ratio 3,1x). El CO2 es mínimo a las 13 h (0,052) y máximo a las 21 h (0,111; ratio 2,1x). Ambos tienen su valle al mediodía (solar) y su pico por la tarde-noche.
14. Correlación horaria precio-CO2: r = 0,58 global; por mes entre 0,39 (feb) y 0,70 (mar), nunca negativa.
15. Discrepancias (`eda_precio_vs_co2.png`, diferencia de z-scores precio − CO2 por hora): de 0-7 h el CO2 está por encima de su media y el precio por debajo (pesa más el CO2, hasta -0,72 a las 5 h); de 18-21 h las dos señales son altas, pero el precio sube mucho más que el CO2 (+0,95 a las 20 h); de 10-13 h el CO2 ya está en su valle solar y el precio todavía no. Las señales rara vez se contradicen del todo (solo el 0,16 % de las horas son a la vez claramente baratas y sucias, y el 4,2 % claramente caras y limpias), pero no ordenan las horas igual. Por eso hay que combinarlas en una sola señal.
16. Febrero 2026 es anómalo: la señal es plana (correlación 0,39, margen diario mediano 0,036) con precio y CO2 bajos todo el día.

## 5. Calendario
17. Fin de semana: demanda media 808 kW frente a 1.245 kW en laborables (-35 %). El laborable tiene un pico de 1.547 kW a las 11 h (`eda_calendario.png`).
18. Mensual: máximo en julio (1.449 kW), mínimo en abril (999 kW). Agosto (16 días) baja a 838 kW, un 39 % menos que jun-jul (1.371 kW), coherente con el cierre vacacional.
19. Aun el día de menor demanda media (5-oct, 665 kW) deja la carga neta por encima de los 500 kW de la batería.

## 6. Margen disponible para la batería
20. Con `w = CO2 + 0,2593·precio` (media 0,121), el margen diario máx(w) - mín(w)/0,9 tiene mediana 0,103 (85 % de la señal media), P10 = 0,040 y P90 = 0,169 sobre 281 días completos. Ningún día tiene margen ≤ 0: siempre hay algo que ganar (`eda_margen.png`).
21. Estacionalidad del margen: mínimo en febrero (mediana 0,036), máximo en agosto (0,181); jul-ago concentran los días de más margen.

## Implicaciones para la estrategia
- La carga neta nunca baja de 500 kW: la batería nunca exporta y predecir carga o FV no aporta; es arbitraje puro de la señal combinada.
- Los datos de carga nocturnos están congelados (33 % de las filas): no usar la carga observada de noche como información fiable ni construir modelos de demanda sobre ella.
- Precio y CO2 discrepan por horas (r = 0,58): una señal compuesta es necesaria; el valle de la señal es el mediodía (13-14 h) y el pico las 18-21 h; de madrugada el CO2 es alto aunque el precio sea bajo.
- El margen diario es siempre positivo y varía 5x entre meses; el valor de la batería depende más de la estacionalidad de las señales que de la demanda.
