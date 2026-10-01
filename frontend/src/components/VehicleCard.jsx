import { motion } from 'framer-motion'
import AnimatedNumber from './AnimatedNumber'
import { SERIES_COLORS } from '../api'

/**
 * The backend hands us the recommendation as one prose string, e.g.
 *   "Wait 30 min (until 20:10) for ~Rs.220, save Rs.45"
 *   "Book now"
 * Prose is fine for a terminal; a UI wants the pieces separately so it can
 * style the savings differently from the wait time. We parse it here and fall
 * back to showing the raw string verbatim if the shape ever changes — a
 * regex that stops matching should degrade, never blank the card.
 */
const WAIT_PATTERN = /^Wait (\d+) min \(until (\d{1,2}:\d{2})\) for ~Rs\.(\d+), save Rs\.(\d+)/

function parseRecommendation(text) {
  const match = WAIT_PATTERN.exec(text ?? '')
  if (!match) {
    return { kind: text === 'Book now' ? 'now' : 'raw', text }
  }
  const [, minutes, until, price, savings] = match
  return { kind: 'wait', minutes: +minutes, until, price: +price, savings: +savings }
}

export default function VehicleCard({ result, index, isCheapest }) {
  const rec = parseRecommendation(result.recommendation)
  const color = SERIES_COLORS[result.vehicle] ?? 'var(--color-accent)'

  return (
    <motion.article
      /* Each card enters slightly after the one before it. The stagger is what
         makes three cards read as one gesture instead of three pop-ins. */
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, delay: index * 0.09, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -6 }}
      className="group glass relative overflow-hidden rounded-2xl p-5"
    >
      {/* A wash of the series colour that only appears on hover. `transition`
          here is CSS, not framer — cheap, and it never fights the JS animation
          running on the parent's transform. */}
      <div
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity
                   duration-300 group-hover:opacity-100"
        style={{ background: `radial-gradient(120% 90% at 50% 0%, ${color}22, transparent 70%)` }}
      />

      {/* Top edge, lit in the series colour — the visual link between this card
          and its line in the chart below. */}
      <div
        className="absolute inset-x-0 top-0 h-px opacity-70"
        style={{ background: `linear-gradient(90deg, transparent, ${color}, transparent)` }}
      />

      <div className="relative">
        <header className="mb-3 flex items-center gap-2">
          {/* The identity dot. Same colour as this vehicle's line in the graph,
              so the reader never has to match by memory. */}
          <span
            className="h-2.5 w-2.5 shrink-0 rounded-full"
            style={{ backgroundColor: color, boxShadow: `0 0 10px ${color}99` }}
          />
          <h3 className="text-sm font-medium text-ink-soft">{result.vehicle}</h3>

          {isCheapest && (
            <span className="ml-auto rounded-full border border-good/30 bg-good/10
                             px-2 py-0.5 text-[10px] font-semibold tracking-wide
                             text-good uppercase">
              Cheapest
            </span>
          )}
        </header>

        <p className="mb-4 font-display text-3xl font-semibold text-ink">
          <AnimatedNumber value={result.current_price} prefix="₹" />
        </p>

        {rec.kind === 'wait' ? (
          <div className="space-y-1.5">
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-warn/25
                             bg-warn/10 px-2.5 py-1 text-xs font-medium text-warn">
              {/* Icon + label, never colour alone — status has to survive being
                  read in greyscale or by someone who is colourblind. */}
              <ClockIcon />
              Wait {rec.minutes} min
            </span>
            <p className="text-xs leading-relaxed text-ink-mute">
              Book at <span className="text-ink-soft">{rec.until}</span> for about{' '}
              <span className="text-ink-soft">₹{rec.price}</span> — saves{' '}
              <span className="font-medium text-good">₹{rec.savings}</span>
            </p>
          </div>
        ) : rec.kind === 'now' ? (
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-good/25
                           bg-good/10 px-2.5 py-1 text-xs font-medium text-good">
            <BoltIcon />
            Book now
          </span>
        ) : (
          <p className="text-xs leading-relaxed text-ink-mute">{rec.text}</p>
        )}
      </div>
    </motion.article>
  )
}

/* Inline SVG rather than an icon library: two icons do not justify a
   dependency, and inline paths cost nothing at runtime. `currentColor` makes
   them inherit the text colour of whatever badge they sit in. */
function ClockIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none"
         stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">
      <circle cx="8" cy="8" r="6.2" />
      <path d="M8 4.6V8l2.3 1.6" />
    </svg>
  )
}

function BoltIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="currentColor" aria-hidden="true">
      <path d="M8.9 1.2 3.6 8.6a.5.5 0 0 0 .4.8h2.7l-.8 5.3a.4.4 0 0 0 .75.28l5.3-7.4a.5.5 0 0 0-.4-.79H9.15l.5-4.9a.4.4 0 0 0-.75-.27Z" />
    </svg>
  )
}
