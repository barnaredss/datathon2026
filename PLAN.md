# Master plan — Repte UPC Sostenible

Owner: orchestrator session (Fable). Workers: Sonnet subagents. One Pro account works, the second is
in reserve (see "Handover"). Deadline: submissions close Sunday 15 Nov between 12:00 and 15:00
(plan as if 12:00). Presentation: slides + pitch in Spanish.

## Status table (update on every task completion)

| ID | Task | Track | Prio | Owner | Status |
|----|------|-------|------|-------|--------|
| T0 | Kit, venv, hourly data, eval harness, agent v1 | Agent | P0 | orchestrator | DONE (Sat 13:30) |
| T1 | Submit v1 to leaderboard, log result | Agent | P0 | **humans** | DONE — 6.43 public, 0 infr., 5th on timestamp tie |
| T2 | Signal and horizon calibration study | Agent | P2 | Sonnet | DROPPED — headroom is 0.0009 pts; T5 already swept λ and horizon |
| T3 | Hardening tests + submission packager | Agent | P2 | Sonnet | TODO |
| T1b | Submit v2 (meter-outage guard), log result | Agent | P0 | **humans** | DONE — identical to v1 (6.43): the test has no outage weeks |
| T4 | Data audit + EDA figures | Jury | P1 | Sonnet | DONE — `analysis/eda_findings.md`, 6 `figures/eda_*` |
| T5 | Strategy evidence figures | Jury | P1 | Sonnet | DONE — `analysis/strategy_findings.md`, 5 `figures/est_*` |
| T5b | Meter-outage robustness study + agent v2 | Both | P0 | orchestrator | DONE — `analysis/outage_findings.md` |
| T6 | What-if study for UPC Sostenible | Jury | P1 | Sonnet | IN PROGRESS (started Sat ~14:05) |
| T7 | Slide deck, pitch script, Q&A sheet (Spanish) | Jury | P1 | Sonnet + orchestrator review | TODO (needs T4–T6) |
| T8 | Final agent selection, code doc pass, freeze | Agent | P0 | orchestrator | TODO (Sunday) |

Waves: **W1 = T4 + T5** (parallel), **W2 = T6 + T2** (parallel), **W3 = T3**, **W4 = T7**, then T8.
If usage runs short, drop in this order: T3, T2, T6. Never drop T5 or T7.

## Strategy (why the plan looks like this)

1. **The leaderboard has a hard ceiling and we are already on it.** The score is linear in grid imports,
   so the optimum is a linear program. With perfect foresight of the whole series the LP gives 5.6753 on
   train; our rolling 24 h agent gets 5.6667 (99.85 %). On a test-shaped set it is 6.1241 vs 6.1250.
   The two teams on the public board both show exactly 6.43 / 5.97 % / 7.50 % — the same ceiling.
2. **So ranking among good teams is decided by ties.** Tie-break 3 is the earliest timestamp → submit v1
   immediately (T1). Remaining upside is ≤ 0.01 points; it gets one bounded study (T2), no more.
