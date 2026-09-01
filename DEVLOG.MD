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