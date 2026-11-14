# Hallazgos de estrategia (T5)

Fuente: `analysis/strategy.py`, números en `analysis/cache/strategy_results.json`.

## 1. Escalera de referencias (est_escalera.png)  train completo | pseudo-test
- Sin batería: 0.0000 (0.00 % del óptimo) | 0.0000 (0.00 % del óptimo)
- Plantilla oficial, antes de penalizar: 1.2706 (22.39 % del óptimo) | 1.4809 (24.18 % del óptimo)
- Solo precio: 4.1218 (72.63 % del óptimo) | 4.6796 (76.40 % del óptimo)
- Solo CO2: 5.1417 (90.60 % del óptimo) | 5.6588 (92.39 % del óptimo)
- Nuestro MPC: 5.6667 (99.85 % del óptimo) | 6.1241 (99.99 % del óptimo)
- Información perfecta: 5.6753 (100.00 % del óptimo) | 6.1250 (100.00 % del óptimo)
- Plantilla oficial con penalización (0,20 por infracción): 0.0000 con 46 infracciones | 1.0809 con 2 infracciones

## 2. Valor del horizonte (est_horizonte.png, pseudo-test)
- H=1: 0.0872; H=2: 1.7778; H=4: 4.5869; H=6: 5.7262; H=8: 6.0361; H=12: 6.1235; H=18: 6.1243; H=24: 6.1241
- Cota de información perfecta: 6.1250. H=24 deja 0.0009 puntos por ganar; H=1 pierde 6.0369 respecto a H=24.

## 3. Frontera CO2–coste (est_pareto.png, pseudo-test)
- λ=0: ΔCO2 6.110 %, ΔCoste 4.607 %, score 5.6588
- λ=0.1: ΔCO2 5.996 %, ΔCoste 6.104 %, score 6.0286
- λ=0.2593: ΔCO2 5.715 %, ΔCoste 7.078 %, score 6.1241
- λ=1: ΔCO2 4.874 %, ΔCoste 8.053 %, score 5.8278
- λ=5: ΔCO2 3.598 %, ΔCoste 8.435 %, score 5.0494
- Scores del resto: λ=0.02: 5.7895; λ=0.05: 5.9056; λ=0.15: 6.0931; λ=0.2: 6.1205; λ=0.35: 6.1054; λ=0.5: 6.0404; λ=0.75: 5.9170; λ=1.5: 5.5844; λ=2: 5.4664; λ=3: 5.2905
- Mejor score del barrido: λ=0.2593 (6.1241); el nuestro (0,2593) da 6.1241.

## 4. Semana de ejemplo (est_semana.png)
- Bloque 3 del pseudo-test, del 2025-12-18 al 2025-12-24, elegido por ser el más cercano a la mediana de actividad de la batería.

## 5. Perfil horario (est_horas.png, train completo)
- Horas con carga media > 20 kW: [0, 1, 2, 3, 4, 11, 12, 13, 14, 15, 16, 17]; con descarga media < -20 kW: [6, 7, 8, 10, 18, 19, 20, 21, 22, 23].
- Pico medio de carga 470 kW a las 14 h; pico medio de descarga -379 kW a las 21 h.

## 6. Números para la presentación
- Ciclos equivalentes por día: 1.384 (train), 1.398 (pseudo-test).
- kWh entregados al campus por día: 2627 (train); cargados desde red: 2914.
- Train completo (5993 h): 28937.3 kg CO2 evitados, 62516.34 € ahorrados.
- Anualizado (x 8760/5993): 42298 kg CO2/año = 42.30 t, 91380 €/año.
- Tiempo de ejecución: 22.4 s en 5993 h (~7.6 s por 2016 h); infracciones 0 (train), 0 (pseudo-test); respaldos usados 0.
- Resultado real en el leaderboard (mitad pública, 1008 h): score 6,43; ΔCO2 5,96 %; ΔCoste 7,52 %; 4282,5 kg CO2; 8934,63 €; 0 infracciones. Mejor puntuación pública de cualquier equipo: 6,43.
- Valor de conocer la demanda actual (tope de descarga de la hora actual), score:
  - train: v1 (última hora medida) 5.6667; demanda real 5.6740 (+0.0072); sin tope (500 kW) 5.6556 (-0.0111, infracciones 0).
  - pseudo-test: v1 (última hora medida) 6.1241; demanda real 6.1241 (+0.0000); sin tope (500 kW) 6.1241 (+0.0000, infracciones 0).

## Mensajes para el jurado
- Alcanzamos el 99.85 % del óptimo con información perfecta de todo el año, con solo 24 h de previsión oficial y 0 infracciones.
- La señal única CO2 + λ·precio supera claramente a usar solo precio (4.6796) o solo CO2 (5.6588) en pseudo-test.
- Predecir demanda o solar aporta como máximo: conocer la demanda real de la hora cambia el score en +0.0072.
