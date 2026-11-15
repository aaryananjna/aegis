// Run with `npm test` (Node's built-in runner, which strips TypeScript types itself).
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import type { AegisEvent } from '../events/types.ts'
import { callFamilyLine, highlightPieces, initialElderState, noVoiceLabels, reduceElder } from './state.ts'

const base = { session_id: 's1', t: 1 }
const cap = (uid: string, revision: number, text: string, is_final: boolean, speaker = '1') =>
  ({ ...base, type: 'caption', utterance_id: uid, revision, text, is_final, speaker_raw: speaker,
     start_s: 0, end_s: 1 }) as AegisEvent
const card = (kind: 'codeword' | 'verify' | 'hangup', seq: number) =>
  ({ ...base, seq, type: 'intervention', kind, text: kind, latched: true }) as AegisEvent
const run = (events: AegisEvent[]) => events.reduce(reduceElder, initialElderState)
const fixture = (name: string) =>
  readFileSync(new URL(`../../public/fixtures/events-${name}.jsonl`, import.meta.url), 'utf8')
    .split('\n').filter(Boolean).map((l) => JSON.parse(l) as AegisEvent)

test('interim is replaced in place by a higher revision, then the final', () => {
  const s = run([cap('u1', 0, 'Nana', false), cap('u1', 1, 'Nana it is', false),
                 cap('u1', 1, 'Nana it is me', true)])
  assert.deepEqual(s.order, ['u1'])
  assert.equal(s.captions.u1.text, 'Nana it is me')
  assert.equal(s.captions.u1.isFinal, true)
})

test('stale revisions and updates after the final are ignored', () => {
  const s = run([cap('u1', 2, 'new', false), cap('u1', 1, 'old', false),
                 cap('u1', 2, 'final', true), cap('u1', 3, 'late', false)])
  assert.equal(s.captions.u1.text, 'final')
})

test('voices are listed once each, with their latest line', () => {
  const s = run([cap('u0', 0, 'Hello?', true, '0'), cap('u1', 0, 'Nana', true, '1'),
                 cap('u2', 0, 'Where are you?', true, '0')])
  assert.deepEqual(s.voices, [{ speakerRaw: '0', lastText: 'Where are you?' },
                              { speakerRaw: '1', lastText: 'Nana' }])
})

test('empty evidence clears highlights for that utterance', () => {
  const ts = (evidence: unknown[]) =>
    ({ ...base, seq: 1, type: 'tactic_set', utterance_id: 'u1', revision: 0,
       provisional: true, evidence }) as AegisEvent
  const on = run([ts([{ tactic: 'secrecy', quote: 'x', span: [0, 1], source: 'rule' }])])
  assert.ok(on.highlights.u1)
  assert.equal(reduceElder(on, ts([])).highlights.u1, undefined)
})

test('cards latch: never go back, hangup replaces codeword or verify', () => {
  assert.equal(run([card('codeword', 1), card('verify', 2)]).card?.kind, 'codeword')
  assert.equal(run([card('verify', 1), card('hangup', 2), card('verify', 3)]).card?.kind, 'hangup')
})

test('overlapping spans merge, and a moved quote is found again', () => {
  const text = "Nana, there's no time for that"
  const pieces = highlightPieces(text, [
    { tactic: 'urgency', quote: 'no time', span: [14, 21], source: 'rule' },
    { tactic: 'verification_avoidance', quote: "there's no time", span: [6, 21], source: 'rule' },
  ])
  assert.deepEqual(pieces.filter((p) => p.marked).map((p) => p.text), ["there's no time"])
  assert.equal(pieces.map((p) => p.text).join(''), text)
  const moved = highlightPieces('Oh, ' + text, [
    { tactic: 'urgency', quote: 'no time', span: [14, 21], source: 'rule' }])
  assert.deepEqual(moved.filter((p) => p.marked).map((p) => p.text), ['no time'])
})

test('scam fixture ends on the hangup card, red, with highlights on caller lines', () => {
  const s = run(fixture('scam-grandson'))
  assert.equal(s.card?.kind, 'hangup')
  assert.equal(s.level, 'high')
  for (const [uid, h] of Object.entries(s.highlights)) {
    for (const ev of h.evidence) assert.equal(s.captions[uid].text.slice(...ev.span), ev.quote)
  }
})

test('benign fixture stays calm with no card', () => {
  const s = run(fixture('benign-party'))
  assert.equal(s.card, null)
  assert.equal(s.level, 'low')
  assert.equal(Object.keys(s.highlights).length, 0)
})

test('bank fixture shows verify first, then hangup', () => {
  const events = fixture('demo-bank')
  const first = events.findIndex((e) => e.type === 'intervention')
  assert.equal(run(events.slice(0, first + 1)).card?.kind, 'verify')
  assert.equal(run(events).card?.kind, 'hangup')
})

