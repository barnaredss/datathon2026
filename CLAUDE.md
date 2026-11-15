# Datathon 2026 — Repte UPC Sostenible (battery control)

Read this first, then `PLAN.md` (status table at the top tells you what is done and what is next).

## The challenge in 10 lines
- Write `BatteryAgent.act(obs) -> kW` (charge > 0, discharge < 0), called hourly for 2,016 test hours
  (12 one-week blocks = last week of each month; SOC carries across blocks; one agent instance).
- Battery: 2,000 kWh, ±500 kW, 90 % round trip (eta = sqrt(0.9) each way), starts at 1,000 kWh, no degradation.
- `obs` gives current + next-24-rows price and CO2 (index 0 = current hour; the vector is row-based, so near
  a block end it already contains the next block; it gets shorter than 24 only at the very end), SOC, and
  last hour's load/solar. `obs["timestamp"]` may be a `pd.Timestamp` or a `str`.
- Score = max(0, 70·ΔCO2 + 30·ΔCost − 0.20·infractions), deltas relative to the campus without battery.
  Exports earn nothing (no cost credit, no CO2 credit). Ground truth: `starter_kit/environment.py`.
- Public leaderboard = 50 % of each test week; private 50 % decides. The jury weighs the presentation decisively.
- Tie-break: score, then fewer infractions, then EARLIEST timestamp.

## What we already know (do not re-derive)
- Net campus load (load − PV) is > 500 kW in 99.5 % of hours and never negative; PV is ~2.4 % of load.
  So the battery never exports and load/PV forecasting is worth ~0. The task is pure arbitrage.
- The score is linear in grid imports, so it collapses to ONE signal: `w = co2 + LAMBDA_PRICE * price`
  with `LAMBDA_PRICE = (0.3/0.7) * CO2_base / Cost_base` ≈ 0.2593 (calibrated on public leaderboard data).
- Organisers (Sat afternoon): several teams tie at the public maximum, but on the PRIVATE ranking no team
  has reached the maximum. We cannot see private scores. Working hypothesis: low-demand hours (holiday
  weeks) or meter outages in private stretches, where discharge beyond net demand is exported for nothing.
- `agent/agent.py` is now v3 = v2 + weekly-profile estimate of net demand (WEEK_PROFILE, 168 values from
  train) used as per-hour discharge caps inside the current block. Identical to v2 on normal data; closes
  12–53 % of the gap to perfect foresight on synthetic low-demand weeks (`analysis/lowload_findings.md`).
  With a perfect 24 h demand forecast the MPC is back within 0.001 of the bound, so in low-demand weeks
  demand forecasting is the lever.
- (history) v1/v2 = rolling 24 h LP on that signal. Train-full 5.6667 vs perfect-foresight 5.6753;
  pseudo-test 6.1241 vs 6.1250. 0 infractions, 4–8 s per 2,016 steps. We are at the ceiling.
- Public leaderboard top is 6.43 (ΔCO2 5.97 %, ΔCost 7.50 %) — the same ceiling. Our v1 scored 6.43.
- Meter outages: all four sensor files have no data for November 2025; 15 hourly rows have load 0; the
  meter is frozen every night 22:05–06:00 (one repeated value). v2 adds a guard: when the last measured
  net load is < 500 kW the LP assumes it persists to the end of the current 168 h block (it detects block
  starts from timestamp jumps > 2.5 h). Identical to v1 on normal data; see `analysis/outage_findings.md`.
  v2 scored exactly like v1 on the public board, so the test has no low-demand periods: present the guard
  as a robustness check, never as a source of score.
- The FULL-test score is saturated (headroom 0.0009 pts). The PUBLIC-half score is not stable: nudging
  LAMBDA_PRICE within 0.18–0.32 moves a half-test score by 0.14–0.46 while the full score moves 0.01,
  and it is zero-sum with the private half (`analysis/split_noise_findings.md`). Do not submit λ variants
  until the humans report how the final ranking is computed (private half or full test; which submission).
- UI: `ui/bot_src.html` + `python -m ui.build_bot` → `ui/bot.html` (artifact https://claude.ai/artifact/5rmyb5vc6S3JduorJMjpVX)
  and `ui/bot_local.html` (offline). Screenshot for the deck: `figures/ui_bot_crop.png`.
- Findings so far live in `analysis/eda_findings.md`, `strategy_findings.md`, `outage_findings.md`.

## Hard mode (added by the organisers Saturday afternoon — the live competition)
- Separate tab, board and quota. Battery 6,000 kWh / ±1,500 kW (start 3,000 kWh), PV x12 (real midday
  surplus, free to store; exports still earn nothing), obs price/CO2 vectors only 3 long (current hour + 2),
  `obs["noves_dades_5min"]` adds last-hour weather, obs has `cap_max_kwh` and `power_max_kw`.
- New rule (both modes): the jury scores exactly 2 submissions per team on the private half; teams mark
  them in the submission tab, default = the two best public ones.
- Code: `agent_hard/agent.py` (source, `PROFILES` marker), `tools/hard.py` (simulator `HardEnv`, perfect-
  foresight bound, profile + ridge fit, `python -m tools.hard` evaluates), `tools/hard_pack.py <tag>`
  freezes a single-file submission with profiles from the full train set.
- Method: 24 h LP on FORECAST signal, demand and solar. Price/CO2 beyond 3 h: ridge regression per lead
  on ratios to a month×daytype×hour climatology. Demand: last value × weekly profile. Solar: monthly
  profile × observed clearness. Current-hour discharge is capped conservatively (exports are lost).
- Status (hard_v3): pseudo-test 20.68 vs ceiling 22.28 (92.8 %). Remaining gap, measured with oracles:
  perfect signal forecast +0.65; true CURRENT-hour net demand +0.62 (knowing later hours adds nothing);
  both together 98.5 %. Each test week is seeded with the last 48 training hours (`PROFILES["prehist"]`:
  the train set ends the day before every test week). Current-hour discharge uses a newsvendor quantile
  from the LP dual (`_newsvendor`); the same rule for charging made things worse and is off.
- hard_v4 adds a tree-based nowcast of the CURRENT hour's solar (`PROFILES["pv_gbm"]`, fitted with LightGBM
  in `tools/hard.py::fit_pv_gbm`, evaluated in pure Python in the agent): pseudo-test 20.80 (93.3 %).
