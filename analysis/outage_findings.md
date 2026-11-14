# Robustez ante averías del contador (v1 → v2)

Fuente: `analysis/outage_study.py`. Scores sobre el pseudo-test (10 semanas, 1.680 h) salvo la última fila.

## Por qué lo miramos
1. La auditoría de datos (`eda_findings.md`, puntos 2 y 5) muestra que el contador y los inversores no
   tienen datos en todo noviembre de 2025 y que hay 15 horas con demanda 0 por caída del medidor.
2. El test oculto incluye la última semana de cada mes, también la de noviembre (hay precio y CO2 de
   noviembre, y 12 semanas = 2.016 h). No sabemos qué demanda contiene esa semana.
3. Indicio: el caso base de la mitad pública del test es de 71,3 kg CO2/h y 117,8 €/h, frente a
   92,1 kg/h y 156,8 €/h en entrenamiento (−23 % y −25 %). Si las 12 semanas se parecieran a su mes
   esperaríamos 92,2 kg/h y 155,2 €/h; con la semana de noviembre a demanda 0, 83,9 y 142,7.
   La diferencia observada es compatible con al menos una semana sin demanda medida (más festivos:
   25–31 dic, 25–31 ago). No es una prueba: es un riesgo que merece protección.

## Qué hace mal un agente sin protección (v1)
Sin demanda, descargar es verter a red (sin crédito de coste ni de CO2) y la energía importada para
cargar no se puede devolver al campus hasta que vuelva la demanda. v1 solo limitaba la descarga de
la hora actual; el LP seguía planificando "cargo ahora, descargo dentro de unas horas" y llenaba la
batería en plena avería.

## Qué hace v2
Si la última demanda neta medida es inferior a 500 kW, el LP supone que esa situación persiste hasta
el final de la semana en curso (tope de descarga en todas las horas del horizonte dentro del bloque).
En la primera hora de una semana nueva se ignora la medida (es de hace un mes). Con demanda normal el
tope no actúa: v2 da exactamente el mismo resultado que v1.

## Resultados (score; entre paréntesis, distancia a la cota de información perfecta)

| Escenario | Cota | v1 | v2 |
|---|---|---|---|
| Pseudo-test normal | 6,1250 | 6,1241 (0,0009) | 6,1241 (0,0009) |
| 3.ª semana sin datos (posición de noviembre) | 6,5090 | 6,4591 (0,0499) | 6,5078 (0,0012) |
| 6.ª semana sin datos | 6,2209 | 6,2006 (0,0203) | 6,2135 (0,0074) |
| 1.ª semana sin datos | 6,3280 | 6,3099 (0,0181) | 6,3220 (0,0060) |
| Última semana sin datos | 5,6202 | 5,4469 (0,1733) | 5,4867 (0,1335) |
| 3.ª y última sin datos | 5,9830 | 5,7300 (0,2530) | 5,8308 (0,1523) |
| Avería de 70 h a mitad de semana | 6,2092 | 6,2044 (0,0048) | 6,2027 (0,0064) |
| Una semana con demanda de 200 kW | 6,4770 | 6,3725 (0,1045) | 6,4428 (0,0341) |
| Train completo (5.993 h) | 5,6753 | 5,6667 (0,0085) | 5,6667 (0,0085) |

## Resultado en el leaderboard
Subimos v2 el sábado 14-nov: resultado idéntico a v1 al céntimo (6,43; ΔCO2 5,96 %; ΔCoste 7,52 %;
4.282,5 kg; 8.934,63 €; 0 infracciones). Conclusión: en el test público la protección no llega a
actuar, es decir, no hay semanas ni horas con demanda neta inferior a 500 kW. La hipótesis de la
semana de noviembre sin demanda queda descartada. Mantenemos v2 porque no cuesta nada y protege la
operación real, pero no aporta puntos en este test.

## Lectura
- v2 no cuesta nada con datos normales. Cuando una semana entera se queda sin demanda recupera el
  98 % de la pérdida si es la 3.ª semana (posición de noviembre), en torno al 65 % si es la 1.ª o la
  6.ª, y el 23 % si es la última (ahí lo que se pierde es haber llegado con la batería cargada, y eso
  no se puede saber antes). El único caso en que pierde (−0,0017) es una avería que termina a mitad
  de semana, porque supone que dura hasta el final.
- Lo que queda por ganar frente a la cota exige saber de antemano que la avería va a ocurrir (vaciar
  la batería antes); eso no es información disponible en operación real.
- 0 infracciones en todos los escenarios.
