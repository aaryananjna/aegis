import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import type { AegisEvent } from '../events/types.ts'
import { endSummary, initialFamilyState, reduceFamily } from './state.ts'

const alert = (kind: 'codeword' | 'hangup', seq: number, evidence = ['a', 'b', 'c', 'd']) =>
  ({ type: 'alert', session_id: 's1', t: seq, seq, alert_id: `s1:${kind}`, kind, evidence,
     summary: `summary ${kind}` }) as AegisEvent
const run = (events: AegisEvent[]) =>
  events.reduce((s, e, i) => reduceFamily(s, e, 1000 * i), initialFamilyState)

test('an alert replayed after reconnecting shows once, with at most 3 quotes', () => {
  const s = run([alert('codeword', 1), alert('codeword', 1)])
  assert.equal(s.alerts.length, 1)
  assert.deepEqual(s.alerts[0].quotes, ['a', 'b', 'c'])
})

test('codeword_ok and call_ended are remembered', () => {
  const s = run([alert('codeword', 1),
                 { type: 'codeword_ok', session_id: 's1', t: 2, seq: 2, resolves: 's1:codeword' } as AegisEvent,
                 { type: 'call_ended', session_id: 's1', t: 3 } as AegisEvent])
  assert.equal(s.codewordOk, true)
  assert.equal(s.endedAt, 2000)
  assert.match(endSummary(s, 'Rose'), /passed the family code word/)
})

test('end summary for a quiet call and a hang up call', () => {
  assert.equal(endSummary(initialFamilyState, 'Rose'), 'No warning signs on this call.')
  assert.match(endSummary(run([alert('codeword', 1), alert('hangup', 2)]), 'Rose'),
               /^2 alerts\. Rose was told to hang up/)
})

test('the end summary matches the hang up card that was shown', () => {
  const verify = { ...alert('codeword', 1), kind: 'verify', alert_id: 's1:verify' } as AegisEvent
  // A fake grandson: "Hang up. Call back on the saved number."
  assert.match(endSummary(run([alert('codeword', 1), alert('hangup', 2)]), 'Rose'), /saved number/)
  // A fake bank: "Hang up. Call the number on your card or their official website." No saved number.
  const bank = endSummary(run([verify, alert('hangup', 2)]), 'Rose')
  assert.doesNotMatch(bank, /saved number/)
  assert.match(bank, /^2 alerts\. Rose was told to hang up and call the real number/)
})

test('scam fixture gives a codeword then a hangup alert', () => {
  const events = readFileSync(new URL('../../public/fixtures/events-scam-grandson.jsonl', import.meta.url), 'utf8')
    .split('\n').filter(Boolean).map((l) => JSON.parse(l) as AegisEvent)
  assert.deepEqual(run(events).alerts.map((a) => a.kind), ['codeword', 'hangup'])
})
