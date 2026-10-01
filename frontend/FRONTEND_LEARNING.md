# Frontend, from scratch

A walkthrough of the frontend in `commute-intelligence-radar/frontend`, written
to teach rather than to summarise. Every section points at real lines in your
code, and every non-obvious choice comes with the reason it was made — because
the reason is the part that transfers to your next project.

Read it in order the first time. After that it works as a reference.

---

## Table of contents

1. [How the app boots](#1-how-the-app-boots)
2. [Vite: the build tool](#2-vite-the-build-tool)
3. [Tailwind v4 and the token system](#3-tailwind-v4-and-the-token-system)
4. [React, as this app actually uses it](#4-react-as-this-app-actually-uses-it)
5. [Talking to the backend](#5-talking-to-the-backend)
6. [Framer Motion: the animation layer](#6-framer-motion-the-animation-layer)
7. [The intro, and why intros usually go wrong](#7-the-intro-and-why-intros-usually-go-wrong)
8. [Making animation cheap](#8-making-animation-cheap)
9. [Accessibility](#9-accessibility)
10. [The chart](#10-the-chart)
11. [File-by-file map](#11-file-by-file-map)
12. [Before you deploy](#12-before-you-deploy)
13. [Exercises](#13-exercises)

---

## 1. How the app boots

Four files, in this order:

```
index.html          the only real HTML page that exists
  └─ src/main.jsx   finds <div id="root"> and hands it to React
       └─ src/App.jsx        the whole UI
            └─ everything else
```

**`index.html`** is not a template React fills in. It is a real file that ships
as-is, and it is the *only* page the server ever serves. That is what "single
page app" means: one HTML document, and JavaScript swaps the contents.

Because it is the only page, everything a crawler or a link preview reads lives
there — `<title>`, `<meta name="description">`, the Open Graph tags. React never
sees these and cannot fix them for you.

Two lines worth understanding:

```html
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
```

`preconnect` tells the browser "you will need this server shortly, start the
DNS lookup and the TLS handshake now." That handshake is ~100–300ms that would
otherwise happen *after* the CSS is parsed. The `crossorigin` attribute is not
optional here: font files are fetched in CORS mode, and a connection opened
without `crossorigin` cannot be reused for them, so you would open two.

```html
<meta name="theme-color" content="#05060e" />
```

Paints the mobile browser's address bar to match the page. One line, and the
difference between "an app" and "a website in a browser".

**`src/main.jsx`** is three lines of real work:

```jsx
createRoot(document.getElementById('root')).render(
  <StrictMode><App /></StrictMode>
)
```

`StrictMode` matters more than it looks. In development it deliberately
**runs your effects twice** — mount, unmount, mount again. It is not a bug; it
is a smoke detector for effects that do not clean up after themselves. Section 7
covers a real bug it would have caught here.

---

## 2. Vite: the build tool

Two commands, two completely different machines:

| | `npm run dev` | `npm run build` |
|---|---|---|
| What it does | dev server, transforms files on demand | bundles everything into `dist/` |
| Your `.jsx` | transformed per-request, cached | compiled, tree-shaken, minified |
| Speed | instant startup | a few seconds |
| Tailwind | scans and regenerates live | scans once, emits final CSS |

**The trap:** dev is forgiving and build is not. Dev can happily serve a file
with an import that only resolves by accident, or a Tailwind class that gets
generated because some *other* file mentioned it. `npm run build` is the real
test. Run it before you deploy, every time.

### Environment variables

`src/api/index.js:13`:

```js
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
```

Three things to know:

1. **Only `VITE_`-prefixed variables are exposed.** Vite hides everything else
   on purpose, so a stray `DATABASE_PASSWORD` in your shell can never leak into
   the bundle.
2. **They are inlined at build time, not read at runtime.** After `npm run
   build`, the string `"https://api.example.com"` is literally sitting in your
   JS file. Changing the variable requires a rebuild.
3. **They are therefore public.** Anyone can read them in devtools. A `VITE_`
   variable is configuration, never a secret.

`??` is the *nullish coalescing* operator: use the left side unless it is
`null` or `undefined`. Not `||`, which would also reject the empty string and
the number zero — a bug that bites the moment a legitimate value is `0`.

---

## 3. Tailwind v4 and the token system

Tailwind's pitch is that you write `class="flex gap-4 rounded-xl"` instead of
inventing a class name, writing a CSS rule, and then maintaining the
relationship between the two. The cost is dense-looking markup. The benefit is
that deleting a component deletes its styles, and there is no such thing as a
CSS file that has quietly grown to 4,000 lines of rules nothing uses.

### v4 is configured in CSS, not JavaScript

If you read a Tailwind tutorial written before 2025 it will tell you to edit
`tailwind.config.js`. **v4 does not use one.** Configuration lives in your
stylesheet, in an `@theme` block — `src/index.css:12`.

```css
@theme {
  --color-ink: #e8eaf4;
  --color-accent: #8b5cf6;
  --font-display: "Space Grotesk", sans-serif;
  --animate-aurora: aurora 26s ease-in-out infinite;
}
```

The naming is a contract, not decoration. Tailwind reads the **prefix** and
generates a whole family of utilities:

| You write | Tailwind generates |
|---|---|
| `--color-ink` | `text-ink`, `bg-ink`, `border-ink`, `fill-ink`, `text-ink/40`… |
| `--font-display` | `font-display` |
| `--animate-aurora` | `animate-aurora` |
| `--spacing-*`, `--radius-*`, `--shadow-*` | the matching utility families |

Which is why `src/index.css` is almost entirely a list of variables. **The
tokens are the design system.** Changing `--color-accent` re-skins every button,
focus ring and hover state in the app from one line.

### Order matters

`@import "tailwindcss"` must come **first**, before `@theme`. Reversed, the
theme block is parsed before Tailwind exists to read it, your custom utilities
are silently never generated, and — the nasty part — nothing errors. You just
get unstyled elements.

### How to check it actually worked

Never assume. Build, then grep the output:

```bash
npm run build
grep -c 'animate-aurora' dist/assets/*.css     # 1 = generated, 0 = broken
```

One gotcha when you do this: Tailwind escapes the slash in opacity modifiers,
so `bg-white/8` appears in the CSS as `.bg-white\/8`. Search for a fixed string
(`grep -F 'bg-white\/8'`) or you will get a false negative and go hunting for a
bug that does not exist. (This happened while building the app.)

### `@utility` for the things tokens cannot express

Two effects need real CSS rules, so they are declared with `@utility`
(`src/index.css:133` and `:142`) and used like any built-in class:

- **`glass`** — the frosted-panel look. A 5% white fill, a 1px hairline border,
  and `backdrop-filter: blur(16px) saturate(140%)`. `backdrop-filter` blurs
  *what is behind the element* rather than the element itself, which is what
  makes the aurora smear softly through every card.
- **`text-gradient`** — `background-clip: text` paints a gradient and then uses
  the glyph shapes as a stencil. The text colour must be `transparent` or it
  paints over the gradient.

### Arbitrary values

`h-[260px]`, `bg-white/4`, `text-[11px]` — square brackets are an escape hatch
for a one-off value you do not want to promote to a token. Use them sparingly;
the moment a value appears three times it wants to be a token instead.

---

## 4. React, as this app actually uses it

### A component is a function that returns markup

```jsx
function VehicleCard({ result, index, isCheapest }) {
  return <article>…</article>
}
```

`{ result, index, isCheapest }` is **destructuring** — React passes one object
(`props`) and this pulls three named fields out of it. Data flows one
direction: parent → child, via props. A child never reaches up.

### State: the values that make it re-render

```jsx
const [pickup, setPickup] = useState('')
```

Read `pickup`, and call `setPickup` to change it. Calling the setter is what
tells React to re-run the function and update the DOM. **Assigning directly
(`pickup = 'x'`) does nothing** — React never finds out.

### The pattern worth stealing: one status, not three booleans

The obvious way to track a fetch:

```jsx
const [loading, setLoading] = useState(false)   // ← don't
const [results, setResults] = useState(null)
const [error, setError]     = useState(null)
```

Three independent flags can describe **eight** combinations. Only four of them
are real. The other four — "loading and errored", "has results and is
loading" — are states your UI will eventually land in and render wrong.

`src/App.jsx:27` uses one value instead:

```jsx
const [status, setStatus] = useState('idle')  // idle | loading | success | error
```

Now the impossible states cannot be represented. This is a **state machine**,
and it is one of the highest-leverage habits in UI code. Any time you find
yourself writing `if (loading && !error && data)`, you want a status field.

### `useCallback`, `useMemo`, `useRef`

Three hooks with three distinct jobs:

- **`useRef`** (`src/App.jsx:32`) — a box that survives re-renders and does
  **not** trigger one when it changes. Used here to hold the in-flight
  `AbortController`. That value must persist, but nothing on screen depends on
  it, so state would be wrong: it would cause a pointless re-render.
- **`useCallback`** (`src/App.jsx:34, 65, 69`) — keeps a function identity
  stable between renders. Without it, every render creates a brand-new function,
  and any child comparing props sees a change.
- **`useMemo`** (`src/ForecastChart.jsx:36`) — caches an expensive computation.
  The chart pivots 31 rows × 3 vehicles and scans them several times; without
  `useMemo` that re-runs on every render, including every single hover.

All three take a **dependency array**. `[results]` means "redo this when
`results` changes". Get it wrong and you get stale data (too few deps) or an
infinite loop (a dep that changes every render). ESLint's `react-hooks` plugin
is configured in this project and checks these for you — `npm run lint`.

### Keys, and the one that does real work here

`key` tells React which item is which across renders. Usually it is boring
(`key={result.vehicle}`). But at `src/App.jsx:130`:

```jsx
key={`${data.pickup}-${data.drop}`}
```

That is deliberate. Searching a *different* route changes the key, so React
throws the old subtree away and mounts a fresh one — which replays every
entrance animation. Same key, and React would reuse the elements and silently
swap the numbers with no animation at all.

**Changing a key is how you force a remount.** A genuinely useful trick.

### Conditional rendering

```jsx
{loading && <Spinner />}          // render only when true
{a ? <X /> : <Y />}               // either/or
```

One footgun: `{items.length && <List />}` renders a literal `0` when the array
is empty, because `0` is falsy but still a valid React child. Use
`{items.length > 0 && …}`.

---

## 5. Talking to the backend

All of it is in `src/api/index.js`, deliberately kept out of the components. A
component's job is to describe what the screen looks like; if it also knows URL
shapes and HTTP status codes, you cannot change either one without touching UI
code.

### The request

```js
const response = await fetch(`${API_BASE}/predict`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ pickup, drop }),
  signal,
})
```

`async`/`await` means "pause here until this finishes, without freezing the
page". `fetch` returns a **Promise** — a placeholder for a value that has not
arrived. `await` unwraps it.

### `fetch` does not throw on HTTP errors

The single most common `fetch` bug. A 404 or a 500 is, as far as `fetch` is
concerned, a successful round trip: the server answered. It only rejects when
the request never completed at all — server down, DNS failure, CORS blocked.

So `src/api/index.js` checks explicitly:

```js
if (!response.ok) throw new Error(`Server responded ${response.status}`)
```

### Three failure modes, three messages

Your backend has a quirk worth handling: `app.py` returns HTTP **200** with an
`{"error": "..."}` body for a bad route. So a successful response is not a
successful search. `src/App.jsx:49` separates them:

| What happened | How it is detected | What the user sees |
|---|---|---|
| Bad route | 200 with `payload.error` | the backend's own message |
| Server down / CORS | `fetch` rejects | "Could not reach the forecast service" + a hint |
| We cancelled it | `err.name === 'AbortError'` | nothing — it was intentional |

### `AbortController`: the race condition you would not have noticed

Search route A, then immediately search route B. Two requests are now in
flight. If A is slower than B, A resolves **second** and overwrites B's results
with the wrong route's prices. The UI shows B's name and A's numbers.

`src/App.jsx:37`:

```js
abortRef.current?.abort()           // kill the previous request
const controller = new AbortController()
abortRef.current = controller
// ...passed to fetch as `signal`
```

`?.` is *optional chaining* — call `.abort()` only if the thing is not
null/undefined. On the first search there is nothing to cancel.

The aborted request rejects with an `AbortError`, which line 59 swallows: it is
not a failure, it is us.

---

## 6. Framer Motion: the animation layer

### The basic shape

Any HTML tag prefixed with `motion.` accepts animation props:

```jsx
<motion.div
  initial={{ opacity: 0, y: 24 }}   // where it starts
  animate={{ opacity: 1, y: 0 }}    // where it goes
  exit={{ opacity: 0 }}             // where it goes when removed
  transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
/>
```

`initial → animate` plays on mount. That is most of the entrance animation in
this app.

### The easing curve is doing a lot of the work

`[0.16, 1, 0.3, 1]` appears all over this codebase. It is a cubic bézier with
a name — "easeOutExpo" — and it means **fast at the start, long gentle
settle**. That is the curve that reads as "responsive". Its opposite, a slow
start, reads as sluggish no matter how short the duration.

`duration` is the other half. Anything over ~0.7s for an entrance feels like
waiting. Most of this app sits between 0.35s and 0.6s.

### Stagger: why three cards feel like one gesture

`src/components/VehicleCard.jsx`:

```jsx
transition={{ duration: 0.55, delay: index * 0.09 }}
```

Each card starts 90ms after the one before. Three simultaneous fades read as a
pop-in; three offset fades read as a single sweep. Keep the offset small —
past ~150ms it stops looking like one motion and starts looking like lag.

### `AnimatePresence`: animating things that are leaving

React removes an element from the DOM the instant it stops being rendered.
There is no frame left in which to animate it. `AnimatePresence` solves this by
holding the element mounted until its `exit` animation finishes.

```jsx
<AnimatePresence mode="wait">
  {status === 'idle' && <EmptyState key="empty" />}
  {status === 'loading' && <ResultsSkeleton key="loading" />}
</AnimatePresence>
```

Two rules:
- **Every child needs a stable `key`.** That is how it tracks who left.
- **`mode="wait"`** makes the outgoing child finish leaving before the incoming
  one starts. Without it the two overlap and the layout jumps mid-crossfade.

### `whileHover` / `whileTap`

```jsx
whileHover={{ y: -6 }}
whileTap={{ scale: 0.96 }}
```

Declarative interaction states, and they animate back automatically. `whileTap`
in particular is what makes a button feel physical on mobile.

### `MotionValue`: animating without re-rendering

This is the most valuable idea in the library, and it is in
`src/components/AnimatedNumber.jsx`.

A count-up done with state re-renders the component ~40 times per second. A
`MotionValue` is state that **lives outside React**:

```jsx
const motionValue = useMotionValue(0)

motionValue.on('change', (latest) => {
  node.textContent = format(latest)     // write straight to the DOM
})

animate(motionValue, value, { duration, ease: [0.16, 1, 0.3, 1] })
```

React renders once. The animation writes directly into the text node. Zero
re-renders.

Note the cleanup at line 45:

```jsx
return () => { controls.stop(); unsubscribe() }
```

Without it, starting a second search mid-count leaves the first animation
running and two animations fight over the same DOM node. **Anything you start
in an effect, you stop in its cleanup.**

### `useReducedMotion`

```jsx
const reduceMotion = useReducedMotion()
```

Reads the OS-level "reduce motion" setting. Some people get motion sickness
from parallax and large transforms; for them this is an accessibility need, not
a preference. In this app it skips the intro entirely (`src/App.jsx:18`),
freezes the aurora, and makes the counter jump straight to its value.

There is also a CSS backstop at `src/index.css:120` that flattens every
animation duration to ~0. Be precise about what it does and does not cover: it
kills **CSS** animations and transitions only. Framer's JS-driven animations
are not CSS animations, so the backstop cannot touch them — the intro is
skipped by the JS check at `App.jsx:18`, not by that media query. The CSS rule
catches stray `@keyframes` usage; the JS handles anything whose *behaviour*
must change.

That makes one detail load-bearing: `useReducedMotion()` must return the right
answer on the **very first** render, because `useState(() => …)` reads it once
and never again. It does — framer calls `initPrefersReducedMotion()` (which
runs `matchMedia(...).matches` synchronously) immediately before its internal
`useState`. Worth knowing you depend on it. If you ever want to be independent
of that implementation detail, read the media query yourself:

```js
const [introDone, setIntroDone] = useState(
  () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
)
```

---

## 7. The intro, and why intros usually go wrong

`src/components/Intro.jsx`. Three constraints, each one a mistake avoided:

**1. It is an overlay, not a gate.**

The tempting structure:

```jsx
{!introDone ? <Intro /> : <App />}    // ← don't
```

This means the app does not even start rendering until the intro ends. You have
turned a decorative animation into a loading screen, and added its full
duration to your time-to-interactive.

What `src/App.jsx:89` does instead: the app renders immediately, and the intro
sits *on top* of it and fades away. Dismissing it reveals a page that has been
finished and painted the entire time.

**2. It is skippable.** Click, tap, scroll, or any key. Delightful the first
time is annoying the fifth time, and you have no idea which visit this is.

**3. Timing comes from `onAnimationComplete`, not `setTimeout`.**

This is the StrictMode bug from section 1. The obvious version:

```jsx
useEffect(() => { setTimeout(onDone, 1500) }, [])   // ← don't
```

In development, StrictMode runs that effect twice, so you get **two** timers.
It also does not clean up, so navigating away leaves a timer that fires into a
dead component. And it hardcodes a duration that has to be manually kept in
sync with the animation it is supposedly waiting for.

`Intro.jsx:101` hangs `onAnimationComplete={onDone}` off the last element to
animate. It cannot desync, because it *is* the animation finishing.

### The radar, in case you want to reuse it

The sweep is one div:

```css
background: conic-gradient(from 0deg, rgba(139,92,246,.55) 0deg, ... transparent 90deg);
mask-image: radial-gradient(circle, #000 62%, transparent 63%);
animation: sweep 2.6s linear infinite;    /* rotate(0) → rotate(360deg) */
```

A `conic-gradient` sweeps colour *around* a centre point, so a wedge is just a
gradient that goes transparent after 90°. The `mask-image` punches out the
middle to leave a ring. One element, no JS, no canvas.

---

## 8. Making animation cheap

The browser renders in stages: **layout** (where things go) → **paint** (what
colour each pixel is) → **composite** (stacking the layers). Each stage is more
expensive than the next one down.

- Change `width`, `height`, `top`, `margin` → full **layout**, then paint, then
  composite. Expensive.
- Change `background-color`, `box-shadow`, `filter` → **paint** + composite.
- Change `transform` or `opacity` → **composite only**, and the GPU does it.

**So: animate `transform` and `opacity`. Almost nothing else.** `y: -6` in
framer compiles to `transform: translateY(-6px)`, not `top`. That is not an
accident — it is why the library chose those property names.

Applied to the aurora (`src/components/Aurora.jsx`):

- The blur is `blur(100px)` and **never animates**. Blurring a 34rem circle is
  genuinely expensive; doing it once and then just moving the result is cheap.
  Animating the blur radius would redo that work 60 times a second.
- Three blobs, not eight.
- `@keyframes aurora` (`src/index.css:64`) touches only `translate3d` and
  `scale`.

`translate3d(x, y, 0)` rather than `translate(x, y)` is a deliberate hint to
promote the element to its own GPU layer.

**The one exception, and why it is one.** The wordmark in `Intro.jsx` animates
`filter: blur(6px) → blur(0px)`. That looks like it contradicts everything
above, so it is worth being explicit about where the line sits: the cost of a
filter scales with *area* × *frames*. One-shot, half a second, over a few
hundred pixels of text is affordable. A sustained loop over a full-viewport
layer is not — which is why the intro's exit animation uses only `opacity` and
`scale`, and why the aurora's `blur(100px)` is set once and never animated.
If you are unsure which side of the line you are on, you are probably on the
expensive side.

One real cost to know about: `backdrop-filter` (the `glass` utility) is not
free, because the browser must sample everything behind the element. A dozen
glass panels on one screen will show up on a mid-range phone. This app has
about six. Keep an eye on it.

---

## 9. Accessibility

Not a checklist bolted on at the end — most of it is just using the right
element.

**Use a real `<form>`.** `src/components/SearchPanel.jsx:27`. A form gives you
Enter-to-submit from any field, a "Go" key instead of a newline key on mobile
keyboards, and browser autofill. Building that onto a `<div onClick>` is work
you do not need to do. The one thing you owe it is `event.preventDefault()`,
or the browser does a full page reload.

**A placeholder is not a label.** It disappears the moment someone types, and
screen readers treat it as a hint, not a name. `SearchPanel.jsx:127` uses a
real `<label>` with `sr-only` — visually hidden, fully present to assistive
tech.

**Never remove a focus outline without replacing it.** `src/index.css` defines
one `:focus-visible` ring for the whole app. `:focus-visible` (rather than
`:focus`) shows it for keyboard navigation but not after a mouse click, which
is the behaviour everyone actually wants.

**Announce changes.** The loading skeleton carries `role="status"` +
`aria-live="polite"` (announced when convenient); the error carries
`role="alert"` (announced immediately). Without these, a screen reader user
clicks the button and nothing happens as far as they can tell.

**Never let colour be the only signal.** Each status badge in
`VehicleCard.jsx` pairs its colour with an icon *and* a word. Works in
greyscale, works for the ~8% of men with some colour vision deficiency, works
at a glance.

**Give the chart a text equivalent.** `ForecastChart.jsx` has a "Show the
numbers" disclosure that reveals a real `<table>` of the same data. Some people
cannot read the chart; some just want the exact value.

---

## 10. The chart

Rebuilt from `dataviz` guidance. The order matters: **form → colour →
marks → interaction → accessibility.** Colour comes fourth, not first.

### Form

Three entities changing over time → a multi-series line chart. Bars would imply
discrete buckets; three overlapping area fills turn to mud.

### Colour

The three series colours in `src/api/index.js:26` are not taste. They were run
through a palette validator against this exact dark surface and checked on five
axes: lightness band, chroma floor, colour-vision-deficiency separation
(ΔE 9.4, target ≥8), normal-vision separation (ΔE 20.9, floor ≥15), and
contrast against the background (all ≥3:1).

Two rules that came out of it:

**Colour follows the entity, never its position.**

```jsx
stroke={SERIES_HEX[vehicle.vehicle]}     // keyed by name
```

If the backend ever reorders its response, Auto stays blue. The version this
replaced picked colours by array index — so a reorder would have repainted
every line, and anyone who had learned "Auto is the blue one" would be misled.

**The UI accent is deliberately not a series colour.** Buttons and focus rings
are violet `#8b5cf6`; no line in the chart is violet. A button can never be
mistaken for data.

The same colour appears on each card's identity dot and top edge
(`VehicleCard.jsx`), so the link between card and line needs no thought.

### The y-axis is not anchored at zero

```jsx
domain={[Math.floor((min - pad) / 10) * 10, Math.ceil((max + pad) / 10) * 10]}
```

For the test route the prices ran ₹71–₹279. Anchored at zero, four hours of
surge collapses into three nearly-flat lines and the chart says nothing. Padded
to the data range, you can see the shape.

(For **bar** charts the opposite rule holds — bars encode magnitude by length,
so a truncated axis lies about the ratios. Lines encode *change*, so framing
the range is correct.)

### Finding "now" without trusting the clock

The backend sends times as bare `"%H:%M"` strings with no timezone. Once the
API is deployed somewhere other than your laptop, `new Date()` in the browser
and those strings can disagree by hours.

So `ForecastChart.jsx:62` derives it from the data instead. `find_wait_recommendation`
in `forecast.py` returns the price of the point nearest to now, rounded the same
way the curve is — so the index where **every** vehicle's forecast price equals
its own `current_price` is "now". Requiring all three to agree rules out
coincidences.

Except it does not rule out all of them, and testing against your real API
caught it: overnight, surge pins to its floor and the curve goes perfectly
flat, so *every* index matches and `findIndex` returns 0 — dragging the marker
an hour to the left. Hence the tie-break at line 66 toward the expected
position. Verified against four cases: the real payload, a flat curve, a single
clean match, and no match at all.

**The clean fix is one line in `app.py`** — add `"now": now.strftime("%H:%M")`
to the response and delete all of this. Worth doing.

### Marks and interaction

- 2px lines, round caps. Thin marks; the data does not need to shout.
- `dot={false}` — 31 dots per line is noise. Only the hovered point gets a
  marker, with a 2px ring in the surface colour so it stays readable where
  lines cross.
- `minTickGap={44}` — 31 x-axis labels on a phone overlap into a grey smear.
  Recharts drops labels until they fit.
- **Recharts' default tooltip is a white box with black text**, invisible on a
  dark background. Same for the default legend, grid and cursor. Every one of
  them is explicitly coloured here. If you ever build a dark chart and it looks
  half-empty, this is why.
- The tooltip sorts cheapest-first, because comparing is the reason you opened it.

---

## 11. File-by-file map

```
frontend/
├── index.html                    the only page; all SEO/meta lives here
├── .env.example                  VITE_API_URL — copy to .env
├── public/
│   └── radar.svg                 favicon (files here are served as-is)
└── src/
    ├── main.jsx                  React entry point
    ├── index.css                 @theme tokens, keyframes, base, @utility
    ├── App.jsx                   state machine + page layout
    ├── ForecastChart.jsx         the chart + table view
    ├── api/index.js              API base URL, fetch, palette, sample routes
    └── components/
        ├── Intro.jsx             the opening overlay
        ├── Aurora.jsx            drifting background + masked grid
        ├── SearchPanel.jsx       the form, chips, autocomplete
        ├── VehicleCard.jsx       one price card
        ├── AnimatedNumber.jsx    count-up, zero re-renders
        └── States.jsx            EmptyState / ResultsSkeleton / ErrorState
```

**Why `src/api/` and not `src/lib/`:** the repo's root `.gitignore` has `lib/`
on line 17 (a Python packaging rule). It matches `frontend/src/lib/` too, so
that file would have been silently untracked, absent from your deploy, and the
build would have failed on a missing import with no clue why. Worth running
`git status --untracked-files=all` before any first deploy.

---

## 12. Before you deploy

Four things, in order of how badly they break.

### 1. CORS will block your deployed frontend — backend, one line

`app.py:16` currently allows exactly one origin:

```python
allow_origins=["http://localhost:5173"]
```

Your deployed site is not that origin, so **every request will fail** with a
CORS error. Add the real one:

```python
allow_origins=["http://localhost:5173", "https://your-site.vercel.app"]
```

### 2. Point the frontend at the deployed API

Set `VITE_API_URL` in your host's environment variables **before** the build
runs — it is inlined at build time, so setting it afterwards does nothing.

It must be `https://`. An https page cannot fetch an http endpoint; the browser
blocks it as *mixed content*, and the error in the console does not obviously
say so.

### 3. Geocoding is not scoped to Bangalore — backend, one line

`geocoding.py:6` sends the bare place name to Nominatim:

```python
params = {"q": place_name, "format": "json"}
```

"Whitefield" is also a town in the UK, and Nominatim may well prefer it —
after which `is_in_blr()` rejects the coordinates and the user gets "This tool
only works for routes inside Bangalore" for a road they are standing on. Fix:

```python
params = {"q": f"{place_name}, Bengaluru, India", "format": "json"}
```

This is why the four sample chips use only endpoints that appear in
`watched_routes.csv` — names your backend has already resolved successfully.
The autocomplete list is broader and will be fully reliable once this is fixed.

### 4. The bundle is 741 kB (224 kB gzipped)

Mostly Recharts. Fine to ship; worth knowing. If you want it smaller, lazy-load
the chart so it only downloads once there are results to draw:

```jsx
const ForecastChart = lazy(() => import('./ForecastChart'))
// then wrap the usage in <Suspense fallback={<ResultsSkeleton />}>
```

### Pre-flight

```bash
npm run build     # must pass — dev being happy proves nothing
npm run lint      # must pass
npm run preview   # serves dist/ — the real thing, not the dev server
git status --untracked-files=all   # nothing important ignored
```

---

## 13. Exercises

Roughly increasing difficulty. Each one teaches something specific.

1. **Re-skin the app.** Change `--color-accent` in `src/index.css` and nothing
   else. Watch buttons, focus rings, chips and hover states all follow. That is
   what a token system buys you.
2. **Add a fourth sample chip.** Use two endpoints that appear in
   `watched_routes.csv` so it is guaranteed to geocode.
3. **Make the intro longer, then shorter.** Change the `delay` on the tagline
   in `Intro.jsx`. Notice that the dismissal timing follows automatically — no
   second number to update. That is the payoff of `onAnimationComplete`.
4. **Break something on purpose.** Delete `mode="wait"` from the
   `AnimatePresence` in `App.jsx:112` and search twice. Watch the states
   overlap. Put it back.
5. **Prove the abort works.** Add `console.log` in the `AbortError` branch
   (`App.jsx:59`), then click two chips in quick succession.
6. **Persist the last route.** Save `pickup`/`drop` to `localStorage` and
   restore them on mount. You will need `useEffect` — and you will discover why
   it needs a dependency array.
7. **Lazy-load the chart** as sketched in section 12, and compare the build
   output before and after.
8. **Fix the two backend one-liners** from section 12, then broaden the sample
   chips and autocomplete now that any Bangalore name resolves correctly.
