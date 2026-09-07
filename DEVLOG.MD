# Development Log

## 2026-09-01 — Pricing model, real road routing, manual + live logging

### Goal for the session

Finish blocks 4–6 of the any-route pricing pipeline: the surge pricing formula, the synthetic historical dataset generator, and the two logging tools (manual ground-truth logger + automated live collector).

---

### 1. Pricing model (`pricing.py`)

Built `peak_factor(hour, is_friday)` — a bimodal Gaussian curve (two bell curves, morning and evening) representing commute congestion intensity across the day. Built `estimate_price()` on top of it, combining:

- A per-vehicle-type base fare (`VEHICLE_TYPES` dict: Auto, Mini, Sedan)
- The peak-hour signal
- A weekend damping factor
- A rain bump
- A legally-bounded surge multiplier

**Key design change during the session:** surge was originally computed by *adding* bonuses on top of `1.0x` (uncapped). Rewrote it to compute a single `raw_signal` (0–1, "how busy right now"), then map that onto a real legal range:

```python
surge = MIN_SURGE + (MAX_SURGE - MIN_SURGE) * raw_signal
```

This guarantees output can never exceed what's legally possible.

**Real data sourced and cited (not invented):**
- Evening peak weighted 1.27x stronger than morning peak — derived from TomTom's 2023 Bengaluru Traffic Index (15 min extra delay in morning rush vs. 19 min in evening rush, on a 10km trip; 19/15 ≈ 1.27). [Deccan Herald]
- Surge legally bounded 0.5x–2.0x of base fare — India's 2025 Motor Vehicle Aggregator Guidelines (MoRTH). Karnataka independently had a matching state-level cap (2x standard, 2.25x luxury) pre-dating the national rule. [Business Standard]
- Friday 6–7pm flagged as the worst recurring citywide traffic window — same TomTom data.
- Auto night surcharge (1.5x, 10pm–5am) — real, DTA-mandated as of August 2025.

**Explicitly flagged as NOT sourced (unverified assumptions), documented rather than hidden:**
- Peak center times (9am / 7:30pm) and curve width parameters — reasonable guesses, not from a dataset.
- The magnitude of the Friday-evening multiplier (1.15x) — the *existence* of the Friday effect is sourced, the *size* of the bump is not.

**A real mistake caught and corrected mid-session:** initially anchored the "Auto" vehicle tier to Karnataka's government-regulated auto-rickshaw meter tariff (₹36 first 2km, ₹18/km after — real, current, government data). This was wrong to use here — independent reporting confirms Bangalore app-based auto fares diverge sharply from the regulated meter rate (a real ₹201 fare for a 6km ride vs. a ~₹108 meter-rate equivalent), and there's an active, unenforced Karnataka High Court ruling on exactly this gap. Re-anchored the Auto tier to the one real *reported app fare* instead, clearly labeled as "one observed report, not an official rate" rather than presenting government data as if it represented something it doesn't.

---

### 2. Historical data generator (`data_generator.py`)

Generates synthetic training data by sampling random pickup/dropoff points inside a Bangalore bounding box, at random timestamps across the last 30 days, and pricing each pair using the block 4 formula.

**Major mid-build revision — distance calculation:**

First version used `haversine_km()` (straight-line distance) with a flat "circuity factor" (×1.4) to approximate real road distance. This was challenged and correctly identified as flawed: a flat multiplier can't distinguish a near-direct route (e.g. Kogilu → Esteem Mall, circuity ≈ 1.0) from a highly indirect one (e.g. Bellandur → Kempegowda Airport, real circuity ≈ 1.8, confirmed via multiple sources reporting 45–56km road distance against a ~30.7km straight-line distance).

**Fix:** replaced the circuity approximation entirely with **OSRM** (Open Source Routing Machine), using its free public demo server (`router.project-osrm.org`) to get real road-network routing distance per specific pair of points — no approximation, no key, no card required, same usage-policy shape as Nominatim (1 req/sec fair use).

**Consequence:** OSRM's rate limit meant the generator could no longer produce tens of thousands of rows instantly. Reduced target from an (accidental) ~64,000 rows down to a deliberate 500 rows (~8–9 minutes to generate) — fewer rows, but every one backed by real routing rather than an approximated multiplier. Also switched from a fixed time-step loop to randomly sampling both location pairs *and* timestamps, since each row now costs a real network call and shouldn't be wasted on a rigid schedule.

