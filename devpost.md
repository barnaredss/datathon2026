# Texto para Devpost

Copiad cada bloque en el campo de Devpost con el mismo nombre.

## Project name
Volta: la batería del Campus Nord, operada en el óptimo

## Elevator pitch (máx. 200 caracteres)
Un agente que opera la batería de la UPC al 99,9 % del óptimo teórico, y Volta, un bot que explica cada decisión y dice al campus cuándo consumir.

## Inspiration
El campus tiene una batería de 2.000 kWh y una pregunta sencilla: cuándo cargarla y cuándo usarla para contaminar menos y pagar menos. Antes de entrenar ningún modelo quisimos entender qué decían los datos, y sobre todo, demostrar cuánto se puede ganar de verdad.

## What it does
- Decide cada hora la potencia de la batería para minimizar el CO₂ (70 %) y el coste (30 %) del campus.
- Modo estándar: 6,43 en el leaderboard público, 0 infracciones, al 99,9 % de lo que lograría alguien que conociera el futuro.
- Modo difícil (batería ×3, solar ×12, solo 3 h de mercado conocidas): 23,44 en el leaderboard público, al 93 % de esa cota en nuestra validación, solo con previsiones y el calendario del campus.
- Volta, una página interactiva, explica hora a hora qué hace la batería y por qué, y qué conviene hacer en el campus: consumir cuando sobra sol, aplazar cuando la red es cara y sucia.
- Recomendaciones para UPC Sostenible: dimensionado (energía y potencia se complementan: duplicar las dos casi duplica el ahorro), valor del rendimiento (≈ 1.900 €/año por punto) y una regla fija para el operador que logra el 79 % del óptimo.

## How we built it
1. Auditoría de datos: la solar es el 2,4 % de la demanda y la demanda neta supera los 500 kW de la batería el 99,5 % de las horas, así que en el modo estándar no hay nada que predecir: es arbitraje puro. También encontramos el contador congelado cada noche y noviembre sin datos.
2. El Score es lineal en la energía importada: se reduce a una única señal por hora, CO₂ + λ·precio, con λ sacado de la propia fórmula (equivale a valorar la tonelada de CO₂ en unos 3.900 €).
3. Un programa lineal exacto (SciPy/HiGHS) sobre las horas conocidas, resuelto cada hora, con un recorte de seguridad que garantiza 0 infracciones. Lo comparamos con un programa lineal que conoce el año entero.
4. Modo difícil: el mismo optimizador con tres previsiones (regresión por hora de adelanto para precio y CO₂; demanda con perfil semanal y el calendario público de festivos y periodos no lectivos de la UPC; solar de la hora con árboles de LightGBM evaluados en Python puro) y una regla de cuantil para descargar con prudencia cuando la demanda real no se conoce.
5. Medimos dónde se pierde cada punto dando al agente información perfecta por partes.
6. Volta: HTML, CSS y SVG animado, sin dependencias, con semanas simuladas por el propio agente.

## Challenges we ran into
- En el modo estándar muchos equipos empatamos en el máximo público: demostramos que es la cota teórica y que las diferencias pequeñas entre mitades del test son ruido del reparto.
- En el modo difícil la descarga máxima supera a la demanda del campus: lo que sobra se vierte a red y no cuenta. Hubo que decidir con prudencia sin conocer la demanda de la hora.
- Una hipótesis que falló: pensamos que la semana de noviembre vendría sin demanda y protegimos el agente; el resultado fue idéntico. Lo contamos tal cual.
- Datos externos: usamos solo lo que un operador real sabría de antemano (el calendario). No el tiempo ni los precios reales del test.

## Accomplishments that we're proud of
- Demostrar con números que el agente estándar está en el óptimo (5,6667 frente a 5,6753 en todo el año).
- Explicar el modo difícil punto por punto: qué aporta cada previsión y qué falta.
- 0 infracciones en todas las entregas y un agente que tarda segundos, sin ficheros de modelo que puedan romperse.
- Volta: la optimización explicada a quien usa el campus.

## What we learned
Mirar los datos antes de modelar. En el modo estándar nos dijeron que no había nada que predecir; en el difícil, exactamente qué había que predecir y cuánto valía cada cosa.

## What's next for Volta
- Conectar Volta a los datos en tiempo real del campus y avisar a los edificios de las horas buenas y malas.
- Usar previsiones meteorológicas reales del día siguiente para la solar, que en nuestro análisis valen hasta un punto de Score.
- Dimensionar una ampliación de batería con el mismo optimizador.

## Built with
python, numpy, pandas, scipy (HiGHS), scikit-learn, lightgbm, matplotlib, python-pptx, html, css, javascript, svg

## Links
- Código: https://github.com/barnaredss/datathon2026
- Presentación: `slides/presentacion.pptx` (subidla como archivo o enlazadla desde el repositorio)
- Volta: `ui/bot_local.html` en el repositorio. El enlace del artifact solo funciona si lo compartís desde su menú Share.

## Imágenes sugeridas (carpeta figures/)
1. `ui_bot_crop.png` (Volta)
2. `est_escalera.png` (estándar: 99,9 % del óptimo)
3. `hard_escalera.png` (difícil: escalera de mejoras y oráculos)
4. `hard_horas.png` (despacho por hora frente al plan perfecto)
5. `whatif_dimensionado.png` (recomendación de dimensionado)
