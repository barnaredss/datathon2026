# Submission log

Paste the leaderboard result row after every upload. Never re-submit an equal agent.

| # | Time | Tag | Local train-full | Local pseudo-test | Public score | ΔCO2 % | ΔCost % | CO2 kg | € | Infr. | Notes |
|---|------|-----|------------------|-------------------|--------------|--------|---------|--------|---|-------|-------|
| 1 | Sat 14 Nov, 12:27:26 (board clock) | v1_lp_mpc | 5.6667 | 6.1241 | 6.43 | 5.96 | 7.52 | 4282.5 | 8934.63 | 0 | rolling 24 h LP, LAMBDA_PRICE 0.2593. Rank 5th: tied on score at 6.43, behind on timestamp |
| 2 | Sat 14 Nov, ~14:00 local | v2_meter_guard | 5.6667 | 6.1241 | 6.43 | 5.96 | 7.52 | 4282.5 | 8934.63 | 0 | v1 + guard for weeks without meter data. Team reports the exact same result as #1 → the guard never changed an action, so the public test has no low-demand periods |

Conclusion after #2: the board is saturated at 6.43. Local headroom to perfect foresight is 0.0009 points.
Do not spend more attempts unless a candidate is strictly better locally.

Reference on the public board (Sat 13:15): top 6.43, ΔCO2 5.97 %, ΔCost 7.50 %, 4289.4 kg, 8907.87 €.

5è	2026-11-14 12:27:26	hackers la l	6.43	5.96	7.52	4282.5	8934.63	0
