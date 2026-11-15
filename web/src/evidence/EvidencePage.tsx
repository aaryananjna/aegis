import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { SiteNav } from '../brand/SiteNav'
import { feedFromSearch, useEvents, type Feed } from '../events/useEvents'
import { BreakdownPanel } from './Breakdown'
import { RiskChart } from './RiskChart'
import { evidenceRows, initialEvidenceState, reduceEvidence, riskAt, TACTIC_LABEL } from './state'

/** For judges: why Aegis decided what it did on this call, with the caller's exact words. */
export function EvidencePage() {
  const [search] = useSearchParams()
  const feed = feedFromSearch(search, 'elder')
  return <Evidence key={JSON.stringify(feed)} feed={feed} />
}

function Evidence({ feed }: { feed: Feed }) {
  const { events, connection, error } = useEvents(feed)
  const state = useMemo(() => events.reduce(reduceEvidence, initialEvidenceState), [events])
  const [pinned, setPinned] = useState<number | null>(null)
  const rows = evidenceRows(state)
  const point = riskAt(state, pinned ?? state.lastT)
  const withAI = state.mode === 'full'

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-8 px-[4vw] py-8">
      <header className="flex flex-col gap-2">
        <SiteNav section="Evidence" />
        <h1 className="title mt-4">How Aegis judged this call</h1>
        <p className="flex flex-wrap items-center gap-3 text-[16px] text-paper-dim">
          <span className={`rounded-full border-2 px-3 py-0.5 font-semibold text-paper
                            ${withAI ? 'border-ai' : 'border-rule'}`}>
            Detection: {withAI ? 'rules + AI' : 'rules only'}
          </span>
          <span>
            {feed.kind === 'fixture'
              ? `Sample call "${feed.name}", not live`
              : feed.kind === 'live'
                ? `Live call · ${connection}`
                : 'No call connected'}
            {error ? ` · ${error}` : ''}
          </span>
        </p>
        <p className="max-w-3xl text-[15px] text-mist">
          Aegis never judges the voice. It flags what the caller says, and every flag below
          quotes the caller's exact words.
        </p>
      </header>

      <section aria-labelledby="risk-h" className="glass flex flex-col gap-3 rounded-2xl p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="risk-h" className="subtitle">Risk over the call</h2>
          <p className="text-[14px] text-mist">
            <span aria-hidden className="mr-1 inline-block size-2.5 rounded-full bg-mark" /> caller's words flagged
            <span aria-hidden className="mr-1 ml-4 inline-block h-3 w-0.5 bg-care-text align-middle" /> card shown to the grandparent
            {pinned !== null && (
              <button type="button" onClick={() => setPinned(null)}
                      className="ml-4 underline underline-offset-4 hover:text-paper focus-visible:outline-2 focus-visible:outline-paper">
                Show latest
              </button>
            )}
          </p>
        </div>
        {state.risk.length ? (
          <RiskChart state={state} pinned={pinned} onPin={setPinned} />
        ) : (
          <p className="text-[16px] text-mist">Waiting for the call to start.</p>
        )}
      </section>

      <div className="grid gap-10 lg:grid-cols-[5fr_7fr]">
        {point ? (
          <div className="glass rounded-2xl p-6">
            <BreakdownPanel point={point} />
          </div>
        ) : (
          <div />
        )}

        <section aria-labelledby="table-h" className="glass flex flex-col gap-3 rounded-2xl p-6">
          <h2 id="table-h" className="subtitle">Evidence</h2>
          {rows.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[15px]">
                <caption className="sr-only">Every flag, with the caller's exact words</caption>
                <thead className="text-[13px] text-mist">
                  <tr className="border-b border-paper/15">
                    <th scope="col" className="py-2 pr-3 font-semibold whitespace-nowrap">Time</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">What the caller did</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">Their exact words</th>
                    <th scope="col" className="py-2 font-semibold whitespace-nowrap">Found by</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} className="border-b border-paper/10 align-top">
                      <td className="py-2 pr-3 whitespace-nowrap text-paper-dim tabular-nums">{r.t.toFixed(1)} s</td>
                      <td className="py-2 pr-3 text-paper">{TACTIC_LABEL[r.tactic] ?? r.tactic}</td>
                      <td className="py-2 pr-3 text-paper">“{r.quote}”</td>
                      <td className="py-2 whitespace-nowrap text-paper-dim">
                        <span aria-hidden className={`mr-2 inline-block size-2.5 rounded-sm ${r.source === 'llm' ? 'bg-ai' : 'bg-rule'}`} />
                        {r.source === 'llm' ? 'AI' : 'Rule'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-[16px] text-mist">Nothing flagged yet.</p>
          )}
        </section>
      </div>
    </main>
  )
}