Added `training_data.csv`, `real_prices.csv`, `watched_routes.csv` to `.gitignore` — these are generated/logged outputs, not source, and (with real OSRM calls in the mix) not perfectly reproducible run-to-run even with the same seed.

---

### 3. Manual logger + live collector (`manual_logger.py`, `collector.py`)

Two separate files, deliberately: `manual_logger.py` records **ground truth** (real prices you type in after checking the actual app); `collector.py` records **our own model's predictions** over time for a fixed watchlist of routes. Neither replaces the other — one checks if the model is *right*, the other checks if it's *internally consistent*.

`manual_logger.py` loops through all vehicle types and lets you leave a price blank (skip) if that type wasn't shown for a given route/time, rather than forcing a single vehicle-type choice up front.

`collector.py` uses a geocode cache (`_geocode_cache` dict) so repeated runs against the same watched routes don't re-hit Nominatim's rate limit unnecessarily — only a genuinely new place name triggers a real lookup + the mandatory 1-second pause.

---

### Bugs hit and fixed today

| Bug | Symptom | Fix |
|---|---|---|
| `data[1]["lon"]` instead of `data[0]["lon"]` in `geocode()` | Silently mixed coordinates from two different Nominatim results | Both indices corrected to `data[0]` |
| `&&` used instead of Python's `and` | `SyntaxError` | Replaced with `and` |
| Referenced `max_lat`/`min_lat` as bare variables | `NameError` | Corrected to dictionary access, `bounds["max_lat"]` etc. |
| `Bangalore_bounds` vs actual `bangalore_bounds` (capitalization mismatch) | `ImportError: cannot import name 'Bangalore_bounds'` | Matched exact variable name across files |
| Dead code left after `return distance` inside `haversine_km` | Not an error (unreachable code), but leftover cruft from editing | Removed |
| Missing `import requests` in `spatial.py` | Would `NameError` the moment `get_road_distance_km` was actually called | Added import |
| Missing `.` between `input(...)` and `.strip()` in `manual_logger.py` | `SyntaxError` | Added missing `.` |
| `ModuleNotFoundError: No module named 'h3'` | Forgot to `pip install h3` before running `spatial.py` | Installed |
| PowerShell `cd D:\PROJECTS` from C: drive silently not changing drives | Prompt stayed on `C:\Windows\System32` despite `cd` "succeeding" | Used `cd /d D:\PROJECTS` instead |
| `git config --global` → `Permission denied` on `.gitconfig` | Couldn't set name/email | Re-ran terminal as Administrator |
| **Stray top-level test code left outside `if __name__ == "__main__":` in `geocoding.py`** | Every file that imported `geocoding.py` (collector, manual logger, data generator) silently fired two extra real geocoding calls and printed unlabeled `True`/`False` on every run | Moved the stray `geocode(...)` + `print(is_in_blr(...))` calls inside the existing `if __name__` block |

---

### Real-world calibration check

Ran `collector.py` at 12:38 AM for 3 routes × 3 vehicle types. Model correctly applied the legal price *floor* (0.5x surge) since `peak_factor` saw no commute-peak signal at that hour.

Then manually checked the real Uber app for the same routes at the same time. **All 8 real prices came back higher than predicted — never lower — by a factor of roughly 1.0x–1.9x** when solved backward for implied real surge.

**Diagnosis:** `peak_factor` only models commute-driven *demand* (traffic congestion at rush hour). It has no concept of late-night driver *scarcity* — a separate, real supply-side surge effect Uber's actual algorithm accounts for and ours currently doesn't.

**Planned fix (block 8):** rather than hand-tuning yet another guessed constant, blend real logged data into model training alongside the synthetic dataset — training primarily on the large synthetic set (teaches general price shape: distance scaling, vehicle-type differences, commute peaks), then weighting/fine-tuning on real logged rows so the model corrects toward observed reality wherever the simulation is wrong. Standard sim-to-real technique.

---

### Open items for next session

