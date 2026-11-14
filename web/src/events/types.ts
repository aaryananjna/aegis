// Event shapes from CONTRACTS.md v2.1 (branch docs/contract-v2.1), plus what main's detector
// emits since PR #8 (`verify` card) and PR #9 (`codeword_ok`).

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

// codeword: caller claims to be family. verify: a bank, the government, a company or no one.
export type CardKind = 'codeword' | 'verify' | 'hangup'

export interface InterventionEvent extends Detector {
  type: 'intervention'
  kind: CardKind
  text: string
  latched: boolean
}

export interface AlertEvent extends Detector {
  type: 'alert'
  alert_id: string
  kind: CardKind
  evidence: string[]
  summary: string
}

// The caller gave the right family code word (sent after codeword_result ok:true).
export interface CodewordOkEvent extends Detector {
  type: 'codeword_ok'
  resolves: string
}

export interface StatusEvent extends Base {
  type: 'status'
  seq?: number
  mode?: 'rules_only' | 'full'
  stt?: 'deepgram' | 'whisper' | 'typed' | 'none'
  warning: string | null
}

// Who the server is scoring as the grandparent (A, #39/#40). Elder screens only, no seq.
// by "server": the server guessed it (first "Hello?"), or speaker_raw null in labels-off mode.
// by "tap": the grandparent's own tap reached the detector.
export interface ElderSetEvent extends Base {
  type: 'elder_set'
  speaker_raw: string | null
  by: 'server' | 'tap'
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
  | CodewordOkEvent
  | ElderSetEvent
  | StatusEvent
  | CallEndedEvent

// What the elder screen sends back on its /events socket.
export type OutboundMessage =
  | { type: 'set_elder'; session_id?: string; speaker_raw: string | null }
  | { type: 'codeword_result'; session_id?: string; ok: boolean }
  | { type: 'end'; session_id?: string } // elder only (#42): ends the call for everyone

// C4: the only events the family page receives (plus codeword_ok, per detection/INTEGRATION.md).
export const FAMILY_TYPES: ReadonlySet<AegisEvent['type']> = new Set([
  'alert',
  'intervention',
  'codeword_ok',
  'status',
  'call_ended',
])
