import { useState } from 'react'

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
    <div>
      <h1>Commute Intelligence Radar</h1>
      <p>Predict Bangalore ride prices and know when to book.</p>

      <div>
        <input
          type="text"
          placeholder="Pickup location"
          value={pickup}
          onChange={(e) => setPickup(e.target.value)}
        />
        <input
          type="text"
          placeholder="Drop location"
          value={drop}
          onChange={(e) => setDrop(e.target.value)}
        />
        <button onClick={getPrices}>Get Prices</button>
      </div>

      {loading && <p>Loading...</p>}

      {results && results.error && <p>{results.error}</p>}

      {results && results.results && (
        <div>
          <p>{results.pickup} → {results.drop} ({results.distance_km} km)</p>
          {results.results.map((r) => (
            <div key={r.vehicle}>
              <h3>{r.vehicle}: ₹{r.current_price}</h3>
              <p>{r.recommendation}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default App