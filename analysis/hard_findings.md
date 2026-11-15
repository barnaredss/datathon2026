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

## 8. Semanas de test con menos demanda (domingo)
- En la mitad pública del test, el caso base es de 59,8 kg CO2/h y 94,2 €/h, frente a 75,0 kg/h y 127,6 €/h
  en nuestras semanas de validación (−20 % y −26 %). Las semanas de test son la última de cada mes e
  incluyen periodos de vacaciones (25–31 dic, final de agosto, Semana Santa).
- Con menos demanda la cota sube mucho (el Score es relativo a un caso base más pequeño y hay más excedente
  solar): demanda ×0,8 → cota 29,01; ×0,85 con tres semanas de festivos → cota 29,46. El agente se queda
  en el 90–92 % de la cota en esos escenarios.
- En esos escenarios, conocer la demanda neta real de la hora en curso vale +1,2 puntos y la de las
  siguientes 8 h, +0,4 más. Por separado, conocer solo la demanda o solo la solar de la hora vale +0,3–0,4.
- hard_v5 detecta los laborables que se comportan como festivos (la demanda de 10–15 h apenas supera a
  la nocturna) y prevé los días siguientes con la forma de un domingo: +0,28 en semanas de festivos
  simuladas, sin cambio en semanas normales (20,80) y +0,01 en el año completo.
- Ajustar los márgenes de prudencia para escenarios de baja demanda no mejora nada (barrido plano).
- El mejor equipo (27,98 público) evita 16,2 kg/h, lo mismo que nuestra cota de información perfecta
  en las semanas de validación (16,0 kg/h). Nosotros, 13,1 kg/h con hard_v3. No conocemos la cota del
  test público; con un caso base un 20 % menor podría estar en torno a 28–29.

## 9. Datos externos: calendario sí, meteorología real no
- Fuentes públicas consultadas: calendario académico de la UPC 2025-26 (periodos no lectivos: Navidad
  29 dic – 5 ene, Semana Santa 30 mar – 6 abr, verano 3–31 ago), festivos de Catalunya y festivos locales
  de Barcelona (Mercè 24 sep 2025; Segona Pasqua 25 may 2026). Son información conocida de antemano: un
  operador real la tiene.
- Los datos de entrenamiento lo confirman. Cociente demanda 10–15 h / nocturna: laborable 1,43, domingo 0,86,
  festivos 0,73–0,84, no lectivo de Navidad 1,22, de Semana Santa 1,00, laborables de agosto 1,15.
- Las semanas de test contienen: Mercè (24 sep), Navidad y Sant Esteve (25–26 dic) más el no lectivo de
  Navidad, el no lectivo de Semana Santa (30–31 mar), Segona Pasqua (25 may), Sant Joan (24 jun) y el
  no lectivo de agosto (25–31 ago). Encaja con el caso base un 20 % menor del test público.
- hard_v6 usa ese calendario en la previsión de demanda (forma de domingo en festivos; mezcla con el peso
  medido en los no lectivos). Validación fuera de muestra en 6 semanas de entrenamiento con festivos:
  13,590 → 13,745 (+0,155; 85,5 % → 86,5 % de la cota). Semanas normales: 20,795 → 20,807.
  La detección automática de cierres se mantiene para días no previstos en el calendario.
- No usamos la meteorología ni los precios reales de las semanas de test: eso sería conocer las respuestas,
  no prever. Los archivos de "previsiones históricas" públicos son prácticamente la observación real.
