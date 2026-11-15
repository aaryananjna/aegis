// Everything the elder screen shows, folded from the event stream. Pure, so it's easy to test.
import type { AegisEvent, CardKind, RiskEvent, StatusEvent, TacticSetEvent } from '../events/types'

export interface Caption {
  utteranceId: string
  revision: number
  text: string
  isFinal: boolean
  speakerRaw: string | null
  typed: boolean
  startS: number // seconds into the call, for the faint "0:42"
}

export interface Highlight {
  provisional: boolean
  evidence: TacticSetEvent['evidence']
}

export interface Voice {
  speakerRaw: string | null
  lastText: string
}

export interface ElderState {
  order: string[] // utterance ids, oldest first
  captions: Record<string, Caption>
  highlights: Record<string, Highlight>
  voices: Voice[] // in order of first appearance
  level: RiskEvent['level'] | null
  card: { kind: CardKind; text: string } | null
  codewordOk: boolean
  warning: string | null
  stt: StatusEvent['stt'] | null // where captions come from, when the server says
  elderSet: { speakerRaw: string | null; by: 'server' | 'tap' } | null // latest elder_set
  ended: boolean
}

export const initialElderState: ElderState = {
  order: [],
  captions: {},
  highlights: {},
  voices: [],
  level: null,
  card: null,
  codewordOk: false,
  warning: null,
  stt: null,
  elderSet: null,
  ended: false,
}

// Cards only move forward: codeword or verify first, then hangup (CONTRACTS: latched).
const CARD_RANK: Record<CardKind, number> = { codeword: 1, verify: 1, hangup: 2 }

export function reduceElder(s: ElderState, e: AegisEvent): ElderState {
  switch (e.type) {
    case 'caption': {
      if (s.ended) return s // nothing is shown (or kept) after the call ends
      const old = s.captions[e.utterance_id]
      const newer =
        !old ||
        (!old.isFinal &&
          (e.revision > old.revision || (e.revision === old.revision && e.is_final)))
      if (!newer) return s // stale revision, or an update after the final
      const caption: Caption = {
        utteranceId: e.utterance_id,
        revision: e.revision,
        text: e.text,
        isFinal: e.is_final,
        speakerRaw: e.speaker_raw,
        typed: e.source === 'typed',
        startS: e.start_s,
      }
      const known = s.voices.some((v) => v.speakerRaw === e.speaker_raw)
      const voices = known
        ? s.voices.map((v) => (v.speakerRaw === e.speaker_raw ? { ...v, lastText: e.text } : v))
        : [...s.voices, { speakerRaw: e.speaker_raw, lastText: e.text }]
      return {
        ...s,
        order: old ? s.order : [...s.order, e.utterance_id],
        captions: { ...s.captions, [e.utterance_id]: caption },
        voices,
      }
    }
    case 'tactic_set': {
      const highlights = { ...s.highlights }
      if (e.evidence.length === 0) delete highlights[e.utterance_id]
      else highlights[e.utterance_id] = { provisional: e.provisional, evidence: e.evidence }
      return { ...s, highlights }
    }
    case 'risk':
      return s.ended ? s : { ...s, level: e.level }
    case 'intervention': {
      if (s.ended) return s
      if (s.card && CARD_RANK[e.kind] <= CARD_RANK[s.card.kind]) return s
      return { ...s, card: { kind: e.kind, text: e.text } }
    }
    case 'codeword_ok':
      return { ...s, codewordOk: true }
    case 'status':
      return { ...s, warning: e.warning, stt: e.stt ?? s.stt }
    case 'elder_set':
      return { ...s, elderSet: { speakerRaw: e.speaker_raw, by: e.by } }
    case 'call_ended':
      // The call isn't saved, so the screen lets go of everything that was said.
      return { ...s, ended: true, order: [], captions: {}, highlights: {}, voices: [], card: null, level: null }
    default:
      return s
  }
}

/**
 * True when the screen can't tell voices apart, so "tap the voice that is you" makes no sense:
 * the captions come from a source without speaker labels (Whisper fallback, or none), or every
 * caption so far arrived without a speaker label.
 */
export function noVoiceLabels(s: ElderState): boolean {
  if (s.stt === 'whisper' || s.stt === 'none') return true
  return s.order.length > 0 && s.order.every((uid) => s.captions[uid].speakerRaw === null)
}

export interface Piece {
  text: string
  marked: boolean
}

/**
 * Split caption text into plain and highlighted pieces. A span is used only if it still points
 * at its quote (the text may have moved on since); otherwise the quote is searched for.
 * Overlapping spans ("no time" inside "there's no time") merge into one highlight.
 */
export function highlightPieces(text: string, evidence: Highlight['evidence']): Piece[] {
  const ranges: [number, number][] = []
  for (const ev of evidence) {
    let [start, end] = ev.span
    if (text.slice(start, end) !== ev.quote) {
      start = text.indexOf(ev.quote)
      if (start < 0 || ev.quote === '') continue
      end = start + ev.quote.length
    }
    ranges.push([start, end])
  }
  ranges.sort((a, b) => a[0] - b[0])
  const merged: [number, number][] = []
  for (const r of ranges) {
    const last = merged[merged.length - 1]
    if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1])
    else merged.push([r[0], r[1]])
  }
  const pieces: Piece[] = []
  let at = 0
  for (const [start, end] of merged) {
    if (start > at) pieces.push({ text: text.slice(at, start), marked: false })
    pieces.push({ text: text.slice(start, end), marked: true })
    at = end
  }
  if (at < text.length) pieces.push({ text: text.slice(at), marked: false })
  return pieces
}
