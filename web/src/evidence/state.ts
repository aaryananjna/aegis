// What the judges' evidence page shows, folded from the elder-role event stream. Pure.
import type { AegisEvent, CardKind, RiskEvent, Tactic, TacticSetEvent } from '../events/types'

export interface RiskPoint {
  t: number
  score: number
  level: RiskEvent['level']
  contributions: RiskEvent['contributions']
}

export interface TacticMark {
  t: number
  utteranceId: string
  evidence: TacticSetEvent['evidence']
}

export interface EvidenceRow {
  t: number
  tactic: Tactic
  quote: string
  source: 'rule' | 'llm'
}

export interface EvidenceState {
  risk: RiskPoint[]
  marks: TacticMark[] // final tactic_sets only, in arrival order
  latestByUtterance: Record<string, TacticMark> // what's true now (each one replaces the last)
  cards: { t: number; kind: CardKind }[]
  mode: 'rules_only' | 'full' | null
  lastT: number
}

export const initialEvidenceState: EvidenceState = {
  risk: [],
  marks: [],
  latestByUtterance: {},
  cards: [],
  mode: null,
  lastT: 0,
}

export function reduceEvidence(s: EvidenceState, e: AegisEvent): EvidenceState {
  const lastT = Math.max(s.lastT, 't' in e ? e.t : 0)
  switch (e.type) {
    case 'risk':
      return { ...s, lastT, risk: [...s.risk, { t: e.t, score: e.score, level: e.level,
                                                 contributions: e.contributions }] }
    case 'tactic_set': {
      if (e.provisional) return { ...s, lastT } // interim guesses never score
      const mark = { t: e.t, utteranceId: e.utterance_id, evidence: e.evidence }
      const latestByUtterance = { ...s.latestByUtterance }
      if (e.evidence.length === 0) delete latestByUtterance[e.utterance_id]
      else latestByUtterance[e.utterance_id] = mark
      return { ...s, lastT, latestByUtterance,
               marks: e.evidence.length ? [...s.marks, mark] : s.marks }
    }
    case 'intervention':
      return { ...s, lastT, cards: [...s.cards, { t: e.t, kind: e.kind }] }
    case 'status':
      return { ...s, lastT, mode: e.mode ?? s.mode }
    default:
      return { ...s, lastT }
  }
}

/** The evidence table: every current piece of evidence, oldest first. */
export function evidenceRows(s: EvidenceState): EvidenceRow[] {
  return Object.values(s.latestByUtterance)
    .flatMap((m) => m.evidence.map((ev) => ({ t: m.t, tactic: ev.tactic, quote: ev.quote, source: ev.source })))
    .sort((a, b) => a.t - b.t)
}

/** The risk point in force at time t (risk is only sent when it changes: a step function). */
export function riskAt(s: EvidenceState, t: number): RiskPoint | undefined {
  let found: RiskPoint | undefined
  for (const p of s.risk) {
    if (p.t <= t) found = p
    else break
  }
  return found
}

export interface Breakdown {
  totals: { rule: number; ai: number; combination: number }
  tactics: { tactic: string; rule: number; ai: number }[] // biggest first
  combos: { pair: string; value: number }[] // biggest first
}

/** Split one risk point's contributions by source: rule, AI and combination. */
export function breakdown(p: RiskPoint): Breakdown {
  const { rule, llm, combos } = p.contributions
  const names = [...new Set([...Object.keys(rule), ...Object.keys(llm)])]
  const tactics = names
    .map((tactic) => ({ tactic, rule: rule[tactic] ?? 0, ai: llm[tactic] ?? 0 }))
    .sort((a, b) => b.rule + b.ai - (a.rule + a.ai))
  const comboRows = Object.entries(combos)
    .map(([pair, value]) => ({ pair, value }))
    .sort((a, b) => b.value - a.value)
  const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0)
  return { totals: { rule: sum(rule), ai: sum(llm), combination: sum(combos) }, tactics, combos: comboRows }
}

// Plain names for judges; the contract's id is shown next to it.
export const TACTIC_LABEL: Record<string, string> = {
  impersonation: 'Pretending to be someone',
  urgency: 'Rushing',
  secrecy: 'Asking for secrecy',
  payment: 'Unusual payment',
  threat: 'Threats',
  verification_avoidance: 'Dodging questions',
  remote_access: 'Remote control of a device',
  distress: 'Sounding panicked',
}

// Short names for combination rows ("Pretending + Payment").
export const TACTIC_SHORT: Record<string, string> = {
  impersonation: 'Pretending',
  urgency: 'Rushing',
  secrecy: 'Secrecy',
  payment: 'Payment',
  threat: 'Threats',
  verification_avoidance: 'Dodging',
  remote_access: 'Remote control',
  distress: 'Panic',
}

export const CARD_LABEL: Record<CardKind, string> = {
  codeword: 'Code word card',
  verify: 'Check-who-it-is card',
  hangup: 'Hang up card',
}
