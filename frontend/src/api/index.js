/* ---------------------------------------------------------------------------
   Where the backend lives.

   `import.meta.env` is Vite's build-time environment. Any variable prefixed
   with VITE_ is read from a .env file and *inlined into the bundle as a string
   literal* when you run `npm run build`. It is not read at runtime, so:
     - you must rebuild after changing it, and
     - it is public. Never put a secret in a VITE_ variable.

   The `??` fallback keeps `npm run dev` working with zero setup while making
   the deployed build point at the real API. See .env.example.
--------------------------------------------------------------------------- */
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/** Vehicle display name -> the CSS variable holding its series colour.
 *  Colour follows the entity, never its position in the response array, so
 *  "Auto" is blue in the cards, in the legend and in the chart — always. */
export const SERIES_COLORS = {
  Auto: 'var(--color-series-1)',
  'Non-AC': 'var(--color-series-2)',
  'Premier AC': 'var(--color-series-3)',
}

/** Same map, resolved to hex. Recharts writes `stroke` into an SVG attribute
 *  where a `var(...)` reference does not resolve, so it needs real values. */
export const SERIES_HEX = {
  Auto: '#3987e5',
  'Non-AC': '#d95926',
  'Premier AC': '#199e70',
}

/** One-click sample routes.
 *
 *  Every endpoint here is one the backend has *already* geocoded to a point
 *  inside the Bangalore bounding box — they appear in watched_routes.csv. That
 *  matters because geocoding.py sends the bare place name to Nominatim with no
 *  city qualifier, so an unqualified name can resolve to the wrong country and
 *  come back as "This tool only works for routes inside Bangalore." Demo
 *  buttons are the last place you want to find that out. */
export const SAMPLE_ROUTES = [
  { pickup: 'Koramangala', drop: 'Indiranagar', label: 'Koramangala → Indiranagar' },
  { pickup: 'Yelahanka', drop: 'Bellandur', label: 'Yelahanka → Bellandur' },
  { pickup: 'Koramangala', drop: 'Bellandur', label: 'Koramangala → Bellandur' },
  {
    pickup: 'Indiranagar',
    drop: 'Kempegowda International Airport',
    label: 'Indiranagar → Airport',
  },
]

/** Autocomplete suggestions for the two inputs, taken verbatim from
 *  bangalore_hubs.csv so the spelling matches what the hub list uses. */
export const HUB_SUGGESTIONS = [
  'BTM Layout', 'Banashankari', 'Banaswadi', 'Basavanagudi', 'Bellandur',
  'Bommanahalli', 'Cox Town', 'Domlur', 'Frazer Town', 'Girinagar',
  'HSR Layout', 'Hebbal', 'Hennur', 'Hoodi', 'Indiranagar', 'JP Nagar',
  'Jalahalli', 'Jayanagar', 'KR Puram', 'Kalyan Nagar', 'Kammanahalli',
  'Kempegowda International Airport', 'Kengeri', 'Koramangala', 'Marathahalli',
  'Peenya', 'RT Nagar', 'Rajajinagar', 'Shivajinagar', 'Varthur', 'Whitefield',
  'Wilson Garden', 'Yelahanka',
]

/**
 * Ask the backend to price a route.
 *
 * Throws on transport failure (backend down, CORS blocked, DNS) so the caller
 * can tell "the network broke" apart from "the server answered, and the answer
 * was an error object" — two states that deserve different messages.
 */
export async function fetchPrediction({ pickup, drop, signal }) {
  const response = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pickup, drop }),
    signal,
  })

  if (!response.ok) {
    // Tag it so the caller can tell "the server answered badly" apart from
    // "we never reached the server" — those need different advice.
    const error = new Error(`Server responded ${response.status}`)
    error.status = response.status
    throw error
  }
  return response.json()
}
