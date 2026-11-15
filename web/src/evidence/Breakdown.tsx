import { breakdown, TACTIC_LABEL, TACTIC_SHORT, type RiskPoint } from './state'

const PART = {
  rule: { label: 'Rule', swatch: 'bg-rule' },
  ai: { label: 'AI', swatch: 'bg-ai' },
  combination: { label: 'Combination', swatch: 'bg-combo' },
} as const

const LEVEL_WORD = { low: 'Normal call', elevated: 'Be careful', high: 'Warning' } as const

/** What pushed the score up at one moment, split by where it came from. */
export function BreakdownPanel({ point }: { point: RiskPoint }) {
  const b = breakdown(point)
  const total = b.totals.rule + b.totals.ai + b.totals.combination
  const rowMax = Math.max(0.0001, ...b.tactics.map((r) => r.rule + r.ai), ...b.combos.map((c) => c.value))

  return (
    <section aria-labelledby="breakdown-h" className="flex flex-col gap-4">
      <div>
        <h2 id="breakdown-h" className="subtitle">What added up</h2>
        <p aria-live="polite" className="text-[15px] text-paper-dim">
          At {point.t.toFixed(1)} s: {LEVEL_WORD[point.level]}, score {point.score.toFixed(2)}
        </p>
      </div>

      <ul className="flex flex-wrap gap-x-5 gap-y-1 text-[14px] text-paper-dim" aria-label="Legend">
        {(Object.keys(PART) as (keyof typeof PART)[]).map((k) => (
          <li key={k} className="flex items-center gap-2">
            <span aria-hidden className={`size-3 rounded-sm ${PART[k].swatch}`} />
            {PART[k].label} {b.totals[k].toFixed(2)}
          </li>
        ))}
      </ul>

      {total > 0 ? (
        <div className="flex h-5 gap-[2px]" role="img"
             aria-label={`Rule ${b.totals.rule.toFixed(2)}, AI ${b.totals.ai.toFixed(2)}, combination ${b.totals.combination.toFixed(2)}`}>
          {(Object.keys(PART) as (keyof typeof PART)[]).filter((k) => b.totals[k] > 0).map((k) => (
            <span key={k} className={`h-full first:rounded-l last:rounded-r ${PART[k].swatch}`}
                  style={{ width: `${(b.totals[k] / total) * 100}%` }} />
          ))}
        </div>
      ) : (
        <p className="text-[15px] text-mist">Nothing has pushed the score up yet.</p>
      )}

      <table className="w-full text-[15px]">
        <caption className="sr-only">Push on the score from each tactic and combination</caption>
        <tbody>
          {b.tactics.map((r) => (
            <Row key={r.tactic} label={TACTIC_LABEL[r.tactic] ?? r.tactic} id={r.tactic}
                 parts={[{ v: r.rule, cls: 'bg-rule' }, { v: r.ai, cls: 'bg-ai' }]} max={rowMax} />
          ))}
          {b.combos.map((c) => (
            <Row key={c.pair} label={c.pair.split('+').map((t) => TACTIC_SHORT[t] ?? t).join(' + ')}
                 id={c.pair} parts={[{ v: c.value, cls: 'bg-combo' }]} max={rowMax} />
          ))}
        </tbody>
      </table>

      <p className="text-[13px] leading-snug text-mist">
        Each number is how hard that part pushes the score up. They add to a fixed starting value
        and are squeezed into a 0 to 1 risk score. It's not a probability. AI can only add, and
        never more than the rules already found for the same tactic.
      </p>
    </section>
  )
}

function Row({ label, id, parts, max }: {
  label: string
  id: string
  parts: { v: number; cls: string }[]
  max: number
}) {
  const sum = parts.reduce((a, p) => a + p.v, 0)
  return (
    <tr className="align-middle">
      <th scope="row" className="w-[45%] py-1.5 pr-3 text-left font-normal text-paper">
        {label}
        <span className="sr-only"> ({id.includes('+') ? 'combination' : id})</span>
      </th>
      <td className="py-1.5">
        <div className="flex h-3.5 gap-[2px]">
          {parts.filter((p) => p.v > 0).map((p, i) => (
            <span key={i} className={`h-full first:rounded-l last:rounded-r ${p.cls}`}
                  style={{ width: `${(p.v / max) * 100}%` }} />
          ))}
        </div>
      </td>
      <td className="w-14 py-1.5 pl-3 text-right text-paper-dim tabular-nums">{sum.toFixed(2)}</td>
    </tr>
  )
}
