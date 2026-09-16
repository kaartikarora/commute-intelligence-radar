import { useState } from 'react'
import ForecastChart from './ForecastChart'

function App() {
  const [pickup, setPickup] = useState('')
  const [drop, setDrop] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)

  async function getPrices() {
    setLoading(true)
    setResults(null)
    try {
      const response = await fetch('http://localhost:8000/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pickup, drop }),
      })
      const data = await response.json()
      setResults(data)
    } catch (err) {
      setResults({ error: 'Something went wrong. Is the backend running?' })
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="max-w-2xl mx-auto px-6 py-20">

        {/* Hero */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight mb-3">
            Commute Intelligence Radar
          </h1>
          <p className="text-slate-400 text-lg">
            Predict Bangalore ride prices, and know when to wait.
          </p>
        </div>

        {/* Search bar */}
        <div className="flex flex-col sm:flex-row gap-3 mb-10">
          <input
            type="text"
            placeholder="Pickup location"
            value={pickup}
            onChange={(e) => setPickup(e.target.value)}
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3
                       placeholder:text-slate-500 focus:outline-none focus:border-indigo-400
                       transition-colors"
          />
          <input
            type="text"
            placeholder="Drop location"
            value={drop}
            onChange={(e) => setDrop(e.target.value)}
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3
                       placeholder:text-slate-500 focus:outline-none focus:border-indigo-400
                       transition-colors"
          />
          <button
            onClick={getPrices}
            className="bg-indigo-500 hover:bg-indigo-400 transition-colors
                       rounded-xl px-6 py-3 font-medium"
          >
            Get Prices
          </button>
        </div>

        {/* Loading */}
        {loading && (
          <p className="text-center text-slate-400">Checking current prices…</p>
        )}

        {/* Error */}
        {results && results.error && (
          <p className="text-center text-red-400">{results.error}</p>
        )}

        {/* Results */}
        {results && results.results && (
          <div>
            <p className="text-slate-400 text-sm mb-6 text-center">
              {results.pickup} → {results.drop} &middot; {results.distance_km} km
            </p>

            <div className="grid sm:grid-cols-3 gap-4 mb-10">
              {results.results.map((r) => (
                <div
                  key={r.vehicle}
                  className="bg-white/5 border border-white/10 rounded-2xl p-5 shadow-xl"
                >
                  <p className="text-slate-400 text-sm mb-1">{r.vehicle}</p>
                  <p className="text-2xl font-semibold mb-3">₹{r.current_price}</p>
                  <p className="text-sm text-indigo-300">{r.recommendation}</p>
                </div>
              ))}
            </div>

            <div className="bg-white/5 border border-white/10 rounded-2xl p-5 shadow-xl">
              <ForecastChart results={results.results} />
            </div>
          </div>
        )}

      </div>
    </div>
  )
}

export default App