test('no voice labels: every caption unlabeled, or a source without labels', () => {
  const status = (stt: string) =>
    ({ ...base, type: 'status', stt, warning: null }) as AegisEvent
  assert.equal(noVoiceLabels(initialElderState), false) // nothing heard yet: don't decide
  assert.equal(noVoiceLabels(run([cap('u0', 0, 'Hello?', true, null as unknown as string)])), true)
  assert.equal(noVoiceLabels(run([cap('u0', 0, 'Hello?', true, '0')])), false)
  assert.equal(noVoiceLabels(run([status('whisper')])), true)
  assert.equal(noVoiceLabels(run([status('none')])), true)
  assert.equal(noVoiceLabels(run([status('deepgram'), cap('u0', 0, 'Hi', true, '1')])), false)
  // A later status without stt (a detector warning) keeps what the server said.
  const s = run([status('whisper'), { ...base, seq: 2, type: 'status', mode: 'rules_only',
                                      warning: 'x' } as AegisEvent])
  assert.equal(s.stt, 'whisper')
})

test('no-labels fixture: captions carry no speaker and the scam still reaches hangup', () => {
  const s = run(fixture('scam-nolabels'))
  assert.equal(noVoiceLabels(s), true)
  assert.equal(s.card?.kind, 'hangup')
})

test('elder_set: the latest one wins, by server or by tap', () => {
  const es = (speaker_raw: string | null, by: 'server' | 'tap') =>
    ({ ...base, type: 'elder_set', speaker_raw, by }) as AegisEvent
  assert.equal(run([]).elderSet, null)
  assert.deepEqual(run([es('0', 'server')]).elderSet, { speakerRaw: '0', by: 'server' })
  assert.deepEqual(run([es('0', 'server'), es('1', 'tap')]).elderSet, { speakerRaw: '1', by: 'tap' })
  assert.deepEqual(run([es(null, 'server')]).elderSet, { speakerRaw: null, by: 'server' })
})

test('autovoice and labels-off fixtures carry elder_set and still reach hangup', () => {
  const auto = run(fixture('scam-autovoice'))
  assert.deepEqual(auto.elderSet, { speakerRaw: '0', by: 'server' })
  assert.equal(auto.card?.kind, 'hangup')
  const off = run(fixture('scam-labelsoff'))
  assert.deepEqual(off.elderSet, { speakerRaw: null, by: 'server' })
  assert.equal(off.card?.kind, 'hangup')
})

test('call_ended clears the captions, highlights and card', () => {
  const sid = 's'
  const events = [
    { type: 'caption', session_id: sid, t: 1, utterance_id: 'u1', revision: 0, speaker_raw: null,
      text: 'I need bail money', start_s: 1, end_s: 2, is_final: true },
    { type: 'intervention', session_id: sid, t: 2, seq: 1, kind: 'hangup', text: 'Hang up.', latched: true },
    { type: 'call_ended', session_id: sid, t: 3 },
    { type: 'caption', session_id: sid, t: 4, utterance_id: 'u2', revision: 0, speaker_raw: null,
      text: 'late line', start_s: 4, end_s: 5, is_final: true },
  ] as AegisEvent[]
  const s = events.reduce(reduceElder, initialElderState)
  assert.equal(s.ended, true)
  assert.deepEqual(s.order, [])
  assert.deepEqual(s.captions, {})
  assert.equal(s.card, null)
})

const risk = (level: 'low' | 'elevated' | 'high', seq: number) =>
  ({ ...base, seq, type: 'risk', score: 0.5, level, contributions: {} }) as AegisEvent
const ended = { ...base, type: 'call_ended' } as AegisEvent

test('warned is set by a card or a Warning and survives the end of the call (#107)', () => {
  assert.equal(run([risk('elevated', 1), ended]).warned, false)
  const byLevel = run([risk('high', 1), risk('low', 2), ended])
  assert.equal(byLevel.warned, true)
  assert.equal(byLevel.card, null) // the card and words are still dropped
  assert.deepEqual(byLevel.order, [])
  assert.equal(run([card('verify', 1), ended]).warned, true)
  assert.equal(run([ended, risk('high', 2)]).warned, false) // nothing counts after the end
})

test('the scam sample ends warned', () => {
  assert.equal(run([...fixture('scam-grandson'), ended]).warned, true)
})

test('callFamilyLine uses a known name, else plain words', () => {
  assert.equal(callFamilyLine('Anna'), 'Call Anna now')
  assert.equal(callFamilyLine('  '), 'Call your family now')
  assert.equal(callFamilyLine(null), 'Call your family now')
  assert.equal(callFamilyLine('x'.repeat(31)), 'Call your family now')
})
