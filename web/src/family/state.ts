// What the family phone shows, folded from the (already role-filtered) event stream. Pure.
import type { AegisEvent, CardKind } from '../events/types'

export interface FamilyAlert {
  alertId: string
  kind: CardKind
  summary: string
  quotes: string[] // at most 3, strongest first
  receivedAt: number // ms, wall clock on this phone
}

export interface FamilyState {
  alerts: FamilyAlert[] // oldest first, one per alert_id
  codewordOk: boolean
  endedAt: number | null
}

export const initialFamilyState: FamilyState = { alerts: [], codewordOk: false, endedAt: null }

export function reduceFamily(s: FamilyState, e: AegisEvent, receivedAt: number): FamilyState {
  switch (e.type) {
    case 'alert':
      // Same alert_id twice (a replay after reconnecting) is the same alert: show it once.
      if (s.alerts.some((a) => a.alertId === e.alert_id)) return s
      return {
        ...s,
        alerts: [
          ...s.alerts,
          { alertId: e.alert_id, kind: e.kind, summary: e.summary,
            quotes: e.evidence.slice(0, 3), receivedAt },
        ],
      }
    case 'codeword_ok':
      return { ...s, codewordOk: true }
    case 'call_ended':
      return s.endedAt === null ? { ...s, endedAt: receivedAt } : s
    default:
      return s
  }
}

/**
 * The heading once the call is over. After an alert, the family's first question is "is she OK?",
 * so it says she hung up (#107). Uses only call_ended and the alerts already received.
 */
export function endTitle(s: FamilyState, name: string): string {
  if (s.endedAt === null || s.alerts.length === 0) return 'Call ended'
  return `${name.charAt(0).toUpperCase()}${name.slice(1)} hung up safely`
}

/** One line for when the call is over. */
export function endSummary(s: FamilyState, name: string): string {
  const last = s.alerts[s.alerts.length - 1]
  if (!last) return `No warning signs on this call.`
  const count = s.alerts.length === 1 ? '1 alert' : `${s.alerts.length} alerts`
  if (last.kind === 'hangup') return `${count}. ${name} was told to hang up and call back on a saved number.`
  if (s.codewordOk) return `${count}. The caller passed the family code word.`
  return `${count}. ${name} was told to check who was calling.`
}
