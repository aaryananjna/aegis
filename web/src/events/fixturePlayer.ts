import type { AegisEvent } from './types'

export function parseJsonl(text: string): AegisEvent[] {
  return text
    .split('\n')
    .filter((line) => line.trim() !== '')
    .map((line) => JSON.parse(line) as AegisEvent)
}

/**
 * Replay events at their original timing: each one fires `t` seconds (divided by `speed`)
 * after start. Events with the same `t` keep file order. Returns a stop function.
 */
export function playFixture(
  events: AegisEvent[],
  onEvent: (e: AegisEvent) => void,
  onDone: () => void,
  speed = 1,
): () => void {
  const timers = events.map((e) =>
    window.setTimeout(() => onEvent(e), (e.t * 1000) / speed),
  )
  const last = events.reduce((m, e) => Math.max(m, e.t), 0)
  timers.push(window.setTimeout(onDone, (last * 1000) / speed + 1))
  return () => timers.forEach((id) => window.clearTimeout(id))
}
