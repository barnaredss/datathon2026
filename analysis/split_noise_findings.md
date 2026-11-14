# Ruido del reparto público/privado

Fuente: `analysis/split_noise.py`, agente actual, pseudo-test (10 semanas, 1.680 h). No conocemos el
reparto real del test; probamos cinco repartos posibles del 50 % de las horas.

## Resultado (score según el peso λ)

| λ | Test completo | 1.ª mitad de cada semana | 2.ª mitad | Días pares | Días impares | Horas al azar |
|---|---|---|---|---|---|---|
| 0,18 | 6,1164 | 7,1099 | 4,9948 | 6,6385 | 5,4302 | 5,1489 |
| 0,21 | 6,1219 | 7,1218 | 4,9928 | 6,6419 | 5,4385 | 5,1368 |
| 0,23 | 6,1248 | 7,0279 | 5,1036 | 6,7665 | 5,2820 | 5,2652 |
| 0,2517 | 6,1249 | 7,0237 | 5,1086 | 6,6846 | 5,3895 | 5,3026 |
| 0,2593 (nuestro) | 6,1241 | 7,0237 | 5,1055 | 6,6510 | 5,4314 | 5,4035 |
| 0,27 | 6,1212 | 6,9784 | 5,1475 | 6,4520 | 5,6849 | 5,5266 |
| 0,29 | 6,1185 | 6,9919 | 5,1272 | 6,4012 | 5,7451 | 5,4304 |
| 0,32 | 6,1133 | 6,9905 | 5,1158 | 6,4182 | 5,7107 | 5,5229 |
| 0,36 | 6,1019 | 6,9850 | 5,0964 | 6,3494 | 5,7744 | 5,8317 |

## Lectura
1. El score del test completo es plano: entre λ = 0,18 y 0,32 cambia 0,0116 puntos (6,1133–6,1249).
2. El score de media semana no lo es: con el mismo barrido cambia 0,14 (1.ª mitad), 0,15 (2.ª mitad),
   0,37 (días pares), 0,46 (días impares) y 0,39 (horas al azar).
3. Es un juego de suma cero: lo que gana una mitad lo pierde la otra (1.ª mitad sube de 7,02 a 7,12 al
   bajar λ a 0,21; la 2.ª baja de 5,11 a 4,99). El motivo es contable: un cambio mínimo de λ mueve una
   carga o una descarga de una hora a otra casi equivalente, y si cae al otro lado del reparto, una mitad
   se queda el coste y la otra el ahorro.
4. El nivel tampoco es comparable entre mitades: con la misma política, 7,02 en una y 5,11 en la otra.
5. Consecuencia: diferencias de centésimas (o décimas) entre equipos que están en el óptimo son ruido del
   reparto, no calidad del controlador. Subir la nota pública retocando λ es posible, pero se paga punto
   por punto en la mitad privada.
6. En el leaderboard real, nuestro λ y el de la referencia difieren y aun así la nota pública coincide a
   0,0001 puntos: cerca de 0,25–0,26 el reparto real no cambia de lado ninguna operación.
