import { motion } from 'framer-motion'

/**
 * What fills the results area before the first search.
 *
 * Without this the page is a search bar floating above a tall empty void,
 * which reads as broken rather than as ready. An empty state is not decoration
 * — it is the answer to "what is this and what do I get".
 */
export function EmptyState() {
  const points = [
    { title: 'Three vehicle types', body: 'Auto, Non-AC and Premier AC priced side by side.' },
    { title: 'Four hours ahead', body: 'A surge forecast, not just the fare right now.' },
    { title: 'Book or wait', body: 'A call on whether waiting actually saves you money.' },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.5 }}
      className="grid gap-3 sm:grid-cols-3"
    >
      {points.map((point, i) => (
        <motion.div
          key={point.title}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.55 + i * 0.08 }}
          className="rounded-2xl border border-dashed border-hairline p-5"
        >
          <p className="mb-1 text-sm font-medium text-ink-soft">{point.title}</p>
          <p className="text-xs leading-relaxed text-ink-mute">{point.body}</p>
        </motion.div>
      ))}
    </motion.div>
  )
}

/**
 * The loading state.
 *
 * A skeleton rather than a spinner, because this request is slow and variable
 * — it geocodes two place names against a public API, asks OSRM for a route,
 * then runs 31 model predictions per vehicle. A skeleton that matches the
 * shape of the incoming layout makes the wait feel shorter and stops the page
 * from jumping when the real content lands.
 */
export function ResultsSkeleton() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      // Announced politely, so a screen reader says "loading prices" without
      // interrupting whatever it is currently reading.
      role="status"
      aria-live="polite"
    >
      <span className="sr-only">Loading prices…</span>

      <div className="mb-4 grid gap-4 sm:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="glass rounded-2xl p-5">
            <Bar className="mb-3 h-3 w-20" delay={i * 0.12} />
            <Bar className="mb-4 h-7 w-28" delay={i * 0.12 + 0.05} />
            <Bar className="h-5 w-24 rounded-lg" delay={i * 0.12 + 0.1} />
          </div>
        ))}
      </div>

      <div className="glass rounded-2xl p-5">
        <Bar className="mb-5 h-3 w-36" />
        <Bar className="h-[220px] w-full rounded-xl" delay={0.15} />
      </div>
    </motion.div>
  )
}

/* The shimmer is a CSS opacity pulse, not a sliding gradient. Same effect,
   and it does not repaint a large gradient on every frame. */
function Bar({ className = '', delay = 0 }) {
  return (
    <div
      className={`animate-shimmer rounded bg-white/8 ${className}`}
      style={{ animationDelay: `${delay}s` }}
    />
  )
}

/** Something went wrong. Distinguishes "the server said no" from "we could not
 *  reach the server at all", because the fix is different for each. */
export function ErrorState({ message, isNetwork, onRetry }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      role="alert"
      className="rounded-2xl border border-red-500/25 bg-red-500/8 p-5 text-center"
    >
      <p className="mb-1 text-sm font-medium text-red-300">{message}</p>
      {isNetwork && (
        <p className="mx-auto max-w-md text-xs leading-relaxed text-ink-mute">
          The request never got an answer. Either the backend is down, or it is
          up but refusing this page's origin — a CORS block looks identical to
          an outage from in here, because the browser withholds the response
          either way. Running locally, check the backend is on port 8000 and
          that this page's port is in its allowed origins.
        </p>
      )}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-lg border border-hairline px-3 py-1.5 text-xs
                     text-ink-soft transition-colors hover:bg-white/5 hover:text-ink"
        >
          Try again
        </button>
      )}
    </motion.div>
  )
}