3. **The jury decides the winner** ("valorarà de forma decisiva la presentació final, la claredat del
   raonament tècnic, l'anàlisi de les dades i la justificació de l'estratègia"). Most remaining effort goes
   to evidence and storytelling: prove optimality, show the data insight that makes forecasting
   unnecessary, and give UPC Sostenible recommendations they can use.
4. **No leakage, no public-mask overfitting.** Official data only. We do not probe the public/private split.
5. **The one real edge found so far: meter outages.** Train has no sensor data for all of November and
   the public baseline is 23–25 % lower per hour than train, so a test week with zero measured demand is
   plausible. v1 loses 0.02–0.25 points in that case; v2 (current `agent/agent.py`) recovers most of it
   and is identical to v1 on normal data. **Outcome (Sat ~14:00): v2 scored exactly the same as v1, so
   the public test has no low-demand periods.** v2 stays as the agent (robustness, no cost), but in the
   pitch this is a robustness check, not a source of score. The leaderboard is a tie at 6.43; no further
   attempts unless a candidate is strictly better locally. All remaining effort goes to the jury track.

## Submission calendar (30 attempts: 10 per shift; "Validació Ràpida" is free and unlimited)

| Shift | Window | Use |
|-------|--------|-----|
| 1 | Sat until 21:00 | v1 now. v2 only if T2 proves a gain. Max 3 attempts. |
| 2 | Sat 21:00 – Sun 08:00 | Nothing unless a proven candidate exists. No all-nighter. |
| 3 | Sun 08:00 – close | Final candidate if strictly better locally. Freeze 90 min before close. |

Rules: always run `tools/evaluate.py` + `check_submission.py` + the web "Validació Ràpida" first. Submit
only if the candidate beats the current best by ≥ 0.002 on BOTH local datasets with 0 infractions. Do not
re-submit an equal agent (it could move our tie-break timestamp later). Humans do every upload (PIN) and
paste the result row into `submissions/LOG.md`.

## Repo layout

```
agent/agent.py            the submission (single file, Spanish comments)
tools/build_hourly.py     raw CSVs -> data/hourly_train.csv, data/hourly_price_co2.csv
tools/evaluate.py         regression gate: load_hourly, pseudo_test, run_agent, perfect_foresight
analysis/style.py         shared matplotlib style (import it in every figure script)
analysis/*.py, *.md       studies and written findings
figures/*.png             all figures for the deck (Spanish labels)
slides/                   deck builder, pptx, pitch script, Q&A
submissions/<tag>/        frozen copies of what was uploaded + LOG.md
starter_kit/, docs/       official kit (read-only). data/train/ is git-ignored (re-download the ZIP)
```

`tools/evaluate.py` API that workers must reuse (do not re-implement):
`load_hourly() -> df[load_kw, pv_kw, precio_eur_per_kwh, co2_kg_per_kwh]`, `pseudo_test(df)` (10 weekly
blocks, 1,680 h), `load_agent(path) -> class`, `run_agent(cls, df) -> dict(score, dco2, dcost, infr, secs,
fallbacks, env)`, `perfect_foresight(df) -> score`, `precise_score(df, grid)`.
Variants are made by subclassing: `class V(BatteryAgent): LAMBDA_PRICE = 0.3`.

---

## T1 — Submit v1 (humans, now)

1. Open https://repteupc.datathon.cat → tab "Lliurament de Solucions".
2. Team name, PIN (your choice, keep it), member names.
3. Upload `submissions/v1_lp_mpc/agent.py`. Click "Validació Ràpida" first, then "Trametre al Leaderboard".
4. Paste score, ΔCO2 %, ΔCost %, kg, €, infractions and the time into `submissions/LOG.md`.
Expected: about 6.43, 0 infractions.

---

## T2 — Signal and horizon calibration (Sonnet, P2, budget ≤ 35 tool calls)

**Goal.** Decide with evidence whether any variant of v1 gains ≥ 0.002 score on both `train-full` and
`pseudo-test`. Expected answer is "no" or a tiny gain; the write-up is also slide material
("what we tried and discarded").

**Do.** Create `analysis/calibration.py` (uses `tools/evaluate.py`, subclasses `BatteryAgent`) and
`analysis/calibration.md`. Run every variant on pseudo-test (3 s each); run only each experiment's best
two on train-full (12 s each). Report scores with 4 decimals.
- E1 `LAMBDA_PRICE` ∈ {0, 0.10, 0.20, 0.23, 0.25, 0.2593, 0.27, 0.29, 0.32, 0.40, 1.0}.
- E2 `TERMINAL_VALUE` ∈ {0, 0.6, 0.9, 1.0, 1.1, 1.3} × 1.2 (1.2 ≈ mean of the scaled signal).
- E3 Horizon extension. Add to `agent/agent.py` a hook `_extend_signal(self, w, obs)` that by default
  returns `w` unchanged and is applied only when `len(w) == 24`. Variants append K ∈ {6, 12, 24} forecast
  hours: (a) repeat the same hours of the known 24 (`w[:K]`), (b) hour-of-day mean profile from
  `data/hourly_price_co2.csv`, rescaled so its mean matches the known 24 h. Terminal value applies at the
  end of the extended horizon.
- E4 Discharge cap for the current hour: last-hour net load (v1) vs always 500 vs 0.9 × last-hour net.
- E5 Only if E1 shows > 0.002 spread within 0.23–0.29: online `LAMBDA_PRICE` from running sums of
  `max(load−pv,0)·co2` and `·price` built from `noves_dades_5min` history, blended with the 0.2593 prior.

**Constraints.** The default behaviour of `agent/agent.py` must stay bit-identical unless a variant wins;
verify with `tools/evaluate.py` before and after (5.6667 / 6.1241). Follow every rule in `CLAUDE.md`.

**Done when.** `analysis/calibration.md` has one table per experiment, a one-paragraph conclusion, and a
recommendation "keep v1" or "adopt X" (adopt only if ≥ +0.002 on both sets, 0 infractions, < 15 s).
Do not change defaults yourself; the orchestrator decides.

---

## T3 — Hardening tests and packager (Sonnet, P2, budget ≤ 25 tool calls)

**Do.**
1. `tools/test_agent.py` (plain asserts, no pytest; exit code 1 on failure). Cases: `timestamp` as str and
   as `pd.Timestamp`; lookahead vectors of length 1…24 and unequal lengths; missing `noves_dades_5min`;
   NaN in price/CO2 vectors; SOC at 0, 1e-9, 1999.9999, 2000; zero and huge prices; `soc_pct` keys absent
   except `soc_kwh`; 5,000 random steps through `CampusBatteryEnv` on shuffled train rows → 0 infractions
   and no exception; fallback path (`_HAVE_LP = False` monkeypatched on the module) → runs, 0 infractions,
   print its pseudo-test score; 2,016 steps in < 15 s; AST scan via `check_submission.check_ast`; a grep
   that the agent source contains no `.stack(`.
2. `tools/make_submission.py <tag>`: runs evaluate + test_agent + check_submission, then copies
   `agent/agent.py` to `submissions/<tag>/agent.py` (zip at root level only if extra files exist) and
   appends a pending row to `submissions/LOG.md` with local scores.

**Done when.** Both tools run green on v1. If a test exposes a real bug in the agent, fix it minimally,
keep scores ≥ baseline, and say so in the report.

---

## T4 — Data audit and EDA figures (Sonnet, P1, budget ≤ 40 tool calls)

**Goal.** The "anàlisi de les dades" part of the jury criteria: 5 figures and a findings file that the
deck quotes. Every finding needs a number.

**Do.** `analysis/eda.py` → `figures/eda_*.png` + `analysis/eda_findings.md` (≤ 60 lines, numbered).
Raw files are in `data/train/` (see `docs/GUIA_VARIABLES.md` for column meanings; `inversor.csv` is 64 MB,
load only the needed columns). Answer:
1. Coverage: which days exist per month; why November 2025 has price/CO2 but no hourly load row (which
   sensor file is missing it); gaps, duplicated timestamps, zero-load hours (count, dates).
2. Night load: hourly mean load is identical for hours 0–5 (972.968). Find out whether the meter data is
   flat/imputed at night or it is an artefact of the pipeline. State it plainly.
3. Scale: PV vs load (mean, peak, share of energy); share of hours with net load < 500 kW and < 0.
   Figure `eda_escala.png`: daily profile of load vs PV on the same axis.
4. Signals: hour × month heatmaps of price and of CO2 (`eda_heatmaps.png`); average daily profiles of
   both, normalised (`eda_perfiles.png`); correlation overall and by month; the hours where they
   disagree most (cheap but dirty, clean but expensive) (`eda_precio_vs_co2.png`).
5. Calendar effects on load: weekday vs weekend, August/holidays (`eda_calendario.png`).
6. Spread available to a battery: per day, (max − min/0.9) of the composite signal
   `w = co2 + 0.2593·price`; distribution by month. This is "how much there is to win" each day.

**Style.** `from analysis.style import apply, COLORS; apply()`; Spanish titles that state the takeaway;
1600×900 px. Do not open figures with the Read tool more than twice in total.

**Done when.** Script runs end to end in < 2 min, 5 PNGs exist, findings file written.

---

## T5 — Strategy evidence figures (Sonnet, P1, budget ≤ 40 tool calls)

**Goal.** Prove to the jury that the strategy is optimal and explain where the value comes from.

**Do.** `analysis/strategy.py` → `figures/est_*.png` + `analysis/strategy_findings.md` (numbers for the
deck). Reuse `tools/evaluate.py`; build variants by subclassing `BatteryAgent`.
1. `est_escalera.png` — benchmark ladder on train-full and pseudo-test (grouped bars, score):
   no battery (0); official template `starter_kit/agent.py` (show both its real score with infractions
   and its score before penalties); price-only signal (override `_signal` to use price only);
   CO2-only (`LAMBDA_PRICE = 0`); our MPC; perfect foresight. Annotate "% of the optimum".
2. `est_horizonte.png` — value of lookahead: truncate the two lookahead vectors to
   H ∈ {1, 2, 4, 6, 8, 12, 18, 24} in a subclass; plot score vs H with the perfect-foresight line.
3. `est_pareto.png` — sweep `LAMBDA_PRICE` over 0 … 5 (≈ 15 values, log-spaced plus 0): ΔCost % vs ΔCO2 %
   curve, our operating point marked, iso-score lines for the 70/30 formula.
4. `est_semana.png` — one representative pseudo-test week, three stacked panels sharing the x axis:
   price and CO2; composite signal with charge/discharge hours shaded; SOC and battery power.
5. `est_horas.png` — mean battery power by hour of day (and by season if readable): when we charge
   and when we discharge.
6. Numbers in the findings file: cycles per day; kWh shifted per day; CO2 avoided and € saved on
   train-full and extrapolated to a full year (× 8760 / hours); runtime; infractions; value of
   load/PV knowledge (score with the current-hour discharge cap using the TRUE net load vs v1 vs no cap).

**Style and done-when.** Same as T4. Script may take a few minutes: run it in the background.

---

## T6 — What-if study for UPC Sostenible (Sonnet, P1, budget ≤ 30 tool calls)

**Goal.** Turn the optimiser into recommendations: the part of the pitch that goes beyond the score.

**Do.** `analysis/whatif.py` → `figures/whatif_*.png` + `analysis/whatif_findings.md`. Generalise the
perfect-foresight LP of `tools/evaluate.py` into a function with parameters (capacity, power, efficiency,
PV scale factor, alpha/beta). Use train-full; report ΔCO2 %, ΔCost %, kg CO2/year, €/year.
1. `whatif_dimensionado.png` — capacity {500, 1000, 2000, 4000, 8000} kWh × power {250, 500, 1000,
   2000} kW: heatmap or curves of yearly € and kg CO2; marginal value of the next kWh and the next kW.
   Which is the binding constraint today, energy or power?
2. `whatif_rendimiento.png` — round-trip efficiency 80 … 98 %.
3. `whatif_solar.png` — PV scaled ×1 … ×20: at which size does midday surplus appear, and how does the
   battery's value change (exports earn nothing in this model).
4. Weights: score-optimal dispatch for alpha ∈ {0, 0.3, 0.5, 0.7, 1} — what UPC gives up in € for
   each extra kg of CO2 avoided. Also state the carbon price implicit in the official 70/30 formula:
   λ = 0.2593 kg CO2 per € means 1 kg CO2 is worth 1/λ ≈ 3.86 €, i.e. ≈ 3,860 €/t CO2 (recompute
   from train baselines and report the exact figure).
5. A simple operator rule (fixed charge hours / discharge hours by season, with the safety clamp) and
   the % of the optimum it captures — an interpretable fallback for the facility manager.

Any figure not derived from the official data (e.g. battery price for payback) must be labelled as an
illustrative assumption. **Done when** as T4.

---

## T7 — Deck, pitch and Q&A in Spanish (Sonnet builds, orchestrator reviews, budget ≤ 40 tool calls)

**Inputs.** `analysis/*_findings.md` (eda, strategy, outage, whatif, calibration), `figures/*.png`,
`agent/agent.py`, `submissions/LOG.md`. Slide 8 must include the meter-outage story from
`analysis/outage_findings.md`: the audit found the November gap, we stress-tested it, v2 is robust.

**Do.** `slides/build_deck.py` (python-pptx, 16:9, content in a Python dict so text edits are one-line) →
`slides/presentacion.pptx`; `slides/guion.md` (pitch script, ~5 min, per slide, plain spoken Spanish);
`slides/qa.md` (15 likely jury questions with 2–3 sentence answers and the backing number).
Storyline (one message per slide, a figure on every slide that has one):
1. Título, equipo, resultado: score, 0 infracciones, "99,9 % del óptimo teórico".
2. El reto y la fórmula del Score.
3. Lo que dicen los datos: la FV es el 2,4 % de la demanda; demanda neta > 500 kW el 99,5 % de las horas
   → la batería nunca vierte y predecir consumo no aporta.
4. Idea clave: el Score es lineal → una sola señal `w = CO2 + λ·precio` (derivación en tres líneas).
5. La solución: MPC con programación lineal exacta sobre las 24 h conocidas; clamp de seguridad; respaldo.
6. Una semana de operación (est_semana).
7. ¿Es óptimo? Escalera de benchmarks + cota de información perfecta + valor del horizonte.
8. Lo que probamos y descartamos, con números (predicción, horizonte extendido, calibración de λ).
9. Recomendaciones para UPC Sostenible (Pareto CO2–coste, dimensionado, más FV, regla del operador).
10. Conclusiones y siguientes pasos.
Backup: calidad de datos; detalle del LP; robustez y tests; sensibilidades.

**Rules.** Every number on a slide must come from a findings file (cite the file in the speaker notes).
No claims about external data. Plain, direct Spanish; no filler. **Done when** the pptx opens, has no
overflowing text, and the script reads in ≤ 5 min 30 s.

---

## T8 — Final selection and freeze (orchestrator, Sunday morning)

- Pick the final agent from `submissions/LOG.md` + local gate. Final doc pass on `agent/agent.py`
  (Spanish, explains the maths; the jury audits it). Write `README_SOLUCION.md` (1 page, Spanish).
- Rehearse: the humans read `slides/guion.md` once aloud; orchestrator trims.
- Freeze code 90 min before close; last upload at least 60 min before close.

---

## Handover to the reserve account

1. `git pull`, open Claude Code in the repo. If `data/train/` is missing: download the participants ZIP
   from the challenge site ("Dades del Campus" tab) and unzip it into the repo root.
2. `python -m venv .venv` then `./.venv/Scripts/python.exe -m pip install -r requirements.txt`.
3. Prompt: "Read CLAUDE.md and PLAN.md. You are the orchestrator. Continue from the status table.
   Dispatch Sonnet subagents with the task briefs verbatim, review their reports, update the table, commit."
4. On every task completion: update the status table, commit, push.

## Open items for the humans
- GitHub: create a PRIVATE repo and give the orchestrator the remote URL.
- Confirm pitch length and exact closing time when the organisers announce them.
- Helmcode API key: purpose unknown, not needed by the plan (the agent cannot use the network). Parked in `.env`.