- [ ] Block 7: feature engineering (one-hot encoding vehicle type, etc.)
- [ ] Block 8: model training, incorporating real + synthetic data blend
- [ ] Continue manual logging at varied times of day (currently only have late-night data points — need at least one real evening-rush data point to properly validate the *existing* commute-peak logic, separate from the newly-discovered late-night gap)
- [ ] AWS account + infra setup (deferred until local pipeline is fully working)

## 2026-09-02 — Feature engineering, first trained model, surge vs. price target decision

### Goal for the session

Finish block 7 (feature engineering) and block 8 (train the actual ML model), moving from a hand-written pricing formula to a real model that learns from data.

---

### 1. Feature engineering (`features.py`)

Built a pipeline combining two data sources into one training table:

- **Synthetic data** (`training_data.csv`, 500 rows) — large, cheap, covers many routes/times, but only as accurate as the hand-written formula that generated it.
- **Real logged data** (`real_prices.csv`, growing via `manual_logger.py`) — small, but ground truth.

**Sim-to-real blending:** real rows are duplicated (`real_weight=5`) before being combined with the synthetic set, so a small number of real observations meaningfully influence training instead of being drowned out by the much larger synthetic set.

**One-hot encoding:** `vehicle_type` (text: "Auto"/"Mini"/"Sedan") converted to three separate 0/1 columns (`vt_Auto`, `vt_Mini`, `vt_Sedan`) via `pd.get_dummies()`. Necessary because assigning plain numbers (Auto=1, Mini=2, Sedan=3) would falsely imply an order/distance between categories that doesn't exist.

Introduced `pandas` properly this session — DataFrames as the working data structure, replacing manual `csv.DictReader` loops used everywhere else so far. Noted: pandas auto-converts "True"/"False" text columns to real booleans on read, unlike plain `csv` module — a behavior difference worth remembering given the manual string-comparison trap hit earlier with `csv.DictReader` in `compare_predictions.py`.

---

### 2. First trained model (`model.py`)

Installed `scikit-learn`, `joblib`. Built `train()`:

- Split data 80/20 (train/test) via `train_test_split`, `random_state=42` for reproducibility.
- Trained a `GradientBoostingRegressor` — an ensemble of decision trees, each correcting the errors of all trees before it.
- Evaluated with **MAE (Mean Absolute Error)** — average of `|predicted - actual|` across held-out test rows, i.e. genuinely unseen data, not training data being re-checked.
- Saved the trained model + one-hot column list together via `joblib.dump()`, to `surge_model.pkl`.

**First run, target = `surge`:** MAE = 0.136 surge points on held-out data.

**Checked `model.feature_importances_`** to see what the model actually relied on:

| Feature | Importance |
|---|---|
| hour | 88.5% |
| distance_km | 5.9% |
| is_weekend | 4.4% |
| vt_Auto | 1.0% |
| vt_Sedan | 0.1% |
| vt_Mini | 0.05% |

---

### 3. Key decision: switched prediction target from `surge` to `price`

**Reasoning:** the feature importance table wasn't a model bug — it was the model accurately learning that in our formula, `surge` only depends on hour/weekend/rain, never on distance or vehicle type. But that's not actually what matters to a rider — they care about the final price, which *does* depend heavily on distance and vehicle type (via base fare). Predicting `surge` alone gives an incomplete picture; predicting `price` directly captures the whole thing at once and is a more directly usable output for the eventual live demo (`main.py`).

**Consequence for `features.py`:** simplified, not just changed — since real rows already have a real logged `price` in `real_prices.csv`, no reverse-engineering through `estimate_price()` was needed anymore (previously required to back out implied surge for real rows, same algebra as `compare_predictions.py`). Removed the `pricing.py` import and the per-row surge-backing-out loop entirely. `X` (features) unchanged; only the target column swapped (`combined["surge"]` → `combined["price"]`).

**Expectation set before rerunning:** MAE will look numerically larger under the price target (rupees, hundreds-scale) vs. the surge target (a 0.5–2.0 range) — this is a unit-scale difference, not a worse model, and shouldn't be compared to the old `0.136` figure directly.

*(Retrain with the new price target pending — to be run and recorded next session.)*

---

### Bugs / environment issues hit today

