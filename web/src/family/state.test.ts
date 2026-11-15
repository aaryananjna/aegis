import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import type { AegisEvent } from '../events/types.ts'
import { endSummary, endTitle, initialFamilyState, reduceFamily } from './state.ts'

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

test('scam fixture gives a codeword then a hangup alert', () => {
  const events = readFileSync(new URL('../../public/fixtures/events-scam-grandson.jsonl', import.meta.url), 'utf8')
    .split('\n').filter(Boolean).map((l) => JSON.parse(l) as AegisEvent)
  assert.deepEqual(run(events).alerts.map((a) => a.kind), ['codeword', 'hangup'])
})

test('endTitle says she hung up safely only after an alert and the end of the call (#107)', () => {
  const ended = { type: 'call_ended', session_id: 's1', t: 9 } as AegisEvent
  assert.equal(endTitle(run([ended]), 'Rose'), 'Call ended')
  assert.equal(endTitle(run([alert('codeword', 1)]), 'Rose'), 'Call ended')
  assert.equal(endTitle(run([alert('codeword', 1), ended]), 'Rose'), 'Rose hung up safely')
  assert.equal(endTitle(run([alert('hangup', 1), ended]), 'your family member'), 'Your family member hung up safely')
})
