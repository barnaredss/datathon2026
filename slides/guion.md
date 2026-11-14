# Guion de la presentación (aprox. 5 minutos)

Las marcas de tiempo son acumuladas. Dilo con tus palabras; las frases son una guía.

## 1. Portada (0:00)
Buenos días. Somos hackers la l, Alexander y Oscar. Hemos operado la batería del campus con un resultado que creemos que está en el techo de lo posible: 6,43 en el leaderboard público, cero infracciones, y el 99,9 % del óptimo teórico. En cinco minutos os explicamos por qué.

## 2. El reto (0:20)
El reto es decidir, cada hora, si cargar o descargar una batería de 2.000 kWh durante 2.016 horas. El Score mezcla CO2 y coste. Solo vemos 24 horas de precio y CO2 hacia delante; la demanda y la solar futuras no las conocemos. Parece un problema de predicción.

## 3. Escala (0:50)
Pero los datos dicen otra cosa. La solar es solo el 2,4 % de la energía consumida, y la demanda neta supera los 500 kW de la batería en el 99,5 % de las horas. Nunca es negativa. Así que la batería jamás vierte a la red: todo lo que descarga se consume en el campus. Predecir demanda o solar no aporta nada. Es arbitraje puro: comprar energía cuando es barata y limpia, y usarla cuando es cara y sucia.

## 4. Auditoría (1:25)
Antes de modelar, auditamos los datos. El contador se congela cada noche, de diez de la noche a seis de la mañana, y repite un valor: un tercio de las filas. Noviembre de 2025 no tiene datos de sensores. Y hay quince horas con demanda cero por averías. Por eso no construimos la estrategia sobre un modelo de demanda, y protegimos el controlador frente a esas averías.

## 5. Precio y CO2 (2:00)
El precio y el CO2 se parecen, con una correlación de 0,58, pero no ordenan las horas igual. De noche el CO2 es alto aunque el precio sea bajo. Usar solo uno nos deja lejos del óptimo. Necesitamos una señal combinada.

## 6. La idea clave (2:30)
Y aquí está la idea clave: el Score es lineal. Con las bases constantes, maximizarlo equivale a minimizar lo que importamos de la red, ponderado hora a hora por el CO2 más un peso por el precio. Ese peso sale directamente de la fórmula oficial, 0,2593. Dicho de otra forma, la fórmula oficial valora una tonelada de CO2 en unos 3.900 euros.

## 7. La solución (3:05)
Con una única señal, el problema es un programa lineal. Cada hora lo resolvemos de forma exacta sobre las 24 horas conocidas, aplicamos solo la primera acción y repetimos. Un recorte de seguridad garantiza cero infracciones, y hay un respaldo por reglas si el solver fallara. Tarda unos siete segundos en las 2.016 horas, y usa solo numpy y scipy. No hay modelo entrenado que pueda romperse.

## 8. Una semana (3:35)
Así se ve una semana de diciembre. La batería carga en el valle barato y limpio del mediodía, y algunas noches, y descarga en la punta de la tarde. Hace unos 1,4 ciclos al día.

## 9. ¿Es óptimo? (3:55)
¿Es óptimo? Sí. Lo comparamos con un programa lineal que conoce todo el año por adelantado. En entrenamiento llegamos al 99,85 %, 5,6667 frente a 5,6753. Con la forma del test, 6,1241 frente a 6,1250. Usar solo precio llega al 73-76 %, y solo CO2, al 91-92 %. No queda margen real: en semanas con la forma del test solo faltan 0,0009 puntos para la cota.

## 10. Lo descartado (4:15)
Probamos y descartamos cosas, con números. Predecir demanda o solar suma como máximo siete milésimas. Con doce horas de horizonte ya hay 6,1235 de 6,1241. Nuestro peso está en el máximo del barrido. Y una honestidad: supusimos que la semana de noviembre no tenía demanda y creamos una protección. El resultado fue idéntico, así que la hipótesis era falsa para este test. La protección queda solo como robustez.

## 11. Recomendaciones (4:40)
Para UPC Sostenible, el mismo optimizador responde a preguntas de planificación. Energía y potencia se complementan: duplicar una da un 22 % más, duplicar ambas casi el doble. Cada punto de rendimiento vale unos 1.900 euros al año. Y un horario fijo de operador logra el 79 % del óptimo.

## 12. Conclusiones (5:05)
En resumen: estamos en el techo teórico y sabemos por qué. Los datos dicen que esto es arbitraje, no predicción; el Score es lineal, así que una señal y un programa lineal exacto bastan; y el mismo optimizador le sirve a UPC para planificar. Unas 42 toneladas de CO2 y 91.000 euros al año. Gracias.
