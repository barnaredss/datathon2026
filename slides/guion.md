# Qué decir en la presentación

Equipo: **hackers la l** — Alexander Hall Parrilla y Oscar Senesi Aladjem.
Presentación: `slides/presentacion.pptx` (15 diapositivas principales + 6 de apoyo).
Respuestas a preguntas: `slides/qa.md`.

## Antes de empezar

1. Si habéis subido un agente mejor al modo difícil, cambiad `"hard": "23,29"` al principio de
   `slides/build_deck.py` por vuestro mejor score público y regenerad:
   `./.venv/Scripts/python.exe slides/build_deck.py`
2. Reparto sugerido: **Alexander** diapositivas 1–9 (problema, datos, idea, modo estándar);
   **Oscar** 10–15 (modo difícil, descartes, recomendaciones, cierre).
3. Duración: versión completa ≈ 6 min 30 s (unas 890 palabras). **Versión corta, ≈ 5 min 30 s: saltad
   las diapositivas 4, 8 y 13** (marcadas abajo con ⏭). Si necesitáis bajar a 5 min justos, acortad
   también la 14 a su primera frase.
4. No leáis las viñetas. Cada diapositiva tiene una sola idea: decidla y pasad.

## Los números que hay que saber de memoria

| Qué | Número |
|---|---|
| Modo estándar, score público | 6,43, 0 infracciones |
| Modo estándar, distancia al óptimo | 99,85 % (5,6667 de 5,6753) y 99,99 % en semanas tipo test |
| Solar frente a demanda | 2,4 % |
| Horas con demanda neta > 500 kW | 99,5 % |
| Correlación precio–CO2 | 0,58 |
| Peso del precio (λ) | 0,2593 kg por euro ≈ 3.900 € por tonelada de CO2 |
| Modo difícil, score público | 23,29 (o el que hayáis subido) |
| Modo difícil, distancia al óptimo | 93,3 % (20,80 de 22,28) |
| Modo difícil con precio y CO2 perfectos | 21,44 (96 %) |
| Impacto anual (batería actual) | 42 t CO2 y 91.000 € |

## Diapositiva a diapositiva

### 1. Portada (0:00 – 0:20) · Alexander
**Idea: tres números y una promesa.**
«Buenos días, somos hackers la l, Alexander y Oscar. Hemos operado la batería del campus en los dos
modos del reto. En el estándar estamos en el 99,9 % del óptimo teórico. En el difícil, en el 93 %,
usando solo previsiones. Y cero infracciones en los dos. En unos minutos os contamos cómo lo sabemos.»

### 2. El reto (0:20 – 0:50)
**Idea: decidir cada hora sin conocer el futuro; dos modos.**
«Cada hora hay que decidir si cargar o descargar, durante 2.016 horas. El Score mezcla CO2, con un
70 %, y coste, con un 30 %. En el modo estándar conocemos el precio y el CO2 de las próximas 24 horas.
En el difícil la batería es tres veces mayor, la solar doce veces mayor, y solo vemos 3 horas. Y un
detalle que lo condiciona todo: lo que se vierte a la red no puntúa.»

### 3. Los datos: escala (0:50 – 1:20)
**Idea: en el modo estándar no hay nada que predecir.**
«Lo primero fue mirar los datos. La solar es el 2,4 % de la demanda, y la demanda neta supera los
500 kW de la batería el 99,5 % de las horas. Es decir: todo lo que la batería descarga se consume en
el campus, siempre. En el modo estándar, predecir la demanda o la solar no aporta nada. Es arbitraje
puro: comprar energía cuando es barata y limpia, y usarla cuando es cara y sucia.»

### 4. Auditoría de datos (1:20 – 1:45) ⏭
**Idea: auditamos antes de modelar.**
«Antes de modelar auditamos los datos. El contador se queda congelado cada noche, de diez a seis:
un tercio de las filas repite un valor. Noviembre no tiene datos de sensores. Y hay quince horas con
demanda cero por averías. Por eso no apoyamos la estrategia en un modelo de demanda.»

### 5. Precio y CO2 (1:45 – 2:10)
**Idea: hacen falta las dos señales, combinadas.**
«El precio y el CO2 se parecen, correlación 0,58, pero no ordenan las horas igual: de madrugada el
precio es bajo y el CO2 alto. Si optimizas solo el precio te quedas en el 75 % del óptimo; solo el
CO2, en el 91 %. Hay que combinarlos, y con el peso correcto.»

### 6. La idea clave (2:10 – 2:40)
**Idea: el Score es lineal, así que basta una señal.**
«Y el peso correcto sale de la propia fórmula. Como el caso base es constante, maximizar el Score
equivale a minimizar lo que importamos de la red, ponderado cada hora por una única señal: el CO2 más
0,26 por el precio. Dicho de otra forma: la fórmula oficial valora la tonelada de CO2 en unos
3.900 euros.»

### 7. La solución (2:40 – 3:05)
**Idea: un programa lineal exacto, resuelto cada hora.**
«Con una sola señal, el problema es un programa lineal. Cada hora leemos las horas conocidas,
resolvemos el plan exacto y aplicamos solo la primera hora. Un recorte de seguridad garantiza cero
infracciones. No hay modelo entrenado que se pueda romper, y tarda unos segundos.»

