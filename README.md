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