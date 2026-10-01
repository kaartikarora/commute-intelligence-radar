import { useReducedMotion } from 'framer-motion'

/**
 * The drifting colour wash behind the whole page.
 *
 * Three absolutely-positioned circles, blurred into soft clouds and slowly
 * moved around. The cost of this effect is almost entirely in the blur, so:
 *
 *  - the blur radius is STATIC (`blur-[100px]`). Animating a filter forces the
 *    browser to re-run the blur every single frame, which is what turns a
 *    pretty background into a phone-melting one.
 *  - the animation only touches `transform`, which the compositor can do on
 *    the GPU without touching layout or paint.
 *  - three blobs, not eight.
 *
 * `aria-hidden` keeps it out of the accessibility tree — it is decoration, and
 * a screen reader announcing "image" here would be noise.
 */
export default function Aurora() {
  const reduceMotion = useReducedMotion()

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      {/* Violet, top-left */}
      <div
        className={`absolute -top-40 -left-32 h-[34rem] w-[34rem] rounded-full
                    bg-accent/25 blur-[100px]
                    ${reduceMotion ? '' : 'animate-aurora'}`}
      />
      {/* Blue, top-right */}
      <div
        className={`absolute -top-24 right-[-14rem] h-[30rem] w-[30rem] rounded-full
                    bg-series-1/20 blur-[100px]
                    ${reduceMotion ? '' : 'animate-aurora-slow'}`}
      />
      {/* Teal, low centre — anchors the page so the bottom isn't dead black */}
      <div
        className={`absolute top-[55%] left-1/4 h-[26rem] w-[26rem] rounded-full
                    bg-series-3/15 blur-[100px]
                    ${reduceMotion ? '' : 'animate-aurora'}`}
        style={{ animationDelay: '-9s' }}
      />

      {/* A faint grid, masked so it fades out toward the edges. Pure CSS: two
          repeating linear-gradients make the lines, and the mask-image keeps
          the pattern from looking like graph paper stapled over the design. */}
      <div
        className="absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage: `
            linear-gradient(to right, rgba(255,255,255,0.045) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255,255,255,0.045) 1px, transparent 1px)`,
          backgroundSize: '64px 64px',
          maskImage: 'radial-gradient(ellipse 80% 60% at 50% 0%, #000 30%, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(ellipse 80% 60% at 50% 0%, #000 30%, transparent 75%)',
        }}
      />
    </div>
  )
}
