# Qué decir en la presentación (5 minutos)

Equipo: **hackers la l** — Alexander Hall Parrilla y Oscar Senesi Aladjem.
Presentación: `slides/presentacion_final.pptx` (10 diapositivas, sin puntuaciones ni rankings). Se regenera con
`./.venv/Scripts/python.exe slides/build_deck5.py presentacion_final.pptx`. Demo: `ui/bot_local.html`.

## Reparto y ritmo

- **Alexander**: diapositivas 1–5 (el problema, la idea, la solución, la prueba). **Oscar**: 6–10 (modo difícil, Volta, cierre).
- Unas 620 palabras: 30 segundos por diapositiva. No leáis la pantalla; cada diapositiva tiene una sola idea.
- El mensaje que nos diferencia: **entendimos el problema antes de modelarlo, y explicamos por qué funciona.**

## Diapositiva a diapositiva

### 1. Portada (0:00 – 0:20) · Alexander
«Somos hackers la l. Hemos diseñado cómo operar la batería del campus para contaminar menos y pagar menos: unas 42
toneladas de CO₂ y 91.000 euros al año con la batería actual, sin una sola infracción. Os contamos cómo pensamos el
problema.»

### 2. Los datos (0:20 – 0:55)
«Antes de entrenar nada, miramos los datos. La solar es solo el 2,4 % de la demanda, y la demanda neta supera los
500 kW de la batería el 99,5 % de las horas. Eso significa que todo lo que la batería descarga se consume en el
campus. Predecir la demanda o la solar no aporta nada. El problema es arbitraje: comprar energía cuando es barata y
limpia, y usarla cuando es cara y sucia.»

### 3. La idea (0:55 – 1:30)
«Y la fórmula del reto esconde una propiedad clave: es lineal. Como el caso base es fijo, mejorarla equivale a
minimizar lo que importamos de la red, ponderado cada hora por una única señal: el CO₂ más lambda por el precio.
Lambda sale de la propia fórmula: equivale a valorar la tonelada de CO₂ en unos 3.900 euros. Y hacen falta las dos
cosas: precio y CO₂ no ordenan las horas igual. Mirando solo el precio te quedas en el 75 % del beneficio posible;
solo el CO₂, en el 91 %. Con los dos, en su peso justo, el 99,9 %.»

### 4. La solución (1:30 – 2:00)
«Con una sola señal, el problema es un programa lineal. Cada hora leemos lo que sabemos, resolvemos el plan exacto de
carga y descarga, aplicamos solo la primera hora y repetimos. Un recorte de seguridad garantiza cero infracciones. Tarda
segundos y no depende de ningún modelo entrenado que se pueda romper.»

### 5. La prueba (2:00 – 2:30)
«No nos conformamos con que funcione: lo comprobamos. Lo comparamos con un plan que conoce el futuro: todos los
precios, el CO₂ y la demanda. En diez semanas de validación, nuestro agente evita 8,51 toneladas de CO₂; ese plan
perfecto, 8,55. Mirar solo el precio evita la mitad. No queda margen.»

*(Cambio de persona.)*

### 6. Modo difícil (2:30 – 3:05) · Oscar
«El modo difícil cambia el problema: batería tres veces mayor, solar doce veces mayor, y solo tres horas de precio y CO₂.
Ahora sí hay que prever. Mantenemos el mismo optimizador y le damos tres previsiones: precio y CO₂ con una regresión por
cada hora de adelanto; la demanda con su perfil semanal y el calendario de festivos de la UPC; y la solar de la hora con
árboles que usan la meteo de la última hora. Y descargamos con prudencia, porque lo que el campus no consume se pierde.
A la derecha, nuestro despacho por hora: casi idéntico al de quien conoce el futuro.»

### 7. Lo que aprendimos (3:05 – 3:40)
«Y medimos qué aporta cada pieza frente a un plan perfecto: con perfiles medios, 88 %; con la regresión, 91; con la
descarga prudente y la solar, 93. Después dimos al agente información perfecta por partes: saber la solar de esta hora,
o el precio de mañana, lo llevaría al 96 %. Esas son las dos piezas que más valen. Usamos el calendario de festivos,
que se conoce de antemano, pero no el tiempo real del test: eso sería conocer la respuesta.»

### 8. Volta (3:40 – 4:15)
«Y para que esto sirva a quien usa el campus, hicimos Volta. Hora a hora explica qué hace la batería y por qué, y qué
conviene hacer: consumir cuando sobra sol, aplazar cuando la red es cara y sucia. Se pone gafas de sol cuando carga con
sol, manda energía al campus en las horas de más CO₂, y duerme cuando no compensa.»
*(Si os sobran 15 segundos: abrid `ui/bot_local.html` y pulsad Reproducir.)*

### 9. Para UPC Sostenible (4:15 – 4:40)
«El mismo optimizador sirve para decidir inversiones. Energía y potencia se necesitan: duplicar las dos casi duplica el
ahorro. Cada punto de rendimiento de la batería vale unos 1.900 euros al año. Y sin optimizador, un horario fijo ya logra
el 79 %.»

### 10. Cierre (4:40 – 5:00)
«En resumen: entendimos el problema antes de modelarlo. Los datos, una señal, el óptimo comprobado, previsiones medidas
y Volta. Con la batería actual, unas 42 toneladas de CO₂ y 91.000 euros al año. Gracias.»

## Números que hay que saber

| Qué | Número |
|---|---|
| Impacto anual (batería actual) | 42 t CO₂ · 91.000 € · 0 infracciones |
| Solar frente a demanda · horas con demanda > 500 kW | 2,4 % · 99,5 % |
| λ · precio implícito del CO₂ | 0,26 kg/€ · ≈ 3.900 €/t |
| Beneficio: solo precio · solo CO₂ · los dos | 75 % · 91 % · 99,9 % |
| CO₂ evitado en 10 semanas: nuestro agente · plan perfecto | 8,51 t · 8,55 t |
| Modo difícil: con previsiones · con la solar de la hora o el precio de mañana | 93 % · 96 % |

## Si preguntan por el ranking

«En el modo estándar el plan está en el óptimo y lo comprobamos contra un plan que conoce el futuro. En el difícil,
otros equipos consiguieron más. Nuestras semanas de validación eran semanas normales y las del test incluían muchos
festivos y menos demanda; ahí la previsión de demanda y de solar pesa más, y lo corregimos tarde, con el calendario.
Lo que sí sabemos con precisión es qué información vale más y por qué.»

## Lo que no hay que decir

- Puntuaciones o posiciones en el ranking.
- Que usamos el tiempo real o los precios reales del test: no lo hicimos.
- Nada sobre otros equipos.
