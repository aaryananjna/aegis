import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, api, deviceToken, type ElderRef, type User } from '../accounts/api'
import { useEvents } from '../events/useEvents'
import { CallSides } from '../landing/CallSides'
import { FamilyQr } from './FamilyQr'
import { ScaledFrame } from '../landing/ScaledFrame'
import { localPath, savedFamilyUrl } from './familyLink'

/**
 * For the recorded demo only: show the family's phone view beside the grandparent's screen,
 * because a Mac screen recording can't capture the real phone. Set to false for the final
 * submission; the QR code alone is enough there.
 */
const SHOW_FAMILY_PHONE = true

type Started = { sessionId: string; elderUrl: string; familyUrl: string; recorded: boolean }

// The running call survives a trip to /evidence and back in this tab (the server keeps running it).
const CALL_KEY = 'aegis_live_call'
const savedCall = {
  get(): Started | null {
    try {
      return JSON.parse(sessionStorage.getItem(CALL_KEY) ?? 'null')
    } catch {
      return null
    }
  },
  set(c: Started | null) {
    try {
      if (c) sessionStorage.setItem(CALL_KEY, JSON.stringify(c))
      else sessionStorage.removeItem(CALL_KEY)
    } catch {
      // storage blocked: the call shows until this page is left
    }
  },
}

const startError = (e: unknown): string => {
  if (!(e instanceof ApiError)) return 'Something went wrong. Try again.'
  switch (e.status) {
    case 0:
      return "Can't reach the Aegis server. Is it running?"
    case 400:
      return 'Live captions need the Deepgram key on the server (DEEPGRAM_API_KEY).'
    case 401:
      return "This laptop's pairing isn't valid any more. Pair it again from My family."
    case 403:
      return 'Calls can only be started on the Aegis laptop itself.'
    case 429:
      return 'Too many calls are running. End one first.'
    default:
      return 'Something went wrong. Try again.'
  }
}

/**
 * The logged-in front page (#63): start a live call from here, then watch the grandparent's live
 * captions right on this page, with the family link as a QR code beside them. The server
 * listens on the laptop mic (`mic: true`) with speaker labels off, as in the demo setup.
 */
