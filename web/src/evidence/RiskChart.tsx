import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent, type RefObject } from 'react'
import { CARD_LABEL, riskAt, TACTIC_LABEL, type EvidenceState } from './state'

const H = 300
const M = { l: 48, r: 104, t: 28, b: 36 } // right margin holds the threshold labels
const LEVEL_WORD = { low: 'Normal call', elevated: 'Be careful', high: 'Warning' } as const

/**
 * Risk score over the call: one step line (risk is sent only when it changes), dots where the
 * caller's words were flagged (final highlights only) and a rule where each card appeared.
 * Hover shows the moment; click or arrow keys pin it for the breakdown below.
 */
export function RiskChart({
  state,
  pinned,
  onPin,
}: {
  state: EvidenceState
  pinned: number | null
  onPin: (t: number | null) => void
}) {
  const box = useRef<HTMLDivElement>(null)
  const width = useWidth(box)
  const [hover, setHover] = useState<number | null>(null)

  const end = Math.max(state.lastT, 5)
  const W = Math.max(width, 320)
  const x = (t: number) => M.l + (t / end) * (W - M.l - M.r)
  const y = (v: number) => M.t + (1 - v) * (H - M.t - M.b)
  const tAt = (px: number) => Math.min(end, Math.max(0, ((px - M.l) / (W - M.l - M.r)) * end))

  let path = ''
  state.risk.forEach((p, i) => {
    path += i === 0 ? `M${x(p.t)},${y(p.score)}` : `H${x(p.t)}V${y(p.score)}`
  })
  if (state.risk.length) path += `H${x(end)}`

  const ticks = Array.from({ length: Math.floor(end / 5) + 1 }, (_, i) => i * 5)
  const focus = hover ?? pinned
  const atFocus = focus === null ? undefined : riskAt(state, focus)
  const nearMarks = focus === null ? [] : state.marks.filter((m) => Math.abs(m.t - focus) < 0.75)

  const onMove = (e: PointerEvent<SVGRectElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    setHover(tAt(e.clientX - r.left + M.l))
  }
  // Arrow keys step through the moments the score changed.
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const times = state.risk.map((p) => p.t)
    if (!times.length) return
    const cur = pinned ?? times[times.length - 1]
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault()
      const later = e.key === 'ArrowRight'
      const next = later ? times.find((t) => t > cur) : [...times].reverse().find((t) => t < cur)
      onPin(next ?? cur)
    } else if (e.key === 'Escape') onPin(null)
  }

  return (
    <div
      ref={box}
      className="relative focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-paper"
      tabIndex={0}
      role="group"
      aria-label="Risk over the call. Left and right arrows step through changes; Escape shows the latest."
      onKeyDown={onKey}
    >
      <svg width={W} height={H} className="block max-w-full" aria-hidden>
        {/* recessive grid: the two thresholds that change the elder screen */}
        {[
          { v: 0.5, word: 'Be careful' },
          { v: 0.8, word: 'Warning' },
        ].map(({ v, word }) => (
          <g key={v}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} stroke="currentColor"
                  className="text-paper/15" strokeDasharray="4 4" />
            <text x={W - M.r + 8} y={y(v) + 4} className="fill-mist text-[13px]">{word} ({v})</text>
          </g>
        ))}
        <line x1={M.l} x2={W - M.r} y1={y(0)} y2={y(0)} className="stroke-paper/25" />
        {[0, 0.5, 1].map((v) => (
          <text key={v} x={M.l - 10} y={y(v) + 4} textAnchor="end" className="fill-mist text-[13px]">{v}</text>
        ))}
        {ticks.map((t) => (
          <text key={t} x={x(t)} y={H - 12} textAnchor="middle" className="fill-mist text-[13px]">{t} s</text>
        ))}

        {/* cards: status colors, always with a text label */}
        {state.cards.map((c) => (
          <g key={`${c.kind}-${c.t}`}>
            <line x1={x(c.t)} x2={x(c.t)} y1={M.t - 6} y2={y(0)} strokeWidth={2}
                  className={c.kind === 'hangup' ? 'stroke-alarm-text' : 'stroke-care-text'} />
            <text x={x(c.t) + (c.kind === 'hangup' ? 6 : -6)} y={M.t - 12}
                  textAnchor={c.kind === 'hangup' ? 'start' : 'end'}
                  className="fill-paper text-[13px] font-semibold">{CARD_LABEL[c.kind]}</text>
          </g>
        ))}

        <path d={path} fill="none" strokeWidth={2} className="stroke-paper" strokeLinejoin="round" />

        {state.marks.map((m) => {
          const p = riskAt(state, m.t)
          return p ? (
            <circle key={`${m.utteranceId}-${m.t}`} cx={x(m.t)} cy={y(p.score)} r={5}
                    className="fill-mark stroke-dusk" strokeWidth={2} />
          ) : null
        })}

        {focus !== null && (
          <line x1={x(focus)} x2={x(focus)} y1={M.t} y2={y(0)} strokeWidth={1}
                className={hover === null ? 'stroke-paper/60' : 'stroke-paper/35'} />
        )}
        <rect x={M.l} y={M.t} width={W - M.l - M.r} height={H - M.t - M.b} fill="transparent"
              onPointerMove={onMove} onPointerLeave={() => setHover(null)}
              onClick={() => hover !== null && onPin(hover)} className="cursor-crosshair" />
      </svg>

      {focus !== null && atFocus && (
        <div
          className="pointer-events-none absolute top-2 max-w-72 rounded-lg border border-paper/15 bg-dusk-raised
                     px-3 py-2 text-[14px] text-paper shadow-lg"
          style={x(focus) > W / 2 ? { right: W - x(focus) + 12 } : { left: x(focus) + 12 }}
        >
          <p className="font-semibold">
            {focus.toFixed(1)} s · {LEVEL_WORD[atFocus.level]} · {atFocus.score.toFixed(2)}
          </p>
          {nearMarks.flatMap((m) => m.evidence).map((ev, i) => (
            <p key={i} className="text-paper-dim">
              {TACTIC_LABEL[ev.tactic] ?? ev.tactic}: “{ev.quote}”
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

function useWidth(ref: RefObject<HTMLDivElement | null>): number {
  const [w, setW] = useState(960)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => setW(Math.floor(entry.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [ref])
  return w
}
