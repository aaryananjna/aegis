import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import type { AegisEvent } from '../events/types.ts'
import { breakdown, evidenceRows, initialEvidenceState, reduceEvidence, riskAt } from './state.ts'

const fixture = (name: string) =>
  readFileSync(new URL(`../../public/fixtures/events-${name}.jsonl`, import.meta.url), 'utf8')
    .split('\n').filter(Boolean).map((l) => JSON.parse(l) as AegisEvent)
const run = (events: AegisEvent[]) => events.reduce(reduceEvidence, initialEvidenceState)

test('scam fixture: risk steps, final marks, both cards, and a quote per evidence row', () => {
  const s = run(fixture('scam-grandson'))
  assert.equal(s.risk[0].score < 0.1, true)
  assert.deepEqual(s.cards.map((c) => c.kind), ['codeword', 'hangup'])
  assert.equal(s.marks.length, 4)
  const rows = evidenceRows(s)
  assert.deepEqual(rows.map((r) => r.tactic).slice(0, 3), ['impersonation', 'distress', 'secrecy'])
  assert.ok(rows.every((r) => r.quote.length > 0 && r.source === 'rule'))
  assert.equal(s.mode, null) // no status event: the page says "rules only"
})

test('riskAt is a step function', () => {
  const s = run(fixture('scam-grandson'))
  assert.equal(riskAt(s, 12.5)?.level, 'elevated') // set at 12.0, next change at 15.0
  assert.equal(riskAt(s, 19)?.level, 'high')
  assert.equal(riskAt(s, -1), undefined)
})

test('provisional highlights never become evidence; an empty final clears a line', () => {
  const ts = (provisional: boolean, evidence: unknown[], seq: number) =>
    ({ type: 'tactic_set', session_id: 's', t: seq, seq, utterance_id: 'u1', revision: 0,
       provisional, evidence }) as AegisEvent
  const hit = [{ tactic: 'secrecy', quote: 'x', span: [0, 1], source: 'rule' }]
  assert.equal(evidenceRows(run([ts(true, hit, 1)])).length, 0)
  assert.equal(evidenceRows(run([ts(false, hit, 1)])).length, 1)
  assert.equal(evidenceRows(run([ts(false, hit, 1), ts(false, [], 2)])).length, 0)
})

test('breakdown splits rule, AI and combination', () => {
  const b = breakdown({ t: 1, score: 0.9, level: 'high', contributions: {
    rule: { secrecy: 1.5, payment: 2 }, llm: { impersonation: 0.4, payment: 0.1 },
    combos: { 'secrecy+payment': 1 } } })
  assert.deepEqual(b.totals, { rule: 3.5, ai: 0.5, combination: 1 })
  assert.equal(b.tactics[0].tactic, 'payment')
  assert.deepEqual(b.combos, [{ pair: 'secrecy+payment', value: 1 }])
})

test('status.mode full means the AI layer is on', () => {
  const s = run([{ type: 'status', session_id: 's', t: 1, seq: 1, mode: 'full', warning: null } as AegisEvent])
  assert.equal(s.mode, 'full')
})
