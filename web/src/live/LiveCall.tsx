import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { ApiError, api, deviceToken, type ElderRef, type User } from '../accounts/api'
import { useEvents } from '../events/useEvents'
import { ScaledFrame } from '../landing/ScaledFrame'
import { FamilyQr } from './FamilyQr'
import { localPath, savedFamilyUrl } from './familyLink'

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
 * The logged-in front page (#63): start a live call from here, then watch Grandma's live
 * captions right on this page, with the family link as a QR code beside them. The server
 * listens on the laptop mic (`mic: true`) with speaker labels off, as in the demo setup.
 */
export function LiveCall() {
  const navigate = useNavigate()
  const [elders, setElders] = useState<ElderRef[]>([])
  const [who, setWho] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [call, setCallState] = useState<Started | null>(() => savedCall.get())
  const setCall = (c: Started | null) => {
    savedCall.set(c)
    setCallState(c)
  }

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

  if (call) return <Running call={call} onDone={() => setCall(null)} onFullScreen={() => navigate(localPath(call.elderUrl))} />

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

function Running({ call, onDone, onFullScreen }: { call: Started; onDone: () => void; onFullScreen: () => void }) {
  const elderPath = localPath(call.elderUrl)
  const embedPath = `${elderPath}&embed=1`
  // Listen as the family does, only to know when the call ends (Grandma's End call, or the server).
  const familyFeed = useMemo(() => {
    const q = new URL(call.familyUrl).searchParams
    return { kind: 'live' as const, sessionId: call.sessionId, role: 'family' as const, token: q.get('token') }
  }, [call])
  const { events, error } = useEvents(familyFeed)
  // A refused link (error) means the server no longer has this call, e.g. it restarted.
  const ended = error !== null || events.some((e) => e.type === 'call_ended')
  const evidence = `/evidence?${new URL(call.elderUrl).searchParams}`

  return (
    <section aria-labelledby="live-h" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 id="live-h" className="subtitle text-[1.6rem]">{ended ? 'The call has ended' : 'Live call'}</h2>
        <p className="text-[16px] text-mist">
          {call.recorded ? 'Saved to the grandparent’s history.' : 'Not saved: this laptop isn’t paired.'}
        </p>
      </div>
      <div className="grid items-start gap-5 lg:grid-cols-[1fr_300px]">
        <ScaledFrame title="Grandma's screen, live call" src={embedPath} width={1280} height={800} className="w-full rounded-2xl" />
        <aside aria-labelledby="fam-h" className="glass flex flex-col gap-4 rounded-2xl p-5">
          <h3 id="fam-h" className="subtitle">Family phone</h3>
          {ended ? (
            <p className="text-[17px] text-paper-dim">The family link stopped working when the call ended.</p>
          ) : (
            <>
              <p className="text-[16px] text-paper-dim">Scan to follow this call and get alerts.</p>
              <FamilyQr familyUrl={call.familyUrl} />
            </>
          )}
        </aside>
      </div>
      <div className="flex flex-wrap gap-3">
        {ended ? (
          <button type="button" onClick={onDone}
                  className="btn-accent min-h-[52px] px-6 text-[18px] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent">
            Start another call
          </button>
        ) : (
          <button type="button" onClick={onFullScreen}
                  className="glass min-h-[52px] rounded-2xl px-6 text-[18px] font-semibold text-paper focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent">
            Open Grandma's screen full size
          </button>
        )}
        {!ended && (
  // The link's token stops working when the call ends, like the family link.
        <Link to={evidence}
              className="glass inline-flex min-h-[52px] items-center rounded-2xl px-6 text-[18px] font-semibold text-paper focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent">
          How Aegis judged this call <span aria-hidden className="ml-2">→</span>
        </Link>
)}
      </div>
    </section>
  )
}
