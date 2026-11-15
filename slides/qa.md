# Preguntas probables del jurado

**1. ¿Por qué no predecís la demanda o la solar?**
Porque no sirve de nada: la solar es el 2,4 % de la energía y la demanda neta supera 500 kW en el 99,5 % de las horas, así que la batería nunca vierte. Conocer la demanda real de la hora cambia el score en +0,0072 (train) y +0,0000 (pseudo-test). Fuente: eda_findings.md, puntos 10-11; strategy_findings.md, punto 6.

**2. ¿Por qué un LP y no aprendizaje por refuerzo o un modelo entrenado?**
El Score es lineal en las importaciones de red, así que el problema es un LP y su solución es exacta, sin entrenamiento ni riesgo de fallar con datos nuevos. Nuestro MPC llega al 99,85 % del óptimo con información perfecta; no hay hueco que justificar un modelo más complejo. Fuente: strategy_findings.md, punto 1.

**3. ¿Cómo sabéis que es óptimo?**
Lo comparamos con el LP de información perfecta de todo el año: 5,6667 frente a 5,6753 en train (99,85 %) y 6,1241 frente a 6,1250 en pseudo-test (99,99 %). Fuente: strategy_findings.md, punto 1.

**4. ¿De dónde sale el peso λ = 0,2593?**
De la fórmula oficial: λ = (0,3/0,7)·CO2_base/Coste_base, porque las bases son constantes. Con las bases del entrenamiento sale 0,2517; con las de la mitad pública del test, que se deducen de las cifras que publica el leaderboard (kg evitados y % de reducción), sale 0,2593, y ese usamos. La diferencia no cambia el resultado: el barrido es plano en esa zona (λ = 0,20 da 6,1205; 0,2593 da 6,1241; 0,35 da 6,1054). Fuente: strategy_findings.md, punto 3; whatif_findings.md, punto 4.

**5. ¿Cuánto cuesta una tonelada de CO2 según la fórmula?**
Unos 3.900 EUR: 3.973 con las bases de train y 3.857 con el 0,2593 calibrado en el leaderboard. Es una lectura de la fórmula, no un precio de mercado. Fuente: whatif_findings.md, punto 4.

**6. ¿Qué pasa si el contador falla en el test?**
Una protección (v2) supone que una demanda neta baja medida persiste hasta fin de semana. Recupera el 98 % de la pérdida simulada si falla la 3.ª semana y es idéntica a v1 con datos normales. Fuente: outage_findings.md, resultados y lectura.

**7. ¿Qué aportó la protección en el leaderboard?**
Nada: v2 dio el mismo resultado que v1 (6,43; 5,96 %; 7,52 %). La hipótesis de una semana de noviembre sin demanda era falsa para este test; queda solo como robustez. Fuente: outage_findings.md, resultado en el leaderboard.

**8. ¿Fiabilidad y tiempo de ejecución?**
0 infracciones en train y pseudo-test, 0 respaldos usados y unos 7,6 s por 2.016 h (límite 60 s). Solo numpy y scipy, sin ficheros de modelo. Fuente: strategy_findings.md, punto 6.

**9. ¿Hay riesgo de sobreajuste al leaderboard público?**
Es bajo: el controlador no se entrena. Lo único que tomamos del leaderboard es la relación entre las bases de CO2 y de coste para fijar λ, y con las bases de entrenamiento (0,2517) el resultado es prácticamente el mismo. Hicimos dos envíos y los dos dieron exactamente el mismo resultado. Fuente: strategy_findings.md, puntos 3 y 6; submissions/LOG.md.

**10. ¿Qué pasa con los datos nocturnos congelados?**
El contador repite un valor de 22:05 a 06:00 (33,5 % de las filas), así que la demanda nocturna real es desconocida. Por eso no construimos un modelo de demanda; la carga neta nocturna (unos 975 kW) igualmente supera 500 kW. Fuente: eda_findings.md, puntos 6-9.

**11. ¿Qué ocurre en noviembre, que no tiene datos?**
Precio y CO2 sí cubren noviembre (552 h); solo faltan los sensores. El agente solo necesita precio y CO2 futuros, y la protección contempla una demanda baja. Fuente: eda_findings.md, punto 2.

**12. ¿Ampliar la batería compensa?**
Duplicar solo energía o solo potencia da cerca de +22 % de ahorro; duplicar ambas, +98 % (180,5 mil EUR/año frente a 91). Para CO2 pesa más la energía (+28,8 t frente a +4,4 t). Fuente: whatif_findings.md, punto 1.

