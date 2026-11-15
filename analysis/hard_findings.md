# Modo difícil: hallazgos

Fuente: `analysis/hard_study.py` (números en `analysis/cache/hard_results.json`), `tools/hard.py`,
`agent_hard/agent.py`. Scores sobre 10 semanas tipo test (1.680 h); los perfiles y modelos se ajustan
SIN esas semanas. Batería 6.000 kWh / ±1.500 kW, solar ×12, solo 3 h de precio y CO2 conocidas.

## 1. Qué cambia respecto al modo estándar
1. Con la solar ×12 hay excedente (demanda neta negativa) el 10,6 % de las horas: 60,1 MWh en 10 semanas.
   Es energía gratis si cabe en la batería; si no se carga, se vierte a red y no puntúa.
2. La descarga máxima (1.500 kW) supera a la demanda neta habitual (600–1.300 kW): descargar de más se
   vierte a red y se pierde entero. En el modo estándar esto no pasaba nunca.
3. Solo se conocen 3 horas de precio y CO2: el resto del día hay que preverlo.

## 2. Escalera de mejoras (score; entre paréntesis, % de la cota de información perfecta 22,28)
- Plantilla oficial: 2,19 (9,8 %).
- Perfiles medios, sin modelos: 19,58 (87,9 %).
- + regresión de precio y CO2 (una por hora de adelanto, 3–23 h): 20,36 (91,4 %).
- + prudencia al descargar e historia de las 48 h previas: 20,68 (92,8 %).
- + previsión de la solar de la hora actual con árboles (agente final, hard_v4): 20,80 (93,3 %).
- 0 infracciones; unos 6–11 s para las 2.016 h (límite 60 s).

## 3. Dónde está el límite (mismo agente con información perfecta por partes)
- Con precio y CO2 reales a 24 h: 21,44 (96,2 %).
- Con la demanda neta real de la hora actual: 21,33 (95,7 %).
- Con ambas: 21,97 (98,6 %). Conocer la demanda de las horas siguientes no añade casi nada.
- Lectura: quedan dos fuentes de pérdida de tamaño parecido (≈ 0,5–0,65 puntos cada una): no conocer la
  señal más allá de 3 h y no conocer la solar de la hora en curso.

## 4. Las tres previsiones
- Precio y CO2: regresión lineal por hora de adelanto sobre cocientes respecto a un perfil
  mes × tipo de día × hora (nivel de las 3 h conocidas, medias de 6 y 24 h, misma hora de ayer y anteayer,
  cambio hoy–ayer). Error medio 5 % a 3 h y 14 % a 12 h. Un modelo de árboles no la mejora.
- Demanda: última medida × perfil semanal. Error medio 24 kW sobre 1.110 kW (de noche es exacta: el
  contador repite el valor).
- Solar de la hora actual: 150 árboles sobre la producción de las dos últimas horas, la de ayer a la misma
  hora, irradiancia y temperaturas de la última hora y el CO2 de la red respecto a su perfil. Error medio
  91 kW frente a 111 kW de la persistencia de la nubosidad. Los árboles se evalúan dentro de `agent.py`.

## 5. Decisión con incertidumbre
- Cada semana de test arranca con las 48 h anteriores del entrenamiento (el entrenamiento llega hasta la
  víspera de cada semana de test): +0,05.
- Regla del cuantil al descargar: la consigna es fija durante la hora y la demanda neta no se conoce;
  se descarga hasta el cuantil 1 − μ/(η·w) de la demanda neta estimada, donde μ es el valor del kWh
  almacenado (dual del LP) y w la señal de la hora: +0,05. La misma regla al cargar empeora (−0,3).
- El despacho medio por hora del agente es casi igual al del plan con información perfecta
  (`figures/hard_horas.png`); lo que queda es ruido de sincronización por el error de previsión.

## 6. Leaderboard
- hard_v3 (20,68 local): 23,29 en el público (sábado 19:00, 5.º de 24). Público ≈ 1,126 × local.
- hard_v4 (20,80 local): pendiente de subir; proyección ≈ 23,4.
- Domingo 10:25: 52 equipos, récord 24,37. En nuestra escala, 24,37 equivale a ≈ 21,6 local, por encima
  de lo que obtiene este agente con precio y CO2 perfectos a 24 h (21,44 ≈ 24,1 en público). Es una
  estimación con un solo punto de calibración; la mitad pública además se mueve décimas con cambios
  mínimos (`split_noise_findings.md`). No usamos datos externos ni datos del periodo de test.

## 7. Probado sin mejora (modo difícil)
Horizonte más largo, valor terminal, planificar con menor rendimiento, colchones de carga con excedente,
árboles en vez de regresión para precio y CO2, una regresión por (adelanto, hora), comprimir o ampliar
la dispersión de la previsión, multiplicadores del peso del precio, regla del cuantil al cargar.
