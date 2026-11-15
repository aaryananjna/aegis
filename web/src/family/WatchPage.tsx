import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { ApiError, api, type ElderRef, type User } from '../accounts/api'
import { useAuth } from '../accounts/auth'
import { SiteNav } from '../brand/SiteNav'
import { CheckIcon } from '../elder/Icons'
import { FamilyWatch, clock, useKeepScreenOn } from './FamilyPage'

/** How often the phone asks whether a call has started (#94). */
const POLL_MS = 3000
const PICK_KEY = 'aegis_watch_elder'

type Live = { session_id: string; family_token: string; started_at: string }

const remembered = {
  get(): string | null {
    try {
      return localStorage.getItem(PICK_KEY)
    } catch {
      return null
    }
  },
  set(id: string) {
    try {
      localStorage.setItem(PICK_KEY, id)
    } catch {
      // not saved: the phone asks again next time
    }
  },
}

/**
 * /watch on the family's phone (#94): log in once, keep the page open, and the grandparent's
 * calls show up by themselves. It asks GET /elders/{id}/live every 3 s; when a call is live it
 * shows the normal family view, and when the call ends it goes back to waiting.
 * Behind the login (App.tsx), so a logged-out phone goes to /account and comes back here.
 */
export function WatchPage() {
  const [elders, setElders] = useState<ElderRef[] | null>(null)
  const [elderId, setElderId] = useState<string | null>(null)
  const [problem, setProblem] = useState<string | null>(null)
  const { refresh } = useAuth()

  useEffect(() => {
    api<{ user: User; elders: ElderRef[] }>('GET', '/auth/me')
      .then((r) => {
        setElders(r.elders)
        const saved = remembered.get()
        const pick = r.elders.find((e) => e.id === saved) ?? (r.elders.length === 1 ? r.elders[0] : null)
        if (pick) setElderId(pick.id)
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) refresh() // login gone: back to /account
        else setProblem("Can't reach Aegis right now. Check the connection and reload.")
      })
  }, [refresh])

  const elder = elders?.find((e) => e.id === elderId) ?? null
  const choose = (id: string) => {
    remembered.set(id)
    setElderId(id)
  }

  if (elder) return <Watching key={elder.id} elder={elder} onSwitch={elders && elders.length > 1 ? () => setElderId(null) : null} />

  return (
    <Shell>
      <h1 className="title mt-3">Watch over a call</h1>
      {problem && <p role="alert" className="glass rounded-2xl p-5 text-[19px] text-paper">{problem}</p>}
      {elders && elders.length === 0 && (
        <p className="glass rounded-2xl p-5 text-[19px] text-paper-dim">
          No grandparent on your account yet.{' '}
          <Link to="/home" className="font-semibold text-paper underline underline-offset-4">Add one in My family</Link>,
          or ask the person who added them to invite you.
        </p>
      )}
      {elders && elders.length > 1 && (
        <section aria-labelledby="pick-h" className="flex flex-col gap-3">
          <h2 id="pick-h" className="subtitle">Who are you watching over?</h2>
          {elders.map((e) => (
            <button
              key={e.id}
              type="button"
              onClick={() => choose(e.id)}
              className="glass min-h-[64px] rounded-2xl px-5 text-left text-[21px] font-semibold text-paper
                         focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
            >
              {e.display_name}
            </button>
          ))}
        </section>
      )}
    </Shell>
  )
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col gap-5 px-5
                     pt-[max(1.25rem,env(safe-area-inset-top))] pb-[max(1.5rem,env(safe-area-inset-bottom))]">
      <SiteNav section="Family" />
      {children}
    </main>
  )
}

function Watching({ elder, onSwitch }: { elder: ElderRef; onSwitch: (() => void) | null }) {
  const [live, setLive] = useState<Live | null>(null)
  const [offline, setOffline] = useState(false)
  const [lastEnded, setLastEnded] = useState<number | null>(null)
  const [denied, setDenied] = useState(false)
  const done = useRef(new Set<string>()) // calls that already ended here: never reopen them
  const { refresh } = useAuth()
  useKeepScreenOn()

  const check = useCallback(async () => {
    try {
      const r = await api<{ live: Live | null }>('GET', `/elders/${encodeURIComponent(elder.id)}/live`)
      setOffline(false)
      const next = r.live && !done.current.has(r.live.session_id) ? r.live : null
      setLive((cur) => (cur && next && cur.session_id === next.session_id ? cur : next))
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return refresh() // login gone: back to /account
      if (e instanceof ApiError && (e.status === 403 || e.status === 404)) return setDenied(true)
      setOffline(true) // network or server: keep trying
    }
  }, [elder.id, refresh])

  // Ask only while waiting; during a call the event stream says when it's over.
  useEffect(() => {
    if (live || denied) return
    check()
    const id = window.setInterval(check, POLL_MS)
    const onVisible = () => document.visibilityState === 'visible' && check()
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.clearInterval(id)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [live, denied, check])

  const over = useCallback(() => {
    setLive((cur) => {
      if (cur) done.current.add(cur.session_id)
      return null
    })
    setLastEnded(Date.now())
  }, [])

  if (live) {
    return (
      <FamilyWatch
        key={live.session_id}
        feed={{ kind: 'live', sessionId: live.session_id, role: 'family', token: live.family_token }}
        name={elder.display_name}
        phone={null}
        embedded={false}
        demo={null}
        onOver={over}
      />
    )
  }

  return (
    <Shell>
      <header className="flex flex-col gap-1">
        <h1 className="title mt-3">Watching over {elder.display_name}</h1>
        <p className="text-[17px] text-mist">
          {denied ? 'Not available' : offline ? 'Reconnecting…' : 'No call right now'}
        </p>
      </header>
      {denied ? (
        <p role="alert" className="glass rounded-2xl p-5 text-[19px] text-paper">
          Your account can't watch over {elder.display_name} any more. Ask the person who added them.
        </p>
      ) : (
        <div className="glass flex flex-col items-start gap-3 rounded-2xl p-6">
          <span className="text-[44px] text-calm-text">
            <CheckIcon />
          </span>
          <h2 className="subtitle text-[1.5rem]">Waiting for a call</h2>
          <p className="text-[19px] text-paper-dim">
            When {elder.display_name}'s next call starts on their laptop, it shows up here by itself.
            Keep this page open.
          </p>
          {lastEnded !== null && <p className="text-[16px] text-mist">Last call ended at {clock(lastEnded)}.</p>}
        </div>
      )}
      {onSwitch && (
        <button
          type="button"
          onClick={onSwitch}
          className="self-start text-[17px] font-semibold text-paper underline underline-offset-4
                     focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
        >
          Watch over someone else
        </button>
      )}
    </Shell>
  )
}