**13. ¿Cuál sería el periodo de amortización?** (supuesto ilustrativo, no es dato oficial)
A 300-500 EUR/kWh instalado, 2.000 kWh costarían 0,6-1,0 M EUR y se amortizarían en 6,6-11 años solo con este ahorro. Es un supuesto nuestro de coste, no un dato oficial. Fuente: whatif_findings.md, punto 1.

**14. ¿Un operador sin optimizador qué puede hacer?**
Una regla fija (cargar 12-16 h; descargar 18-21 h en invierno y 20-23 h en verano) logra el 79,2 % del óptimo, aunque medida sobre los datos en los que se ajustó. El 21 % restante exige mirar los precios y el CO2 del día. Fuente: whatif_findings.md, punto 5.

**15. ¿Cuál es el impacto anual y es fiable?**
Unas 42,3 t de CO2 y 91.380 EUR al año, anualizando el año de entrenamiento (5.993 h) con el factor 8760/5993. Es una extrapolación, no una garantía para otro año. Fuente: strategy_findings.md, punto 6.

**16. ¿Por qué hay tantos equipos empatados, y qué significan las diferencias pequeñas?**
Porque el óptimo es el mismo para todos. Y las diferencias pequeñas no son fiables: en semanas tipo test, mover λ de 0,18 a 0,32 cambia el score del test completo en 0,01, pero el de media semana hasta en 0,14, porque desplaza cargas y descargas entre la mitad pública y la privada. Lo que gana una mitad lo pierde la otra. Fuente: split_noise_findings.md, puntos 1 a 3.

## Modo difícil

**17. ¿Por qué en el modo difícil os quedáis en el 93 % y no en el 99 %?**
Porque ahí hay que prever. Lo medimos dando al agente información perfecta por partes: con precio y CO2 reales a 24 h llegaría a 21,44 (96 %); con la demanda neta real de la hora en curso, a 21,33 (96 %); con ambas, a 21,97 (98,6 %). Son dos pérdidas de tamaño parecido y ninguna se puede eliminar del todo. Fuente: hard_findings.md, punto 3.

**18. ¿Usáis datos externos o del periodo de test?**
No. Solo `data/train`. Las 48 h con las que arranca cada semana son del entrenamiento: el entrenamiento llega hasta la víspera de cada semana de test. Los perfiles, la regresión y los árboles se ajustan con ese mismo año. Fuente: hard_findings.md, puntos 4 y 5; `tools/hard.py`.

**19. Hay equipos con más puntuación en el modo difícil. ¿Por qué?**
No lo sabemos. Lo que hemos medido es que nuestro agente, con precio y CO2 perfectos a 24 h, obtendría 21,44 en nuestras semanas de validación, que en la escala del leaderboard público son unos 24,1 (estimación con un único punto de calibración). También medimos que la puntuación de media semana se mueve décimas con cambios mínimos. El ranking que decide es el privado. Fuente: hard_findings.md, punto 6; split_noise_findings.md.

**20. ¿Qué es la regla del cuantil?**
La consigna es fija durante la hora, pero la demanda neta real no se conoce. Descargar de más se vierte a red y se pierde; descargar de menos deja energía sin usar. Lo óptimo es descargar hasta un cuantil de la demanda estimada que depende de cuánto vale la energía guardada frente a la señal de esa hora: más alto en las horas caras, más bajo en las dudosas. Aportó +0,05; la misma regla al cargar empeoraba (−0,3) y no se usa. Fuente: hard_findings.md, punto 5.

**21. ¿Por qué árboles para la solar y regresión para el precio?**
Porque lo comprobamos. Para precio y CO2 los árboles no mejoran a la regresión (mismo error a 12 h y peor a 3 h). Para la solar de la hora en curso sí: error medio de 91 kW frente a 111 kW de la persistencia. Los árboles se evalúan dentro de `agent.py`, sin librerías de modelos. Fuente: hard_findings.md, puntos 4 y 7.

**22. ¿Cuánto tarda y qué pasa si algo falla en el modo difícil?**
Entre 6 y 11 s para las 2.016 h (límite 60 s) y 0 infracciones. Si el solver fallara hay una política de respaldo por horas, y todas las consignas pasan por el recorte de seguridad con la capacidad y la potencia que da el propio simulador. Fuente: hard_findings.md, punto 2.
