import { motion } from 'framer-motion'
import { HUB_SUGGESTIONS, SAMPLE_ROUTES } from '../api'

/**
 * Pickup, drop, and go.
 *
 * This is a real <form>, not two inputs beside a <div onClick>. That one
 * choice buys three things for free:
 *   - Enter submits, from either field
 *   - mobile keyboards show a "Go" key instead of a newline key
 *   - browsers offer to remember and refill the route
 * Wiring all of that onto a div by hand is work you do not need to do.
 */
export default function SearchPanel({
  pickup, drop, onPickupChange, onDropChange, onSubmit, onPickRoute, loading,
}) {
  // Firing a request with an empty field just round-trips to an error message.
  // Better to make the button visibly unavailable until it can succeed.
  const canSubmit = pickup.trim() && drop.trim() && !loading

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault() // stop the browser's full-page reload
          if (canSubmit) onSubmit()
        }}
        className="glass rounded-2xl p-2 shadow-2xl shadow-black/40"
      >
        <div className="flex flex-col gap-2 sm:flex-row">
          <Field
            id="pickup"
            label="Pickup"
            placeholder="Koramangala"
            value={pickup}
            onChange={onPickupChange}
            icon={<DotIcon />}
          />

          {/* Divider, desktop only. A hairline between fields reads as one
              control; on mobile the fields stack, where it would look wrong. */}
          <div className="hidden w-px shrink-0 self-stretch bg-hairline sm:block" />

          <Field
            id="drop"
            label="Drop"
            placeholder="Indiranagar"
            value={drop}
            onChange={onDropChange}
            icon={<PinIcon />}
          />

          <button
            type="submit"
            disabled={!canSubmit}
            className="group relative shrink-0 overflow-hidden rounded-xl bg-accent
                       px-6 py-3.5 font-medium text-white transition-all duration-200
                       hover:bg-accent-soft hover:shadow-lg hover:shadow-accent/30
                       active:scale-[0.98]
                       disabled:cursor-not-allowed disabled:bg-white/8
                       disabled:text-ink-mute disabled:shadow-none"
          >
            <span className="flex items-center justify-center gap-2">
              {loading ? (
                <>
                  <Spinner />
                  Scanning
                </>
              ) : (
                <>
                  Get prices
                  <ArrowIcon />
                </>
              )}
            </span>
          </button>
        </div>
      </form>

      {/* Sample routes. A blank pair of text boxes is a quiz: the visitor has
          to guess both what this does and which place names it accepts. One
          click on a chip answers both. Every name here is one the backend has
          successfully geocoded before. */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-xs text-ink-mute">Try:</span>
        {SAMPLE_ROUTES.map((route, i) => (
          <motion.button
            key={route.label}
            type="button"
            onClick={() => onPickRoute(route)}
            disabled={loading}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.35 + i * 0.06 }}
            whileTap={{ scale: 0.96 }}
            className="rounded-full border border-hairline bg-white/4 px-3 py-1.5
                       text-xs text-ink-soft transition-colors
                       hover:border-accent/40 hover:bg-accent/10 hover:text-ink
                       disabled:opacity-40"
          >
            {route.label}
          </motion.button>
        ))}
      </div>

      {/* One shared <datalist> for both inputs: the browser renders it as a
          native autocomplete dropdown, keyboard-accessible, zero JS. */}
      <datalist id="blr-hubs">
        {HUB_SUGGESTIONS.map((hub) => (
          <option key={hub} value={hub} />
        ))}
      </datalist>
    </motion.div>
  )
}

function Field({ id, label, placeholder, value, onChange, icon }) {
  return (
    <div className="relative flex-1">
      {/* A real <label>, visually hidden. Sighted users get the placeholder;
          screen readers get a name that does not vanish once you start typing
          (which is exactly what a placeholder-as-label does). */}
      <label htmlFor={id} className="sr-only">{label}</label>
      <span className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-ink-mute">
        {icon}
      </span>
      <input
        id={id}
        name={id}
        list="blr-hubs"
        autoComplete="off"
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl bg-transparent py-3.5 pr-4 pl-10 text-ink
                   placeholder:text-ink-mute focus:outline-none"
      />
    </div>
  )
}

function DotIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor"
         strokeWidth="1.6" aria-hidden="true">
      <circle cx="8" cy="8" r="3.2" />
      <circle cx="8" cy="8" r="6.6" strokeOpacity=".4" />
    </svg>
  )
}

function PinIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor"
         strokeWidth="1.6" strokeLinejoin="round" aria-hidden="true">
      <path d="M8 14.5s5-4.2 5-8a5 5 0 0 0-10 0c0 3.8 5 8 5 8Z" />
      <circle cx="8" cy="6.4" r="1.9" />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4 transition-transform duration-200
                                        group-hover:translate-x-0.5"
         fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
         strokeLinejoin="round" aria-hidden="true">
      <path d="M3 8h10M9 4l4 4-4 4" />
    </svg>
  )
}

function Spinner() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4 animate-spin" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="6.2" stroke="currentColor" strokeOpacity=".25" strokeWidth="2" />
      <path d="M14.2 8A6.2 6.2 0 0 0 8 1.8" stroke="currentColor" strokeWidth="2"
            strokeLinecap="round" />
    </svg>
  )
}