| Issue | Symptom | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'pandas'` despite having installed it previously | A `.venv` (virtual environment) was active in this terminal session, isolated from whatever global Python environment `pandas` was originally installed into | Reinstalled all required packages (`requests h3 pandas scikit-learn joblib`) explicitly inside the active `.venv` |

---

### Concept: why the model doesn't "keep learning" automatically

`GradientBoostingRegressor` is a **batch learner** — it has no built-in mechanism to incrementally absorb one new example at a time. New rows added to `real_prices.csv` via `manual_logger.py` have zero effect on the saved `surge_model.pkl` until `python model.py` is explicitly rerun, retraining from scratch on the full (old + new) dataset. This is standard practice in real ML systems (e.g. "retrain nightly"), not a limitation specific to this project — later, this is exactly what the scheduled "ML training" step in the AWS architecture (from the earlier planning session) is meant to automate.

---

### Open items for next session

- [ ] Rerun `model.py` with the new `price` target, record new MAE + feature importances
- [ ] Confirm `distance_km` and `vehicle_type` now carry meaningfully more importance
- [ ] Write the "predict next price drop" scanning logic on top of the trained model
- [ ] Build `main.py` — the first true end-to-end live demo (type a route, get a real prediction)
- [ ] Continue logging real data at varied times (weekend day still outstanding)

## 2026-09-02 (continued) — Price-target retrain, sanity check, and calibration hitting a data wall

### Retrained with `price` target (block 8, second pass)

After switching the model's prediction target from `surge` to `price` (see previous entry), retrained and confirmed the change worked as intended.

**MAE:** Rs.78.38 on held-out data. NOT comparable to the previous 0.136 figure — that was in surge units (0.5–2.0 scale), this is in rupees (hundreds scale). Against real logged prices ranging ~Rs.130–680, an average error of ~Rs.78 is a reasonable first-pass result, expected to improve as more real data accumulates.

**Feature importance shifted exactly as predicted** when moving from surge to price:

| Feature | Predicting surge (before) | Predicting price (now) |
|---|---|---|
| hour | 88.5% | 49.1% |
| distance_km | 5.9% | **38.0%** |
| vt_Auto | 1.0% | 7.5% |
| vt_Mini | 0.05% | 4.0% |
| is_weekend | 4.4% | 1.2% |
| vt_Sedan | 0.1% | 0.2% |

`distance_km` jumping from ~6% to 38%, and vehicle type from near-zero to meaningful, confirms the model now learns the whole price picture (base fare + surge) rather than just the time-driven surge half. This was the entire point of the target change.

### Added prediction + sanity-check functions to `model.py`

Added `load_model()` and `predict_price()` — the latter rebuilds the exact input shape the model expects (including one-hot vehicle columns) for a single prediction. This is also the function `main.py` will eventually call.

**Sanity check across four hand-picked routes:**

| Route | Predicted | Directionally correct? |
|---|---|---|
| 5.7km Mini @ 13:00 | Rs.33 | **No — implausibly low** |
| 5.7km Mini @ 19:00 | Rs.280 | Yes (evening > midday ✓) |
| 30km Sedan @ 19:00 | Rs.1014 | Yes (long premium ride ✓) |
| 5.7km Auto @ 03:00 | Rs.138 | Yes (night surcharge ✓) |

Three of four moved in sensible directions — the model correctly learned time/distance/vehicle relationships. The Rs.33 midday Mini is implausibly low: 1pm is a dead zone in the pricing model (surge pushed to the 0.5x legal floor), combined with thin real midday data and unsourced Mini base numbers (`base_fare: 40, per_km: 12`, guesses from early on). The sanity check did its job — surfaced a real weakness the aggregate MAE had averaged over.

### Calibration attempt (`calibrate.py`) — hit a data wall twice

Wrote `calibrate.py` to back out real `base_fare`/`per_km` for Mini from logged prices, using least-squares linear regression (fitting `base_price = base_fare + per_km × distance` to real `(distance, implied_base)` points, after stripping out estimated surge).

**Attempt 1 (all 6 Mini rows): produced `base_fare = -579.7` (impossible).**
Diagnosis: the three late-night rows (~00:30) had their surge estimated at the 0.5x floor by `peak_factor`, which has no concept of late-night driver scarcity (the same gap found in the earlier calibration session). Dividing genuinely-high real late-night prices by a wrongly-low 0.5x surge dumped all the unexplained cost into "base fare," inflating implied bases to Rs.289–964 and breaking the fit. The negative result was the math correctly signaling the input surge estimates were wrong for those rows.

**Attempt 2 (excluded 10pm–5am rows): produced `per_km = -4.7` (impossible).**
Diagnosis: this left only 3 daytime points, all clustered within ~2km of each other (12.8, 14.7, 13.1 km). You can't determine a line's slope (`per_km`) from points clustered at nearly the same x-value — the unrelated vertical scatter in implied base (Rs.386, 274, 132, driven by route-specific and surge-noise factors we don't model) gets misread as a fake downward slope.

**Conclusion:** calibration is currently impossible with the data on hand, and forcing it produces physically-impossible results in one direction or another. This is the calibration code correctly refusing to invent a trustworthy answer from untrustworthy input — better a visibly-absurd number that makes us stop than a plausible-but-wrong one we'd trust. **Left `pricing.py`'s Mini numbers unchanged** — the original guesses are better than a `-4.7` slope from clustered data.

### KNOWN BLOCKED ITEM

- **Mini base-fare calibration is blocked on data**, specifically needs: real **daytime** (5am–10pm) Mini rides across a **spread of distances** (some ~3km, some ~10km, some ~25km — deliberately varied, not clustered). Target ~6–8 such points. This single logging habit unblocks both the calibration AND the model's midday dead-zone at once. `calibrate.py` is correct and ready; it's waiting on better-spread data, same as the model.

### Open items for next session

- [ ] Log daytime Mini rides at deliberately varied distances (unblocks calibration + midday predictions)
- [ ] Build `main.py` — end-to-end live demo (works fine now regardless; uses current model predictions)
- [ ] Re-run `calibrate.py` once ~6–8 distance-varied daytime points exist; update `pricing.py` if sane
- [ ] Retrain model (`python model.py`) periodically as real data grows
- [ ] Weekend data still outstanding

## 2026-09-03 (early hours) — main.py end-to-end, display names, and the self-correction loop working

### main.py — full pipeline, end to end

Built `main.py`, tying every prior block into one runnable program: type pickup + drop → geocode both → Bangalore boundary check → OSRM road distance → load trained model → predict price per vehicle type → display. Almost no new logic; it's the payoff of building tested pieces separately — assembly, not new problem-solving. Only genuinely new bit: predicting for the current moment via `datetime.now()` rather than a typed-in hour.

First live run (KR Puram → Lalbagh, 15.3km, ~2:22am) predicted Auto ₹279 / Mini ₹159 / Sedan ₹245. Real app prices checked immediately after: ₹448 / ₹258 / ₹325 — predictions ~1.3–1.6x low, the now-familiar late-night driver-scarcity gap, surfaced a fourth independent way.

### Display names (decoupled from internal keys)

Wanted to rename Mini→"Non-AC", Sedan→"Premier AC" for users. Rather than rename everywhere (which would touch VEHICLE_TYPES keys, all CSVs, the model's one-hot columns, and orphan existing logged data), used the standard **display-name decoupling** pattern: added a `DISPLAY_NAMES` dict in `pricing.py` mapping internal key → pretty label, and used it ONLY at print/prompt points in `main.py` and `manual_logger.py`. Internal keys (`Mini`/`Sedan`) stay untouched everywhere data is stored or fed to the model. No CSV edits, no retrain needed for the rename. Key discipline: `label` is display-only; `vehicle_type` is what gets written/modelled.

### Logged a strong batch of real data

Logged ~6 real routes with good distance spread (Koramangala→HSR ~5km up to Yelahanka→Electronic City ~36km). Note: all logged live at ~2:30–3:48am (was awake building), so all fall in the 10pm–5am window.

Also noted: Nominatim geocoding failed on some landmark phrasings ("ITPL Main Road, Whitefield", "Whitefield ITPL TTMC") but worked on "Whitefield ITPL,Bangalore" — rephrase-on-failure remains the workaround.

### Calibration still blocked — but for a NEW reason

Re-ran `calibrate.py` hoping the new distance spread would fix the earlier `-4.7` per_km. It didn't — still only 3 points, same result. Diagnosis via direct CSV inspection: all 5 new Mini rows have hours 2.72–3.80 (logged at 3am), so `calibrate.py`'s 10pm–5am filter correctly excludes every one. Irony: logged exactly the distance variety calibration needed, but at the one time of day calibration can't trust the surge estimate. **Calibration now blocked specifically on distance-varied _daytime_ (5am–10pm) rides**, not on distance spread anymore.

### The self-correction loop worked (no hardcoded night constant)

Earlier in the session, decided AGAINST adding a hardcoded ~1.3x night-scarcity multiplier to `pricing.py` — kept it clean, chose to let the model learn night pricing from real data instead. Then retrained (`python model.py`) on the now-larger real dataset (including the 5 new night rides, weighted 5x).

**Results — retrain visibly pulled predictions toward reality:**

- `distance_km` feature importance rose to 42.3% (from 38%), now ~tied with `hour` (42.5%) — the distance-varied night logging directly taught the model distance matters more.
- 03:00 Auto sanity check: ₹138 → ₹165 (night data pulling late predictions up).
- Live re-run of KR Puram → Lalbagh at 4am:

| Vehicle | Before retrain | Real logged | After retrain |
|---|---|---|---|
| Auto | ₹279 | ₹448 | ₹429 |
| Non-AC | ₹159 | ₹258 | **₹263** |
| Premier AC | ₹245 | ₹325 | ₹361 |

Non-AC essentially dead-on. The night-scarcity effect got **learned from real data**, not hand-coded — exactly the clean path chosen earlier. Caveat: this route matched tightly partly because it was itself logged tonight (model has now seen it); unlogged routes won't be this tight yet. But the mechanism is proven: log real data → retrain → predictions improve.

### Still-weak spot (consistent, expected)

13:00 short Mini still predicts ₹35 (implausibly low) — no daytime short-Mini data logged yet, so nothing corrected it. Model improved exactly where given data, stayed weak exactly where not. Correct behaviour.

### Open items

- [ ] Log distance-varied DAYTIME (5am–10pm) rides — unblocks calibration AND the midday dead-zone
- [ ] Re-run calibrate.py once daytime spread exists
- [ ] Continue logging generally; retrain periodically
- [ ] Weekend data still outstanding
- [ ] main.py works but is CLI-only — web dashboard / AWS still ahead

## 2026-09-05 — Automating the manual logger: persistent Uber session + real hub-name pool

### Goal for the session

Replace `manual_logger.py`'s manual "type in the real price" workflow with something that can run unattended every 2-3 hours. Landed on: a persistent Playwright browser session (instead of a static copied cookie) to keep Uber's internal GraphQL API authenticated long-term, plus a real-place hub pool (via OSM's Overpass API) to pick sensible random Bangalore routes instead of raw random coordinates or a fixed watchlist. Full design written up separately (`automatemanuallogger.txt`).

### 1. Why not a static cookie

An existing scraper (outside this repo) hits Uber's internal GraphQL endpoint using a session cookie copied once from devtools — reviewing it surfaced two problems: a bug (`cookies = { cooks, }` referenced an undefined name, so the cookie dict was never actually built) and a live session token sitting in plaintext inside a comment. Beyond the bug, a static cookie is fundamentally fragile on its own terms: it rots in "several days to weeks" with nothing to refresh it, requiring manual re-copying forever — automating around a decaying secret just moves the manual work, it doesn't remove it.

### 2. Persistent browser session (`uber_session.py`)

Built on Playwright's `launch_persistent_context()` — points Chromium at a profile folder (`uber_profile/`) that behaves like a normal saved Chrome profile. Log in once by hand (`login()`, headed/visible), and every future run (`get_fresh_cookies()`, headless) reuses that same saved session, pulling current cookies straight out of the live browser context. Because a real browser periodically loads the real page, Uber's own frontend can refresh short-lived tokens the way it would for a normal user — expected to meaningfully outlast a frozen cookie string, though not a permanent guarantee.

Verified end to end: `login()` opened a real window, logged in manually, saved the session to `uber_profile/`; `get_fresh_cookies()` then returned 49 cookies headlessly with zero login prompt, confirming the persistent session survives a full headless relaunch. `uber_profile/` is treated as a real credential store — gitignored before `login()` was ever run, never printed or logged.

### 3. Real hub-name pool (`blr_hubs.py`)

Random raw coordinates inside the Bangalore bounding box (the same approach `data_generator.py` already uses for synthetic data) risk landing on a lake, a park interior, or a highway median — fine for a formula that doesn't care, bad for a real Uber pickup pin. Instead: query OSM's **Overpass API** (a different service from Nominatim, built for bulk/category queries rather than "look up this one name") for every `place=suburb/neighbourhood/quarter` node inside the existing `bangalore_bounds` (reused from `geocoding.py`, not retyped), and save the resulting names locally (`bangalore_hubs.csv`) so future route-picking forward-geocodes real place names via the existing `geocode()` instead of trusting arbitrary coordinates.

First run returned 1032 names — far more than the ~50–150 expected, since `neighbourhood`/`quarter` tags cover far more small sub-localities than just the well-known named areas.

**Data quality problem found on inspection:** many names were bare, ambiguous layout labels with no place context — `"1st Block"`, `"2nd Phase"`, `"Sector 5"`. Bangalore has many different layouts each with their own numbered blocks/phases, so geocoding one of these alone has no way to know which is meant. Fixed with a regex filter (`is_too_generic()`) that rejects names that are *entirely* a bare numbered label, while keeping names that carry real context (`"12th Block Nagarbhavi"`, `"1st Main Road, Indiranagar"`) — anchored with `^`/`$` specifically so it only rejects a whole-string match, not a partial one. Dropped the pool from 1032 to 1015 names.

Also decided: append `", Bangalore"` to hub names at the point they're actually geocoded later (in `auto_logger.py`, not baked into the CSV) — doesn't guarantee Nominatim picks the exact original OSM node when a name is ambiguous within the city, but reliably keeps the match within Bangalore instead of an unrelated place elsewhere, which is good enough for this project's purposes.

### Bugs hit and fixed today

| Bug | Symptom | Fix |
|---|---|---|
| Missing f-string body in `build_query()` (`query = f` with nothing after it) | `SyntaxError` | Restored the triple-quoted Overpass QL query string |
| `is_too_generic()` written but never called inside `fetch_hub_names()`'s loop | Filter had zero effect — pool count stayed at 1032 after adding the function | Changed `if name:` to `if name and not is_too_generic(name):` |
| Overpass's public server (`overpass-api.de`) returned `HTTP 504` | Request failed, "Fetched 0 named localities" | Retried / switched to a mirror instance (`lz4.overpass-api.de`) — known flakiness of the free shared public server, not a code bug |

### Cybersecurity framing for this work

Treating this automation as a demonstration of secure engineering around authentication, not just working code (full writeup in `automatemanuallogger.txt`): reverse-engineered an internal API via traffic analysis, session lifecycle handled via a persistent browser context instead of a frozen static secret, credential material (`uber_profile/`) never committed or logged, and external responses (Overpass today; Uber/OSRM/Open-Meteo next) treated as untrusted input to validate rather than trust blindly. Calibration note recorded alongside this: evidence of security-conscious engineering, not a substitute for a dedicated security project if that's ever the goal.

### Open items for next session

- [ ] Build `auto_logger.py` — the orchestrator: pick 3 routes (short/medium/long distance bands) from `bangalore_hubs.csv`, get weather (Open-Meteo), get fresh cookies (`uber_session.py`), scrape Uber prices, validate, write to `real_prices.csv`
- [ ] Confirm real Uber tier display names on first live scrape, adjust `UBER_NAME_MAP` if they differ from the Auto/UberGo/Premier guess
- [ ] Set up Windows Task Scheduler once `auto_logger.py` is verified manually (target: every 2-3 hours)
- [ ] Add an OSM/ODbL attribution note somewhere (README or code comment) for the hub-name data, consistent with how other real data sources are already cited in this devlog

## 2026-09-07 (evening) — The forecast feature: the actual payoff of the whole project

### Context

Every prior session built ingredients (geocoding, routing, pricing, data pipeline, trained model). This session built the thing they were all *for*: the price forecast + "should you wait?" recommendation, with honest uncertainty visualization. This is the core value proposition of the project — not "what's the price now" but "here's how it's likely to move, and whether waiting saves money."

### Retrained first (latest real data)

`python model.py` on current `real_prices.csv`:
- **MAE: 73.65** (down from 78 → 73.65 as real data accumulates)
- **Feature importance shifted again:** `distance_km` now TOP feature at 47% (was 38%), overtaking `hour` (38%). The distance-varied logging directly taught the model distance matters more.
- 13:00 short-Mini sanity check: ₹35 → **₹58** (midday dead-zone improving as daytime data comes in, still slightly low)

### Built `forecast.py`

Design decisions (all settled through discussion, tuned by real-world judgment not guessing):
- **Graph horizon: 4 hours ahead + 1 hour of past context** — past shown as "hindcast" so the user can see the trend leading into now, separated by a dashed "now" marker.
- **Wait recommendation horizon: max 60 min** — nobody realistically waits longer for a ride, even if the graph shows more.
- **Prediction granularity: 10-min steps** — decided against 4-min (model inputs barely change over 4 min, so it'd add points without adding information; 10 min captures the hour-scale patterns smoothly).
- **All 3 vehicle types as 3 lines** on one graph.

**The wait logic — scaled savings rule (`SAVINGS_RATE`):** a wait is only recommended if `savings > SAVINGS_RATE * wait_minutes`. This captures "short waits need only small savings, long waits need big savings" in one line. Tuned from 3.0 → 1.0 → **1.7** Rs/min by feel for Bangalore (explicitly a subjective preference knob, NOT a sourced number — commented as such). Among all qualifying waits, picks the one with the highest margin (`savings - rate*wait`).

Core new concept vs. everything before: `build_forecast` loops the existing `predict_price()` across future (and past) time steps — same model, just asked about other times instead of now. Everything else is orchestration of already-built, already-tested functions.

### Data-confidence shading — turning a limitation into a feature

Looked at the first forecast graph and immediately saw the problem: jagged spikes + dead-flat plateaus = **not enough data**, model lurching where real points are sparse and falling back to flat averages where it has none. This is a data problem, not a code problem — `forecast.py` was faithfully drawing what the model believes; the model just doesn't believe much yet.

Rather than hide this, made it visible: **red shading marks time regions where real training data is sparse (low confidence).**

Key debugging moment: first version measured density from the *combined* (synthetic + real) training set — every hour showed 14-72 nearby rows, so nothing got flagged. But that coverage is synthetic (the generator fills all 24 hours evenly by construction); it says nothing about real grounding. **Fixed to measure density from `real_prices.csv` ONLY** — the honest signal for "is the model grounded in real observations or just echoing the synthetic formula here." Real counts are small and clustered:
```
[0,0,0,0,0,0,0,0, 5,5,7,7,7,7, 2,2, 0,0,0,0,0, 3,3,3,3,3,3, 6,12,12]
```
Zeros everywhere except the handful of time windows with logged rides. `SPARSE_THRESHOLD` dropped to 2 accordingly. Result: graph shades red everywhere real coverage is thin (currently most of it), clear only at well-logged windows — an honest map of "where the model is guessing" that doubles as a map of "where I still need to log rides." It shrinks visibly on each retrain as data grows.

### Why this matters (portfolio angle)

Anyone can plot a prediction line. Showing *calibrated uncertainty* — honestly marking where the model is confident vs. guessing — demonstrates understanding of a model's limits, not just how to run scikit-learn. The most valuable moment of the session was reading the raw graph and correctly diagnosing "not enough data" rather than assuming a code bug — that upstream-vs-code instinct is the real ML skill.

### Where the project stands

**Complete core project works end to end:** geocode → boundary check → OSRM routing → trained model → multi-hour forecast → scaled wait recommendation → uncertainty-shaded graph. Blocks 1 through the payoff feature, done.

### Bugs hit

| Bug | Symptom | Fix |
|---|---|---|
| `matplotlib` not installed in `.venv` | ModuleNotFoundError | `pip install matplotlib` inside active venv |
| `build_forecast` missing `now` parameter on disk | `NameError: name 'now' is not defined` | Added `now` to the function signature |
| Confidence density measured synthetic+real combined | No shading appeared (all hours looked well-covered) | Measure density from `real_prices.csv` only |

### Open items

- [ ] Keep logging real rides across varied times/distances → curves smooth + red bands shrink on retrain
- [ ] Consider tuning SAVINGS_RATE once seen against more real routes
- [ ] SHAP model explainability (`explain_model.py`) — planned, not yet built
- [ ] Web dashboard / AWS deployment — the remaining expansion work (CLI-only for now)
- [ ] Weekend data still thin