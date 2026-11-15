import { useEffect, useRef } from 'react'
import type { AegisEvent } from './types'

/**
 * The landing page's demo shows Grandma's screen and the family phone side by side, each
 * replaying the same sample. A tap on Grandma's screen ("They knew it", "End call") changes the
 * call, so the phone has to hear about it too. Both frames carry `?demo=<id>` and talk over a
 * same-browser BroadcastChannel; nothing leaves the browser.
 */
export type DemoTap = 'codeword_ok' | 'end'

const channelName = (id: string) => `aegis-demo:${id}`

/** The events a tap stands for, as the server would have sent them on a real call. */
export function eventsForTap(tap: DemoTap, sessionId: string): AegisEvent[] {
  const t = performance.now() / 1000
  return tap === 'codeword_ok'
    ? [{ type: 'codeword_ok', session_id: sessionId, t, seq: 1_000_000, resolves: 'codeword' }]
    : [{ type: 'call_ended', session_id: sessionId, t }]
}

export function tellDemo(id: string | null, tap: DemoTap) {
  if (!id || typeof BroadcastChannel === 'undefined') return
  const ch = new BroadcastChannel(channelName(id))
  ch.postMessage(tap)
  ch.close()
}

export function useDemoTaps(id: string | null, onTap: (tap: DemoTap) => void) {
  const handler = useRef(onTap)
  useEffect(() => {
    handler.current = onTap
  })
  useEffect(() => {
    if (!id || typeof BroadcastChannel === 'undefined') return
    const ch = new BroadcastChannel(channelName(id))
    ch.onmessage = (m) => {
      if (m.data === 'codeword_ok' || m.data === 'end') handler.current(m.data)
    }
    return () => ch.close()
  }, [id])
}
