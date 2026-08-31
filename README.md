# commute-intelligence-radar
## Data Sources & Design Decisions

The pricing simulation (`pricing.py`) isn't guesswork dressed up as realism — every constant is either sourced from real, public data, or explicitly flagged as an unverified assumption. No numbers came from Uber's own systems; all of this is publicly available third-party data.

### Sourced from real data

- **Evening peak is 1.27x stronger than morning peak.** Based on TomTom's 2023 Traffic Index for Bengaluru specifically: a 10km trip in the city center takes an extra 15 minutes during morning rush hour vs. an extra 19 minutes during evening rush hour (19/15 ≈ 1.27). [Source: Deccan Herald](https://www.deccanherald.com/amp/story/india%2Fkarnataka%2Fbengaluru%2Fbengaluru-remains-most-congested-in-india-drops-to-sixth-globally-dutch-index-2878811)

- **Surge is bounded between 0.5x and 2.0x of base fare.** Per India's 2025 Motor Vehicle Aggregator Guidelines (Ministry of Road Transport and Highways), cab aggregators can charge at most 2x base fare during peak hours, and fares must be at least 0.5x base fare off-peak. [Source: Business Standard](https://www.business-standard.com/india-news/cab-aggregators-surge-pricing-rapido-uber-ola-125070200228_1.html). Karnataka had already independently set a matching state-level cap (2x for standard cars, 2.25x for luxury) prior to the national rule.

- **Fridays 6-7pm are the single worst recurring traffic window in Bengaluru**, per the same TomTom/Deccan Herald data — worse than any other weekday evening.

### Modeled assumptions (not directly sourced)

- **Peak center times (9:00am, 7:30pm)** and **peak width/spread parameters** are reasonable estimates based on typical Indian office-commute hours, not from a specific dataset.
- **The magnitude of the Friday-evening bump** — the *existence* of Friday being worst is sourced (above), but the specific multiplier applied to model that effect is an unverified placeholder, pending calibration against real logged data.

### Plan to improve accuracy over time

The manual logging process (`manual_logger.py`) exists specifically to validate and eventually recalibrate these modeled assumptions against real observed prices, rather than leaving them as permanent guesses.

### Vehicle types

- **Auto** pricing is anchored to a real reported app fare (~Rs.33.5/km during evening rush, per Deccan Herald reporting on an actual MG Road–Indiranagar ride) — deliberately *not* the government-regulated meter rate. Reporting confirms a documented, litigated gap between the two: the Karnataka High Court ruled aggregators can't charge more than 5% above the stipulated meter fare, but "aggregators do not follow the fare notification," per an independent mobility expert quoted in the same coverage. Using the meter rate here would have been citing a real number that doesn't represent what the app actually charges.
- Auto also carries a real, DTA-mandated **1.5x night surcharge (10pm–5am)**, per the same August 2025 fare notification.
- **Mini and Sedan** base fares are modeled estimates — Ola/Uber cab fares aren't publicly regulated in Karnataka (the state's taxi-fare notification explicitly excludes them), so there's no legitimate public source to anchor them to.

### Distance methodology

Distance was initially approximated with a flat "circuity factor" (a multiplier converting straight-line distance to estimated road distance). This was replaced before shipping, because a single constant can't distinguish a nearly-direct route (e.g. Kogilu–Esteem Mall) from a highly indirect one (e.g. Bellandur–Kempegowda Airport, where road distance runs ~1.8x straight-line distance due to a single practical highway corridor). 

Distance is now computed via **OSRM** (Open Source Routing Machine, router.project-osrm.org's public demo server) — real road-network routing per specific pair of points, not an approximation. This is the same category of free, no-key, no-card public service as the Nominatim geocoder already in use, subject to the same 1 req/sec fair-use limit.

### What this tool is not

- **Not a live Uber price feed.** Every number shown is a statistical estimate, not a real-time quote.
- **Not aware of real driver availability.** There's no legitimate way to access live driver-supply data, so this tool never claims to know whether a ride is actually bookable right now.
- Prices are labeled "Estimate" throughout the interface for this reason.