### 8. Una semana de operación (3:05 – 3:20) ⏭
**Idea: hace lo que haría una persona con buen criterio.**
«Así se ve una semana: carga al mediodía, cuando la red es barata y limpia, y descarga en la punta
de la tarde.»

### 9. ¿Es óptimo? (3:20 – 3:50)
**Idea: lo demostramos comparando con quien conoce el futuro.**
«¿Cómo sabemos que es óptimo? Lo comparamos con un programa lineal que conoce el año entero por
adelantado. Nos quedamos al 99,85 %: 5,6667 frente a 5,6753. En semanas con la forma del test, al
99,99 %. En el modo estándar no queda margen: por eso tantos equipos empatamos en 6,43.»

*(Cambio de persona.)*

### 10. Modo difícil: qué cambia (3:50 – 4:20) · Oscar
**Idea: ahora sí hay que prever, y aparece un riesgo nuevo.**
«El modo difícil cambia el problema. La batería es tres veces mayor. La solar, doce veces mayor: ahora
sobra energía al mediodía una de cada diez horas, y es gratis si cabe en la batería. Y solo vemos tres
horas de precio y CO2. Además aparece un riesgo que antes no existía: la batería puede descargar más
de lo que el campus consume, y lo que sobra se pierde.»

### 11. Modo difícil: la solución (4:20 – 4:55)
**Idea: mismo optimizador, tres previsiones, y prudencia.**
«Mantenemos el mismo programa lineal y le damos tres previsiones. El precio y el CO2, con una regresión
por cada hora de adelanto. La demanda, con la última medida y el perfil semanal. Y la solar de la hora
en curso, con un modelo de árboles. Como la consigna es fija durante la hora y la demanda real no se
conoce, descargamos con prudencia: más cuando la hora vale mucho, menos cuando es dudosa. En la figura,
el verde es nuestro agente y el azul el plan que conoce el futuro: operan casi igual.»

### 12. Modo difícil: cuánto queda (4:55 – 5:30)
**Idea: medimos dónde se pierde cada punto.**
«Aquí está cada mejora. Con perfiles medios, 88 % de la cota. Con la regresión, 91. Con la prudencia al
descargar, 93. Y para saber qué falta, dimos al agente información perfecta por partes: con el precio
y el CO2 reales llegaría al 96 %; con la demanda de la hora en curso, también al 96. Esas son las dos
cosas que no se pueden saber, y valen lo mismo. En el leaderboard público, 23,29.»
*(Si habéis subido hard_v4, decid vuestro número.)*

### 13. Lo que probamos y descartamos (5:30 – 5:50) ⏭
**Idea: decidimos con números, y lo que no funcionó lo decimos.**
«También descartamos cosas con números. En el estándar, predecir demanda suma siete milésimas. En el
difícil, modelos más complejos para el precio no mejoran a la regresión. Y una hipótesis que falló:
pensamos que la semana de noviembre vendría sin demanda, protegimos el agente, y el resultado fue
idéntico. Se queda como robustez, no como puntos.»

### 14. Recomendaciones para UPC Sostenible (5:50 – 6:15)
**Idea: el optimizador también sirve para planificar.**
«El mismo optimizador responde preguntas de inversión. Energía y potencia se necesitan mutuamente:
duplicar una da un 22 % más; duplicar las dos, casi el doble. Cada punto de rendimiento vale unos
1.900 euros al año. Y si no hubiera optimizador, un horario fijo —cargar de doce a cuatro, descargar
por la tarde— logra el 79 % del óptimo.»

### 15. Conclusiones (6:15 – 6:35)
**Idea: óptimo donde se puede demostrar, medido donde no.**
«Resumiendo. En el modo estándar el problema se reduce a una señal y un programa lineal, y estamos en
el óptimo. En el difícil, al 93 % solo con previsiones, y sabemos exactamente qué falta. Con la batería
actual, unas 42 toneladas de CO2 y 91.000 euros al año. Gracias.»

## Lo que NO hay que decir

- No digáis que somos primeros ni deis una posición: el ranking final es el privado y no lo vemos.
- No presentéis la protección ante averías como una ganancia: en este test no dio puntos.
- No digáis «predecimos la demanda» en el modo estándar: ahí justamente demostramos que no hace falta.
- No citéis precios de baterías ni del carbono en el mercado como datos: no están en los datos oficiales.
- No habléis de otros equipos. Si preguntan por puntuaciones más altas en el modo difícil, usad la
  pregunta 19 de `qa.md`.

## Si solo recuerdan una cosa

«Mirad los datos antes de modelar: en el modo estándar nos dijeron que no había nada que predecir, y
en el difícil, exactamente qué había que predecir y cuánto valía cada cosa.»

## Diapositivas de apoyo (para preguntas)

- B1 Formulación del programa lineal.
- B2 Frontera CO2–coste: nuestro peso está en el máximo de la fórmula 70/30.
- B3 Rendimiento y solar: qué compensa mejorar.
- B4 Robustez ante averías del contador (tabla v1 frente a v2).
- B5 Regla del operador: 79 % del óptimo.
- B6 Ruido del reparto público/privado: media semana se mueve 0,14; el test completo, 0,01.
