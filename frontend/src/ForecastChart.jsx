import { useMemo, useState } from 'react'
import {
  CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { SERIES_HEX } from './api'

/* Chart chrome. Deliberately recessive: the data is the only thing that gets
   to be bright on this surface. */
const GRID = '#ffffff0f'
const AXIS = '#ffffff1a'
const MUTED = '#6f7592'

/* How far into the curve "now" sits: forecast.py builds PAST_HOURS=1 of
   history and GRAPH_HOURS=4 ahead, so now is one fifth of the way along.
   This is only ever used as a TIE-BREAKER between points the data has already
   confirmed are candidates — never as the answer on its own. If the backend
   ever changes those constants, a curve with any variation in it still lands
   on the right point from the data alone; only the perfectly-flat overnight
   case would drift, and there every point has the same price anyway.
   (The clean fix is one line in app.py: return `now.strftime("%H:%M")` in the
   response and delete all of this.) */
const PAST_SHARE = 1 / 5

/**
 * Four hours of predicted price for every vehicle type, plus the hour of
 * context behind us.
 *
 * Form choice: change-over-time across three entities, so a multi-series line
 * chart. (Bars would imply discrete buckets; an area chart with three
 * overlapping fills would turn to mud.)
 */
export default function ForecastChart({ results }) {
  const [showTable, setShowTable] = useState(false)

  const { chartData, nowLabel, domain } = useMemo(() => {
    const times = results[0].forecast.map((p) => p.time)

    // Pivot: the API gives one array per vehicle, Recharts wants one row per
    // x-value with a key per series.
    const rows = times.map((time, i) => {
      const row = { time }
      results.forEach((v) => { row[v.vehicle] = v.forecast[i].price })
      return row
    })

    /* Where is "now" on this axis?
       Not `new Date()`. The backend formats times as a bare "%H:%M" with no
       timezone, so once the API is deployed anywhere but this laptop the
       browser clock and those strings disagree. Instead we find it in the
       data: find_wait_recommendation returns the price of the forecast point
       nearest to now, rounded the same way the curve is, so any index where
       EVERY vehicle's forecast price equals its own current_price is a
       candidate for "now". Requiring all three to agree rules out most
       coincidences.

       But it does not rule out all of them. Overnight the surge factor pins to
       its floor and the curve goes perfectly flat, so every point matches and
       the first one wins — which would drag the marker an hour to the left.
       So when there is more than one candidate we break the tie toward where
       "now" is expected to sit. See PAST_SHARE. */
    const candidates = rows
      .map((_, i) => i)
      .filter((i) => results.every((v) => v.forecast[i].price === v.current_price))

    const expected = Math.round((rows.length - 1) * PAST_SHARE)
    const nowIndex = candidates.length
      ? candidates.reduce((a, b) => (Math.abs(b - expected) < Math.abs(a - expected) ? b : a))
      : -1

    // Pad the y-domain instead of anchoring it at zero. These prices sit in a
    // narrow band a long way above zero; a 0-anchored axis would squash four
    // hours of surge into three nearly-flat lines and hide the whole story.
    const all = rows.flatMap((r) => results.map((v) => r[v.vehicle]))
    const min = Math.min(...all)
    const max = Math.max(...all)
    const pad = Math.max((max - min) * 0.18, 10)

    return {
      chartData: rows,
      nowLabel: nowIndex >= 0 ? times[nowIndex] : null,
      domain: [
        Math.max(0, Math.floor((min - pad) / 10) * 10),
        Math.ceil((max + pad) / 10) * 10,
      ],
    }
  }, [results])

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-base font-semibold text-ink">Next four hours</h2>
          <p className="text-xs text-ink-mute">
            Predicted fare per vehicle type{nowLabel ? ` · now ${nowLabel}` : ''}
          </p>
        </div>
        <SeriesLegend results={results} />
      </div>

      {/* Shorter on phones. A 400px chart plus a legend on a 360px-wide screen
          leaves no room for the page around it. */}
      <div className="h-[260px] w-full sm:h-[380px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
            <CartesianGrid stroke={GRID} strokeWidth={1} vertical={false} />

            {/* The hour behind us, dimmed. It separates "already happened"
                from "predicted" without needing a second colour. */}
            {nowLabel && (
              <ReferenceArea
                x1={chartData[0].time}
                x2={nowLabel}
                fill="#ffffff"
                fillOpacity={0.025}
              />
            )}

            <XAxis
              dataKey="time"
              stroke={AXIS}
              tick={{ fill: MUTED, fontSize: 11 }}
              tickLine={false}
              /* 31 points on a phone would overlap into a grey smear.
                 minTickGap makes Recharts drop labels until they fit. */
              minTickGap={44}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={domain}
              stroke={AXIS}
              tick={{ fill: MUTED, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={56}
              tickFormatter={(v) => `₹${v}`}
            />

            <Tooltip
              content={<PriceTooltip nowLabel={nowLabel} />}
              /* The crosshair. Without an explicit colour this renders as a
                 near-black line that is invisible on a dark surface. */
              cursor={{ stroke: '#ffffff33', strokeWidth: 1 }}
            />

            {nowLabel && (
              <ReferenceLine
                x={nowLabel}
                stroke="#ffffff59"
                strokeWidth={1}
                strokeDasharray="3 4"
                label={{ value: 'now', position: 'insideTopLeft', fill: MUTED, fontSize: 10 }}
              />
            )}

            {results.map((vehicle) => (
              <Line
                key={vehicle.vehicle}
                type="monotone"
                dataKey={vehicle.vehicle}
                /* Colour is keyed to the vehicle NAME, not to its position in
                   the array. If the backend ever reorders its response, Auto
                   stays blue. */
                stroke={SERIES_HEX[vehicle.vehicle]}
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                /* A dot on all 31 points is noise. Only the hovered point gets
                   a marker, sized >=8px across, with a 2px ring in the surface
                   colour so it stays readable where two lines cross. */
                dot={false}
                activeDot={{
                  r: 4.5,
                  fill: SERIES_HEX[vehicle.vehicle], // explicit: don't rely on it inheriting
                  strokeWidth: 2,
                  stroke: '#0b0d18',
                }}
                isAnimationActive
                animationDuration={900}
                animationEasing="ease-out"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* The table view. Every chart needs a non-visual path to the same
          numbers: for screen readers, for anyone who cannot separate the hues,
          and honestly for anyone who just wants to read an exact value. */}
      <div className="mt-4 border-t border-hairline pt-3">
        <button
          type="button"
          onClick={() => setShowTable((s) => !s)}
          aria-expanded={showTable}
          className="text-xs font-medium text-ink-mute transition-colors hover:text-ink-soft"
        >
          {showTable ? 'Hide the numbers' : 'Show the numbers'}
        </button>

        {showTable && (
          <div className="mt-3 max-h-64 overflow-auto rounded-xl border border-hairline">
            <table className="w-full text-left text-xs tabular-nums">
              <caption className="sr-only">
                Predicted fare by time and vehicle type
              </caption>
              <thead className="sticky top-0 bg-surface text-ink-mute">
                <tr>
                  <th scope="col" className="px-3 py-2 font-medium">Time</th>
                  {results.map((v) => (
                    <th key={v.vehicle} scope="col" className="px-3 py-2 font-medium">
                      {v.vehicle}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="text-ink-soft">
                {chartData.map((row) => (
                  <tr
                    key={row.time}
                    className={row.time === nowLabel ? 'bg-accent/10 text-ink' : ''}
                  >
                    <th scope="row" className="px-3 py-1.5 font-normal">{row.time}</th>
                    {results.map((v) => (
                      <td key={v.vehicle} className="px-3 py-1.5">{'₹'}{row[v.vehicle]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

/** Custom legend: a colour key beside each name. Identity never rests on the
 *  colour alone, because the name is always right there next to it. */
function SeriesLegend({ results }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      {results.map((v) => (
        <li key={v.vehicle} className="flex items-center gap-1.5 text-xs text-ink-soft">
          <span
            className="h-0.5 w-4 rounded-full"
            style={{ backgroundColor: SERIES_HEX[v.vehicle] }}
          />
          {v.vehicle}
        </li>
      ))}
    </ul>
  )
}

/** Recharts' default tooltip is a white box with black text, unreadable on
 *  this surface. Replacing `content` is the supported way to restyle it. */
function PriceTooltip({ active, payload, label, nowLabel }) {
  if (!active || !payload?.length) return null

  // Cheapest first: the reason someone opened this tooltip is to compare.
  const rows = [...payload].sort((a, b) => a.value - b.value)

  return (
    <div className="rounded-xl border border-hairline bg-surface/95 px-3 py-2
                    shadow-2xl backdrop-blur-xl">
      <p className="mb-1.5 text-[11px] font-medium text-ink-mute">
        {label}{label === nowLabel ? ' · now' : ''}
      </p>
      <ul className="space-y-1">
        {rows.map((row) => (
          <li key={row.dataKey} className="flex items-center gap-2 text-xs">
            {/* Read the colour from our own map rather than from `row.stroke`.
                Recharts does not guarantee `stroke` on a tooltip payload entry,
                and an undefined value here would silently render a colourless
                dot — losing the tooltip's only identity channel. Same map the
                lines use, so the two can never disagree. */}
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: SERIES_HEX[row.dataKey] }}
            />
            <span className="text-ink-soft">{row.dataKey}</span>
            <span className="ml-auto pl-3 font-medium text-ink tabular-nums">
              {'₹'}{row.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
