import { useCallback, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'

import Aurora from './components/Aurora'
import ForecastChart from './ForecastChart'
import Intro from './components/Intro'
import SearchPanel from './components/SearchPanel'
import VehicleCard from './components/VehicleCard'
import { EmptyState, ErrorState, ResultsSkeleton } from './components/States'
import { fetchPrediction } from './api'

export default function App() {
  const reduceMotion = useReducedMotion()

  /* Anyone who has asked their OS to reduce motion skips the intro entirely.
     The initialiser form of useState (a function, not a value) means this is
     evaluated once on mount rather than on every render. */
  const [introDone, setIntroDone] = useState(() => Boolean(reduceMotion))

  const [pickup, setPickup] = useState('')
  const [drop, setDrop] = useState('')

  /* One `status` string instead of separate `loading` / `results` / `error`
     flags. Three booleans can describe eight states, five of which are
     nonsense ("loading AND errored AND has results"). A single status value
     can only ever hold one of the four states that actually exist. */
  const [status, setStatus] = useState('idle') // idle | loading | success | error
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  // Tracks the in-flight request so a second search can cancel the first.
  const abortRef = useRef(null)

  const runSearch = useCallback(async (from, to) => {
    // Cancel whatever is still in the air. Without this, a slow first request
    // can resolve *after* a fast second one and overwrite the newer results.
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setStatus('loading')
    setError(null)

    try {
      const payload = await fetchPrediction({ pickup: from, drop: to, signal: controller.signal })

      // FastAPI answers 200 with an `error` key for a bad route, so a
      // successful HTTP response is not automatically a successful search.
      if (payload.error) {
        setError({ message: payload.error, isNetwork: false })
        setStatus('error')
        return
      }

      setData(payload)
      setStatus('success')
    } catch (err) {
      // An abort is us cancelling on purpose; it is not a failure to report.
      if (err.name === 'AbortError') return

      // A tagged `status` means the server answered, just badly (500, 404).
      // An untagged error means the request never completed at all — server
      // down, DNS, or CORS. Different causes, so different advice.
      setError(
        err.status
          ? { message: `The forecast service returned an error (${err.status}).`, isNetwork: false }
          : { message: 'Could not reach the forecast service.', isNetwork: true },
      )
      setStatus('error')
    }
  }, [])

  const handleSubmit = useCallback(() => {
    runSearch(pickup.trim(), drop.trim())
  }, [pickup, drop, runSearch])

  const handlePickRoute = useCallback((route) => {
    setPickup(route.pickup)
    setDrop(route.drop)
    runSearch(route.pickup, route.drop)
  }, [runSearch])

  // The cheapest ride right now, used to badge one card. Computed rather than
  // assumed, because which vehicle is cheapest changes with distance and hour.
  const cheapest = data?.results?.reduce(
    (best, r) => (best === null || r.current_price < best ? r.current_price : best),
    null,
  )

  return (
    <>
      <Aurora />

      {/* AnimatePresence keeps a component mounted long enough to play its
          `exit` animation. Without it, setIntroDone(true) would rip the splash
          off the screen in a single frame. */}
      <AnimatePresence>
        {!introDone && <Intro key="intro" onDone={() => setIntroDone(true)} />}
      </AnimatePresence>

      {/* The app is rendered and painted underneath the intro the whole time,
          so dismissing the splash reveals a finished page instead of starting
          to build one. */}
      <div className="relative mx-auto min-h-screen w-full max-w-5xl px-4 py-14 sm:px-6 sm:py-20">
        <Header reduceMotion={reduceMotion} />

        <SearchPanel
          pickup={pickup}
          drop={drop}
          onPickupChange={setPickup}
          onDropChange={setDrop}
          onSubmit={handleSubmit}
          onPickRoute={handlePickRoute}
          loading={status === 'loading'}
        />

        {/* `mode="wait"` makes the outgoing state finish leaving before the
            incoming one starts, so the two never overlap mid-crossfade. */}
        <section className="mt-10">
          <AnimatePresence mode="wait">
            {status === 'idle' && <EmptyState key="empty" />}

            {status === 'loading' && <ResultsSkeleton key="loading" />}

            {status === 'error' && (
              <ErrorState
                key="error"
                message={error.message}
                isNetwork={error.isNetwork}
                onRetry={handleSubmit}
              />
            )}

            {status === 'success' && data && (
              <motion.div
                /* Keying on the route means a *new* search replays the whole
                   entrance animation instead of silently swapping numbers. */
                key={`${data.pickup}-${data.drop}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.35 }}
              >
                <RouteSummary data={data} />

                <div className="mb-4 grid gap-4 sm:grid-cols-3">
                  {data.results.map((result, i) => (
                    <VehicleCard
                      key={result.vehicle}
                      result={result}
                      index={i}
                      isCheapest={result.current_price === cheapest}
                    />
                  ))}
                </div>

                <motion.div
                  initial={{ opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  className="glass rounded-2xl p-5"
                >
                  <ForecastChart results={data.results} />
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        <footer className="mt-16 border-t border-hairline pt-6 text-center text-xs text-ink-mute">
          <p>
            Forecasts come from a gradient-boosted model trained on logged Bangalore
            fares. Estimates, not quotes.
          </p>
        </footer>
      </div>
    </>
  )
}

function Header({ reduceMotion }) {
  return (
    <motion.header
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      className="mb-10 text-center"
    >
      <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-hairline
                      bg-white/4 px-3 py-1 text-[11px] tracking-wide text-ink-soft">
        {/* The live dot: a solid core with a ring expanding out of it. Two
            elements, one CSS animation, and it makes a static badge feel awake. */}
        <span className="relative flex h-1.5 w-1.5">
          {!reduceMotion && (
            <span className="absolute inline-flex h-full w-full animate-pulse-ring
                             rounded-full bg-series-3" />
          )}
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-series-3" />
        </span>
        Live surge model · Bangalore
      </div>

      <h1 className="mb-3 font-display text-4xl font-bold tracking-tight text-balance sm:text-6xl">
        <span className="text-gradient">Know before you book.</span>
      </h1>

      <p className="mx-auto max-w-xl text-base leading-relaxed text-ink-soft text-pretty sm:text-lg">
        Live fare predictions for every ride type in Bangalore, four hours ahead —
        so you can tell a real surge from five minutes of bad luck.
      </p>
    </motion.header>
  )
}

function RouteSummary({ data }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      className="mb-5 flex flex-wrap items-center justify-center gap-x-3 gap-y-1
                 text-sm text-ink-soft"
    >
      <span className="font-medium text-ink">{data.pickup}</span>
      <svg viewBox="0 0 24 8" className="h-2 w-6 text-ink-mute" fill="none"
           stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
        <path d="M0 4h21M18 1l3 3-3 3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className="font-medium text-ink">{data.drop}</span>
      <span className="text-ink-mute">·</span>
      <span className="tabular-nums text-ink-mute">{data.distance_km} km by road</span>
    </motion.div>
  )
}
