// Event shapes from CONTRACTS.md v2.1 (branch docs/contract-v2.1).

export type Role = 'elder' | 'family'

export type Tactic =
  | 'impersonation'
  | 'urgency'
  | 'secrecy'
  | 'payment'
  | 'threat'
  | 'verification_avoidance'
  | 'remote_access'
  | 'distress'

interface Base {
  session_id: string
  t: number
}

// Detector events carry seq; server events (caption, call_ended, server status) don't.
interface Detector extends Base {
  seq: number
}

export interface CaptionEvent extends Base {
  type: 'caption'
  utterance_id: string
  revision: number
  speaker_raw: string | null
  text: string
  start_s: number
  end_s: number
  is_final: boolean
  source?: 'live' | 'typed'
}

export interface TacticSetEvent extends Detector {
  type: 'tactic_set'
  utterance_id: string
  revision: number
  provisional: boolean
  evidence: { tactic: Tactic; quote: string; span: [number, number]; source: 'rule' | 'llm' }[]
}

export interface RiskEvent extends Detector {
  type: 'risk'
  score: number
  level: 'low' | 'elevated' | 'high'
  contributions: {
    rule: Record<string, number>
    llm: Record<string, number>
    combos: Record<string, number>
  }
}

export interface InterventionEvent extends Detector {
  type: 'intervention'
  kind: 'codeword' | 'hangup'
  text: string
  latched: boolean
}

export interface AlertEvent extends Detector {
  type: 'alert'
  alert_id: string
  kind: 'codeword' | 'hangup'
  evidence: string[]
  summary: string
}

export interface StatusEvent extends Base {
  type: 'status'
  seq?: number
  mode?: 'rules_only' | 'full'
  stt?: 'deepgram' | 'whisper' | 'typed' | 'none'
  warning: string | null
}

export interface CallEndedEvent extends Base {
  type: 'call_ended'
}

export type AegisEvent =
  | CaptionEvent
  | TacticSetEvent
  | RiskEvent
  | InterventionEvent
  | AlertEvent
  | StatusEvent
  | CallEndedEvent

// What the elder screen sends back on its /events socket.
export type OutboundMessage =
  | { type: 'set_elder'; session_id?: string; speaker_raw: string | null }
  | { type: 'codeword_result'; session_id?: string; ok: boolean }

// C4: the only events the family page receives.
export const FAMILY_TYPES: ReadonlySet<AegisEvent['type']> = new Set([
  'alert',
  'intervention',
  'status',
  'call_ended',
])