export function LiveCall() {
  const [elders, setElders] = useState<ElderRef[]>([])
  const [who, setWho] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [call, setCallState] = useState<Started | null>(() => savedCall.get())
  const setCall = (c: Started | null) => {
    savedCall.set(c)
    setCallState(c)
  }
  const clearCall = useCallback(() => {
    savedCall.set(null)
    setCallState(null)
  }, [])

  useEffect(() => {
    api<{ user: User; elders: ElderRef[] }>('GET', '/auth/me')
      .then((r) => {
        setElders(r.elders)
        setWho((w) => w || r.elders[0]?.display_name || '')
      })
      .catch(() => {}) // the call still starts; the family page just says "your family member"
  }, [])

  const start = async () => {
    setBusy(true)
    setError(null)
    const token = deviceToken.get()
    try {
      const r = await api<{ session_id: string; elder_url: string; family_url: string; recorded: boolean }>(
        'POST',
        '/sessions',
        { ...(who ? { name: who.slice(0, 40) } : {}), mic: true, labels: false },
        token ? { 'X-Device-Token': token } : {},
      )
      savedFamilyUrl.set(r.session_id, r.family_url)
      setCall({ sessionId: r.session_id, elderUrl: r.elder_url, familyUrl: r.family_url, recorded: r.recorded })
    } catch (e) {
      setError(startError(e))
    } finally {
      setBusy(false)
    }
  }

  if (call) return <Running call={call} onDone={clearCall} />

  return (
    <section aria-labelledby="start-h" className="glass flex flex-col gap-5 rounded-3xl p-[clamp(1.25rem,3vw,2rem)]">
      <div className="flex flex-col gap-1">
        <h2 id="start-h" className="subtitle text-[1.6rem]">Start a call</h2>
        <p className="text-[18px] text-paper-dim">
          Put the phone on speaker next to this laptop. Aegis listens through the laptop's microphone
          and shows live captions here.
        </p>
      </div>
      {elders.length > 1 && (
        <label className="flex flex-col gap-2 text-[16px] font-semibold text-paper">
          Who is on the call?
          <select
            value={who}
            onChange={(e) => setWho(e.target.value)}
            className="min-h-[48px] max-w-sm rounded-xl border border-paper/25 bg-dusk-raised px-3 text-[17px] text-paper
                       focus-visible:outline-2 focus-visible:outline-accent"
          >
            {elders.map((e) => (
              <option key={e.id} value={e.display_name}>
                {e.display_name}
              </option>
            ))}
          </select>
        </label>
      )}
      {error && (
        <p role="alert" className="text-[17px] text-alarm-text">
          {error}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={start}
          disabled={busy}
          className="btn-accent inline-flex min-h-[56px] items-center px-7 text-[19px] disabled:opacity-60
                     focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
        >
          {busy ? 'Starting…' : who ? `Start a call for ${who}` : 'Start a call'}
        </button>
        {!deviceToken.get() && (
          <span className="text-[16px] text-mist">
            This laptop isn't paired, so the call won't be saved to history.{' '}
            <Link to="/home" className="font-semibold text-paper underline underline-offset-4">Pair it</Link>
          </span>
        )}
      </div>
    </section>
  )
}

function Running({ call, onDone }: { call: Started; onDone: () => void }) {
  const elderPath = localPath(call.elderUrl)
  // Listen as the family does, only to know when the call ends (the grandparent's button, or the server).
  const familyFeed = useMemo(() => {
    const q = new URL(call.familyUrl).searchParams
    return { kind: 'live' as const, sessionId: call.sessionId, role: 'family' as const, token: q.get('token') }
  }, [call])
  const { events, error } = useEvents(familyFeed)
  const ended = error !== null || events.some((e) => e.type === 'call_ended')
  // Refused before hearing anything: a call kept from earlier in this tab that the server no
  // longer has (it ended, or the server restarted). Drop it and offer a new call instead.
  const stale = error !== null && events.length === 0
  useEffect(() => {
    if (stale) onDone()
  }, [stale, onDone])
  const evidence = `/evidence?${new URL(call.elderUrl).searchParams}`
  const big = 'min-h-[60px] rounded-2xl px-7 text-[19px] font-semibold focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent'

  if (stale) return null
  return (
    // Breaks out of the page column, so the grandparent's screen is as big as the window allows.
    <section aria-labelledby="live-h"
             className="relative left-1/2 flex w-[min(94vw,1560px)] -translate-x-1/2 flex-col gap-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 id="live-h" className="subtitle text-[1.8rem]">{ended ? 'The call has ended' : 'Live call'}</h2>
        <p className="text-[16px] text-mist">
          {call.recorded ? 'Saved to their call history.' : 'Not saved: this laptop isn’t paired.'}
        </p>
      </div>
      <CallSides
        grandparent={
          // A smaller page than the real 1280 x 800 laptop, so at this size everything on it
          // (captions, the red button, the End call box) shows bigger.
          <ScaledFrame title="Their screen, live call" src={`${elderPath}&embed=1`}
                       width={1040} height={680} className="w-full rounded-2xl" />
        }
        family={
          <div className="flex flex-col gap-5">
            {SHOW_FAMILY_PHONE && (
              <ScaledFrame title="The family's phone, live call" src={`${localPath(call.familyUrl)}&embed=1`}
                           width={390} height={844} fit className="mx-auto w-full max-w-[360px] rounded-[2rem]" />
            )}
            {!ended ? (
              <div className="glass rounded-2xl p-5">
                <p className="mb-3 text-[16px] text-paper-dim">Scan with the family’s phone to follow this call.</p>
                <FamilyQr familyUrl={call.familyUrl} />
              </div>
            ) : (
              <p className="glass rounded-2xl p-5 text-[17px] text-paper-dim">The family link stopped working when the call ended.</p>
            )}
          </div>
        }
      />
      <div className="flex flex-wrap gap-3">
        {ended ? (
          <button type="button" onClick={onDone} className={`btn-accent ${big}`}>
            Start another call
          </button>
        ) : (
          // The link's token stops working when the call ends, like the family link.
          <Link to={evidence} className={`glass inline-flex items-center text-paper ${big}`}>
            How Aegis judged this call <span aria-hidden className="ml-2">→</span>
          </Link>
        )}
      </div>
    </section>
  )
}
