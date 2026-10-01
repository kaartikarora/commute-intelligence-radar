import { useEffect, useRef } from 'react'
import { animate, useMotionValue, useReducedMotion } from 'framer-motion'

/**
 * A number that counts up to its value instead of snapping to it.
 *
 * The interesting part is what this does NOT do: it never calls setState.
 * A 60fps count-up driven by useState would re-render this component ~40
 * times per animation. Instead we hold the value in a framer `MotionValue`
 * (state that lives outside React) and write the formatted string straight
 * into the DOM node via a ref. React renders once; the browser does the rest.
 *
 * `tabular-nums` locks every digit to the same width, so the text does not
 * jitter horizontally as the digits change.
 */
export default function AnimatedNumber({ value, prefix = '', duration = 1.1 }) {
  const nodeRef = useRef(null)
  const motionValue = useMotionValue(0)
  const reduceMotion = useReducedMotion()

  useEffect(() => {
    const node = nodeRef.current
    if (!node) return

    const format = (n) =>
      `${prefix}${Math.round(n).toLocaleString('en-IN')}`

    if (reduceMotion) {
      node.textContent = format(value)
      return
    }

    const unsubscribe = motionValue.on('change', (latest) => {
      node.textContent = format(latest)
    })

    const controls = animate(motionValue, value, {
      duration,
      ease: [0.16, 1, 0.3, 1], // fast out of the gate, long gentle settle
    })

    // Cleanup matters here. Without it, a second search starting mid-count
    // leaves the first animation running and the two fight over the node.
    return () => {
      controls.stop()
      unsubscribe()
    }
  }, [value, prefix, duration, motionValue, reduceMotion])

  return <span ref={nodeRef} className="tabular-nums">{prefix}0</span>
}
