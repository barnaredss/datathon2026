# Submission log

## Hard mode (Mode Difícil — separate board and quota: 10 per shift)

Battery 6,000 kWh / ±1,500 kW, PV x12, 3 h of price/CO2 in obs. Local = `python -m tools.hard`.
Public board on Sat 18:30: 16 teams, record 23.23, most between 21 and 23.

| # | Time | Tag | Local pseudo-test | Local ceiling (perfect foresight) | Public score | ΔCO2 % | ΔCost % | Infr. | Notes |
|---|------|-----|-------------------|-----------------------------------|--------------|--------|---------|-------|-------|
| h0 | pending | hard_v0 | 19.54 | 22.28 | | | | | climatology forecasts; superseded |
| h1 | pending | hard_v1 | 20.51 | 22.28 | | | | | + ridge forecaster for price/CO2, discharge margin, optimistic PV |
| h2 | pending | hard_v2 | 20.58 | 22.28 | | | | | + discharge margin that grows with expected solar. Upload this one |

## Standard mode

Final selection: the jury scores exactly 2 submissions per team on the private half. Mark them in the
submission tab ("Selecció Oficial per al Jurat"): v3_load_aware and v2_meter_guard.

Paste the leaderboard result row after every upload. Never re-submit an equal agent.

| # | Time | Tag | Local train-full | Local pseudo-test | Public score | ΔCO2 % | ΔCost % | CO2 kg | € | Infr. | Notes |
|---|------|-----|------------------|-------------------|--------------|--------|---------|--------|---|-------|-------|
| 1 | Sat 14 Nov, 12:27:26 (board clock) | v1_lp_mpc | 5.6667 | 6.1241 | 6.43 | 5.96 | 7.52 | 4282.5 | 8934.63 | 0 | rolling 24 h LP, LAMBDA_PRICE 0.2593. Rank 5th: tied on score at 6.43, behind on timestamp |
| 2 | Sat 14 Nov, ~14:00 local | v2_meter_guard | 5.6667 | 6.1241 | 6.43 | 5.96 | 7.52 | 4282.5 | 8934.63 | 0 | v1 + guard for weeks without meter data. Team reports the exact same result as #1 → the guard never changed an action, so the public test has no low-demand periods |
| 3 | Sat 14 Nov, afternoon | v3_load_aware | 5.6667 | 6.1241 | 6.43 | 5.96 | 7.52 | 4282.5 | 8934.63 | 0 | v2 + weekly-profile demand estimate for low-demand weeks. Team reports no change on public. Any gain would be on the private half, which we cannot see |

Board after #2 (team "hackers la l"): still 5th with the original timestamp 12:27:26, so a repeat
submission with an equal score does not move the tie-break time.

Conclusion after #2: the board is saturated at 6.43. Local headroom to perfect foresight is 0.0009 points.
Do not spend more attempts unless a candidate is strictly better locally.

Reference on the public board (Sat 13:15): top 6.43, ΔCO2 5.97 %, ΔCost 7.50 %, 4289.4 kg, 8907.87 €.

5è	2026-11-14 12:27:26	hackers la l	6.43	5.96	7.52	4282.5	8934.63	0