- Public calibration: hard_v3 = 20.68 local → 23.29 public (rank 5 of 24; top 23.46). Public ≈ 1.126 × local.
- Tried without gain: longer horizon, terminal value, planning with lower efficiency, surplus buffers,
  LightGBM instead of ridge for price/CO2, ridge per (lead, target hour), yesterday-blend climatology,
  compressing or expanding forecast spread, price-weight multipliers, newsvendor rule for charging.
- The agent's dispatch by hour is close to the perfect-foresight plan; the residual is timing noise from
  forecast error (e.g. it charges at 01:00 where perfect foresight waits for 03:00–04:00).
- hard_v4 = 23.44 public. hard_v5 adds holiday detection (weekday that behaved like a Sunday → Sunday shape
  for the following weekdays): same as v4 on normal weeks, +0.28 on synthetic holiday weeks.
- Sunday board: top 27.98 (16.2 kg/h avoided = our local PF kg/h). Public baseline/hour is 20 % below our
  validation weeks; with lower demand the PF rises a lot (load ×0.8 → PF 29.0) and the agent sits at
  90–92 % of it. Prudence-parameter sweeps on low-demand scenarios are flat (`analysis/hard_findings.md` §8).
- hard_v6 adds `CALENDARIO` (official Catalan/Barcelona holidays + UPC 2025-26 non-teaching periods, public and
  known in advance) to the demand shape: +0.155 out of sample on holiday weeks (`hard_findings.md` §9).
  The user asked to look at external data; we use only information known before each hour. Never embed
  real observed weather/prices of the test weeks.
- Local pseudo-test profiles are fitted out of sample; always check `fallbacks=0` in the output.

## Hard rules
- Official data plus information known in advance only (the public holiday / UPC calendar, asked for by the user
  on Sunday). Never embed real observed test-period prices, CO2, weather or demand in the agent.
- The submitted agent may import only: numpy, pandas, scipy, scikit-learn, joblib, xgboost, lightgbm, math,
  datetime, collections, itertools, random, json, pathlib, typing.
- AST scanner rejects: imports of os, sys, shutil, subprocess, socket, urllib, requests, http, importlib,
  inspect, gc, builtins, threading, multiprocessing, ctypes, signal; calls named `.system() .popen()
  .spawn*() .rmtree() .stack() .get_objects() .currentframe()` (so NO `np.stack` / `df.stack` — use
  `np.concatenate` / `np.column_stack`); builtins eval, exec, compile, globals, locals, vars, __import__;
  attributes `__globals__ __code__ __builtins__ __subclasses__ f_back f_locals f_globals`.
- Prefer no `.pkl` (server library versions unknown). If state is needed, ship constants or JSON.
- Zero infractions always: every return goes through `_clamp`. Runtime limit is 60 s total; keep < 15 s.
- LP objective coefficients must be O(1) (HiGHS tolerance 1e-7 silently breaks tiny coefficients).
- `agent/agent.py` is the single source of truth for submissions. Never edit files in `submissions/`.
- Code comments and docstrings of the agent, all figures, slides and the pitch are in SPANISH
  (the jury audits the code). Internal tooling, plan and reports are in English.
- Never commit `.env`, `.venv/`, `_download/`, `data/train/`.
- GitHub: https://github.com/barnaredss/datathon2026 (remote `origin`). FROZEN since the deadline (Sun 15 Nov 2026):
  NEVER commit or push. A late commit can invalidate the project. Leave local edits uncommitted.

## Commands (Windows, Git Bash)
- Python: `./.venv/Scripts/python.exe` (3.14; numpy, pandas, scipy, sklearn, lightgbm, xgboost, matplotlib)
- Rebuild hourly data: `./.venv/Scripts/python.exe tools/build_hourly.py`
- Regression gate: `./.venv/Scripts/python.exe tools/evaluate.py [agent_path]` (~15 s)
- Official checker: `./.venv/Scripts/python.exe starter_kit/check_submission.py agent/agent.py`
- Study/figure scripts run as modules from the repo root: `./.venv/Scripts/python.exe -m analysis.eda`
  (so `from analysis.style import ...` and `from tools.evaluate import ...` resolve).

## Token discipline (we are on limited Pro usage)
- Subagents run on Sonnet, get one self-contained brief from `PLAN.md`, and do not spawn agents.
- Write results to files; the final report to the orchestrator is ≤ 150 words: what changed, key numbers,
  file paths, open issues. No code or tables pasted in the report.
- Never print dataframes or long logs to the console; print one-line summaries. Never read raw CSVs with
  the Read tool (use pandas). Run anything longer than ~60 s in the background.
- Do not re-explore what this file already states. Do not refactor outside your task's files.
