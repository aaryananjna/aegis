import { useCallback, useEffect, useRef, useState } from 'react'
import { parseJsonl, playFixture } from './fixturePlayer'
import { FAMILY_TYPES, type AegisEvent, type OutboundMessage, type Role } from './types'

export type Feed =
  | { kind: 'live'; sessionId: string; role: Role; token: string | null }
  | { kind: 'fixture'; name: string; role: Role; speed: number }
  | { kind: 'none'; role: Role }

export type Connection =
  | 'idle'
  | 'loading'
  | 'playing'
  | 'connecting'
  | 'open'
  | 'reconnecting'
  | 'ended'
  | 'error'

/** `?fixture=scam-grandson[&speed=2]` replays a sample; `?session=s1&token=…` connects live. */
export function feedFromSearch(search: URLSearchParams, role: Role): Feed {
  const fixture = search.get('fixture')
  if (fixture) {
    const speed = Number(search.get('speed') ?? '1')
    return { kind: 'fixture', name: fixture, role, speed: speed > 0 ? speed : 1 }
  }
  const session = search.get('session')
  if (session) return { kind: 'live', sessionId: session, role, token: search.get('token') }
  return { kind: 'none', role }
}

// Reconnects get the session's past events again (CONTRACTS C6), so skip ones we already have.
function eventKey(e: AegisEvent): string {
  if ('seq' in e && typeof e.seq === 'number') return `seq:${e.seq}`
  if (e.type === 'caption') return `caption:${e.utterance_id}:${e.revision}:${e.is_final}`
  return `${e.type}:${e.t}`
}

function liveUrl(feed: Extract<Feed, { kind: 'live' }>): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const q = new URLSearchParams({ role: feed.role })
  if (feed.token) q.set('token', feed.token)
  return `${proto}://${window.location.host}/events/${encodeURIComponent(feed.sessionId)}?${q}`
}

const BAD_TOKEN = 4401

export function useEvents(feed: Feed) {
  // Each event with the wall-clock time it arrived here (ms), for "8:42 PM" on the family page.
  const [log, setLog] = useState<{ events: AegisEvent[]; receivedAt: number[] }>({
    events: [],
    receivedAt: [],
  })
  const [connection, setConnection] = useState<Connection>('idle')
  const [error, setError] = useState<string | null>(null)
  const socket = useRef<WebSocket | null>(null)
  // Sample calls only: stop the recording and add events on the spot (the screen's own buttons).
  const sample = useRef<{ add: (e: AegisEvent) => void; stop: () => void } | null>(null)
  const feedKey = JSON.stringify(feed)

  useEffect(() => {
    const f = JSON.parse(feedKey) as Feed
    setLog({ events: [], receivedAt: [] })
    setError(null)
    if (f.kind === 'none') {
      setConnection('idle')
      return
    }

    const seen = new Set<string>()
    let ended = false
    const add = (e: AegisEvent) => {
      if (f.role === 'family' && !FAMILY_TYPES.has(e.type)) return // the server filters live (C4)
      const key = eventKey(e)
      if (seen.has(key)) return
      seen.add(key)
      if (e.type === 'call_ended') ended = true
      const at = Date.now()
      setLog((prev) => ({ events: [...prev.events, e], receivedAt: [...prev.receivedAt, at] }))
    }

    if (f.kind === 'fixture') {
      let stop = () => {}
      let cancelled = false
      setConnection('loading')
      fetch(`/fixtures/events-${encodeURIComponent(f.name)}.jsonl`)
        .then((r) => {
          // A missing file comes back as index.html with 200 (single-page app fallback).
          if (!r.ok || r.headers.get('content-type')?.includes('text/html')) {
            throw new Error(`fixture "${f.name}" not found in web/public/fixtures/`)
          }
          return r.text()
        })
        .then((text) => {
          if (cancelled) return
          setConnection('playing')
          stop = playFixture(parseJsonl(text), add, () => setConnection('ended'), f.speed)
        })
        .catch((err: Error) => {
          if (cancelled) return
          setError(err.message)
          setConnection('error')
        })
      sample.current = {
        add,
        stop: () => {
          cancelled = true // not loaded yet: never start it
          stop()
          setConnection('ended')
        },
      }
      return () => {
        cancelled = true
        stop()
        sample.current = null
      }
    }

    let closedByUs = false
    let mine: WebSocket | null = null // this effect's socket, never another effect's
    let retry = 0
    let retryTimer: number | undefined

    const connect = () => {
      setConnection(retry === 0 ? 'connecting' : 'reconnecting')
      const ws = new WebSocket(liveUrl(f))
      mine = ws
      socket.current = ws
      ws.onopen = () => {
        retry = 0
        setConnection('open')
      }
      ws.onmessage = (msg) => {
        try {
          add(JSON.parse(String(msg.data)) as AegisEvent)
        } catch {
          // Not JSON: ignore it rather than break the screen.
        }
      }
      ws.onclose = (ev) => {
        // A late close from an older socket (React StrictMode, reconnects) must not drop the new one.
        if (socket.current === ws) socket.current = null
        if (closedByUs) return
        if (ev.code === BAD_TOKEN && seen.size > 0 && !ended) {
          // The tokens die with the call. Refused after we'd already heard it means it ended
          // while we were reconnecting (#78): show it as ended, not as a broken link.
          add({ type: 'call_ended', session_id: f.sessionId, t: performance.now() / 1000 })
          setConnection('ended')
        } else if (ev.code === BAD_TOKEN && !ended) {
          setError('This call has ended, or this link is no longer valid.')
          setConnection('error')
        } else if (ended) {
          setConnection('ended')
        } else {
          retry += 1
          setConnection('reconnecting')
          retryTimer = window.setTimeout(connect, Math.min(5000, 500 * 2 ** retry))
        }
      }
    }
    connect()

    return () => {
      closedByUs = true
      window.clearTimeout(retryTimer)
      mine?.close()
      if (socket.current === mine) socket.current = null
    }
  }, [feedKey])

  /** Send set_elder or codeword_result. Returns false when there's no open live socket. */
  const send = useCallback((msg: OutboundMessage): boolean => {
    const ws = socket.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return false
    ws.send(JSON.stringify(msg))
    return true
  }, [])

  /**
   * Sample calls only: what a real call would do after a tap, played here because there's no
   * server. `stop` ends the recording first (the rest of the script no longer applies).
   */
  const playLocally = useCallback((events: AegisEvent[], opts: { stop?: boolean } = {}) => {
    const s = sample.current
    if (!s) return
    if (opts.stop) s.stop()
    events.forEach(s.add)
  }, [])

  return { events: log.events, receivedAt: log.receivedAt, connection, error, send, playLocally }
}
