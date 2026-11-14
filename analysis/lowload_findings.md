# Semanas de baja demanda (v2 → v3)

Fuente: `analysis/lowload_study.py`. Pseudo-test (10 semanas, 1.680 h) con la demanda escalada.

## Por qué lo miramos
1. La organización avisó (sábado 14-nov) de que en el ranking privado ningún equipo alcanza la
   puntuación máxima, aunque varios empatan en el máximo del público.
2. Para un agente que ya está en el óptimo con demanda normal, el único mecanismo que deja margen es
   que el campus no pueda absorber la descarga: si la demanda neta baja de 500 kW, lo que sobra se
   vierte a red sin ningún crédito. Las semanas del test son la última de cada mes e incluyen festivos
   (25–31 dic, 25–31 ago), que no aparecen en el entrenamiento.
3. No vemos el ranking privado: es una hipótesis razonada, no un hecho comprobado.

## Diagnóstico (todas las semanas con la demanda a la mitad)
- v2 pierde 0,2061 puntos frente a un MPC que conociera la demanda real de las 24 h siguientes.
- El 77 % de esa pérdida (0,1584) es energía vertida: 1.026 kWh descargados en horas en que el campus
  no podía absorberlos, sobre todo a las 6–9 h y a las 20–23 h, cuando la demanda cambia de nivel.
- Con la demanda real de las 24 h siguientes, el MPC vuelve a quedar a 0,001 de la cota: en semanas de
  baja demanda, prever la demanda sí importa.

## Qué hace v3
Estima la demanda neta de cada hora del horizonte escalando la última medida con el perfil semanal
medio del año de entrenamiento (día de la semana × hora, 168 valores). Para la hora actual toma el
mínimo entre esa estimación y la última medida. Con demanda normal ningún tope actúa y el resultado
es idéntico al de v2.

## Resultados (distancia a la cota de información perfecta; menos es mejor)

| Escenario | Cota | v2 | v3 |
|---|---|---|---|
| Normal | 6,1250 | 0,0009 | 0,0009 |
| Todas las semanas ×0,80 | 7,6881 | 0,0013 | 0,0013 |
| Todas las semanas ×0,65 | 9,5046 | 0,0291 | 0,0138 |
| Todas las semanas ×0,50 | 12,3443 | 0,2078 | 0,1314 |
| Semana 4 ×0,45 | 6,4756 | 0,0190 | 0,0130 |
| Semana 4 ×0,35 | 6,5185 | 0,0670 | 0,0422 |
| Última semana ×0,40 | 6,4723 | 0,0455 | 0,0402 |
| Semana 3 sin datos | 6,5090 | 0,0012 | 0,0012 |
| Últimas 72 h sin datos | 5,9422 | 0,1521 | 0,1521 |

## Lectura
- v3 nunca es peor que v2 en estos escenarios y reduce la pérdida entre un 12 % y un 53 % cuando la
  demanda cae por debajo de ~65 % de lo normal. Por encima de ~80 % no cambia nada.
- Train completo y pseudo-test normal: mismos scores que v2 (5,6667 y 6,1241), 0 infracciones.
- Probamos también persistencia del mismo tramo horario del día anterior y márgenes de seguridad del
  3 % al 10 %: no mejoran de forma consistente; nos quedamos con la versión sin parámetros extra.
- Lo que queda frente a la cota es error de previsión de la demanda (el MPC con demanda real queda a
  0,001) y, en las averías al final del test, no saber de antemano que van a ocurrir.
