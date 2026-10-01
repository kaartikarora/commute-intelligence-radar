import { useEffect } from 'react'
import { motion } from 'framer-motion'

const TITLE = 'Commute Intelligence Radar'

/**
 * The opening animation.
 *
 * Three rules this follows, because intros are the easiest thing in a UI to
 * get wrong:
 *
 *  1. It is an OVERLAY, not a gate. The real app is already mounted and
 *     painted underneath. Dismissing it is a fade, not a mount — so the first
 *     frame of the app is never delayed by the animation.
 *  2. It is SKIPPABLE. Click, tap, scroll or any key kills it instantly.
 *     An intro you cannot escape stops being delightful on the second visit.
 *  3. It is SHORT. ~1.4s to fully drawn. Past about two seconds an intro is
 *     no longer an intro, it is a loading screen.
 *
 * Timing is driven by framer's `onAnimationComplete`, deliberately NOT by a
 * setTimeout inside useEffect: React's StrictMode double-invokes effects in
 * development, which would start two timers and produce a visible flicker.
 */
export default function Intro({ onDone }) {
  // Any interaction skips straight to the app.
  useEffect(() => {
    const skip = () => onDone()
    window.addEventListener('pointerdown', skip)
    window.addEventListener('keydown', skip)
    window.addEventListener('wheel', skip, { passive: true })
    window.addEventListener('touchstart', skip, { passive: true })
    return () => {
      window.removeEventListener('pointerdown', skip)
      window.removeEventListener('keydown', skip)
      window.removeEventListener('wheel', skip)
      window.removeEventListener('touchstart', skip)
    }
  }, [onDone])

  return (
    <motion.div
      // `exit` is what AnimatePresence in App.jsx plays on the way out. The
      // slight scale-up makes the overlay feel like it lifts off the page
      // rather than just dissolving.
      initial={{ opacity: 1 }}
      /* opacity + scale only. Blurring a full-viewport layer every frame is
         exactly the thing the perf rules warn about, and the lift-off reads
         fine without it. */
      exit={{ opacity: 0, scale: 1.06 }}
      transition={{ duration: 0.65, ease: [0.4, 0, 0.2, 1] }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center
                 gap-8 bg-void px-6"
    >
      {/* --- the radar --------------------------------------------------- */}
      <motion.div
        initial={{ scale: 0.6, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="relative h-28 w-28"
      >
        {/* Two static rings + an expanding ping = the radar dish. */}
        <div className="absolute inset-0 rounded-full border border-accent/40" />
        <div className="absolute inset-[22%] rounded-full border border-accent/25" />
        <div className="absolute inset-0 animate-pulse-ring rounded-full border border-accent/50" />

        {/* The sweep. A conic-gradient wedge spun by a CSS rotate — one
            element, no JS, and it stays on the compositor. */}
        <div
          className="absolute inset-0 animate-sweep rounded-full"
          style={{
            background:
              'conic-gradient(from 0deg, rgba(139,92,246,0.55) 0deg, rgba(94,234,212,0.18) 45deg, transparent 90deg)',
            maskImage: 'radial-gradient(circle, #000 62%, transparent 63%)',
            WebkitMaskImage: 'radial-gradient(circle, #000 62%, transparent 63%)',
          }}
        />

        {/* Centre dot */}
        <div className="absolute top-1/2 left-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2
                        rounded-full bg-accent-soft shadow-[0_0_14px_3px_rgba(167,139,250,0.6)]" />
      </motion.div>

      {/* --- the wordmark, revealed one word at a time -------------------- */}
      <h1 className="text-center font-display text-3xl font-bold tracking-tight sm:text-5xl">
        {TITLE.split(' ').map((word, i) => (
          <motion.span
            key={word}
            /* The one filter animation in the app. It is allowed because it is
               one-shot, half a second long, and covers a few hundred pixels of
               text — not a sustained loop over the whole viewport. */
            initial={{ opacity: 0, y: 18, filter: 'blur(6px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{ duration: 0.5, delay: 0.25 + i * 0.12, ease: [0.16, 1, 0.3, 1] }}
            className="mr-[0.25em] inline-block text-gradient"
          >
            {word}
          </motion.span>
        ))}
      </h1>

      {/* --- tagline. This is the LAST thing to animate, so its completion
              is what ends the intro. --------------------------------------- */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.45, delay: 0.8 }}
        onAnimationComplete={onDone}
        className="text-sm tracking-[0.2em] text-ink-mute uppercase"
      >
        Scanning Bangalore
      </motion.p>
    </motion.div>
  )
}
