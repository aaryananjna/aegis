import { useEffect, useMemo, useRef, type CSSProperties } from 'react'
import { useSearchParams } from 'react-router'
import { SiteNav } from '../brand/SiteNav'
import { CheckIcon, KeyIcon, PhoneDownIcon, PhoneIcon, ShieldIcon } from '../elder/Icons'
import { eventsForTap, useDemoTaps } from '../events/demoLink'
import { feedFromSearch, useEvents, type Feed } from '../events/useEvents'
import { endSummary, endTitle, initialFamilyState, reduceFamily, type FamilyAlert } from './state'

// Display only, from the link the server hands out (made up in demos). Sample calls use Rose.
const SAMPLE = { name: 'Rose', phone: '+15550100' }

const focusRing = 'focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-paper'

export function FamilyPage() {
  const [search] = useSearchParams()
  const feed = feedFromSearch(search, 'family')
  const sample = feed.kind === 'fixture'
  const name = search.get('name') || (sample ? SAMPLE.name : 'your family member')
  const phone = search.get('phone') || (sample ? SAMPLE.phone : null)
  const embedded = search.get('embed') === '1' // inside the landing page's demo: no nav
  const demo = sample ? search.get('demo') : null // taps on Grandma's screen beside it reach here
  return <FamilyWatch key={JSON.stringify(feed)} feed={feed} name={name} phone={phone} embedded={embedded} demo={demo} />
}

/**
 * The family's view of one call. `onOver` (used by /watch) hears when the call has ended or
 * its link was refused, so the page can go back to waiting for the next call.
 */
export function FamilyWatch({ feed, name, phone, embedded, demo, onOver }: {
  feed: Feed; name: string; phone: string | null; embedded: boolean; demo: string | null
  onOver?: () => void
}) {
  const { events, receivedAt, connection, error, playLocally } = useEvents(feed)
  useDemoTaps(demo, (tap) => playLocally(eventsForTap(tap, 'sample'), { stop: true }))
  const state = useMemo(
    () => events.reduce((s, e, i) => reduceFamily(s, e, receivedAt[i]), initialFamilyState),
    [events, receivedAt],
  )
  useBuzzOnNewAlert(state.alerts.length)
  useKeepScreenOn()
  const over = state.endedAt !== null || error !== null
  const reportOver = useRef(onOver)
  useEffect(() => {
    reportOver.current = onOver
  })
  useEffect(() => {
    if (over) reportOver.current?.()
  }, [over])

  useEffect(() => {
    document.title = state.alerts.length ? `Alert: ${name} may be on a scam call` : 'Aegis'
  }, [state.alerts.length, name])

  const latest = state.alerts[state.alerts.length - 1]
  const earlier = state.alerts.slice(0, -1).reverse()
  const linkProblem =
    feed.kind === 'none' ? 'This link is missing its call. Open the family link the laptop shows.' : error

  return (
    // Embedded in the landing demo the page is only as tall as what's on it; the frame grows with it.
    <main className={`mx-auto flex ${embedded ? '' : 'min-h-dvh'} max-w-xl flex-col gap-5 px-5
                     pt-[max(1.25rem,env(safe-area-inset-top))] pb-[max(1.5rem,env(safe-area-inset-bottom))]`}>
      <header className="flex flex-col gap-1">
        {!embedded && <SiteNav section="Family" />}
        <h1 className="title mt-3">Watching over {name}</h1>
        <p className="text-[17px] text-mist">
          <Connection feed={feed} connection={connection} />
        </p>
      </header>

      <section aria-live="assertive" aria-label="Alerts" className="flex flex-col gap-4">
        {linkProblem ? (
          <p className="glass rounded-2xl p-5 text-[20px] text-paper">{linkProblem}</p>
        ) : null}
        {state.endedAt !== null && (
          <div className="glass rounded-2xl p-5">
            {state.alerts.length > 0 ? (
              // After an alert, "is she OK?" comes first (#107).
              <h2 className="subtitle flex items-center gap-3">
                <span className="text-calm-text"><CheckIcon /></span>
                {endTitle(state, name)}
              </h2>
            ) : (
              <h2 className="subtitle">{endTitle(state, name)}</h2>
            )}
            <p className="mt-1 text-[19px] text-paper-dim">{endSummary(state, name)}</p>
            <p className="mt-2 text-[16px] text-mist">{clock(state.endedAt)}</p>
          </div>
        )}
        {latest ? (
          <AlertCard alert={latest} name={name} phone={phone} codewordOk={state.codewordOk} big />
        ) : (
          !linkProblem && state.endedAt === null && <AllQuiet name={name} />
        )}
      </section>

      {earlier.length > 0 && (
        <section aria-labelledby="earlier" className="flex flex-col gap-3">
          <h2 id="earlier" className="text-[17px] font-semibold text-mist">Earlier</h2>
          {earlier.map((a) => (
            <AlertCard key={a.alertId} alert={a} name={name} phone={null} codewordOk={state.codewordOk} />
          ))}
        </section>
      )}
    </main>
  )
}

const KIND = {
  codeword: {
    title: 'Possible scam call',
    told: (name: string) => `${name} was asked to check the family code word.`,
    box: 'bg-[color-mix(in_oklab,var(--color-care)_18%,var(--color-dusk))] border-care',
    icon: <KeyIcon />,
    iconColor: 'text-care-text',
  },
  verify: {
    title: 'Possible scam call',
    told: (name: string) => `${name} was told not to pay or share any numbers.`,
    box: 'bg-[color-mix(in_oklab,var(--color-care)_18%,var(--color-dusk))] border-care',
    icon: <ShieldIcon />,
    iconColor: 'text-care-text',
  },
  hangup: {
    title: 'Likely scam call',
    told: (name: string) => `${name} was told to hang up.`,
    box: 'bg-alarm-deep border-alarm',
    icon: <PhoneDownIcon />,
    iconColor: 'text-white',
  },
} as const

export function AlertCard({
  alert,
  name,
  phone,
  codewordOk,
  big = false,
}: {
  alert: FamilyAlert
  name: string
  phone: string | null
  codewordOk: boolean
  big?: boolean
}) {
  const k = KIND[alert.kind]
  const passed = alert.kind === 'codeword' && codewordOk
  const Heading = big ? 'h2' : 'h3' // cards under "Earlier" sit one level below it
  return (
    <article
      className={`flex flex-col gap-3 rounded-2xl border-2 ${big ? 'p-5' : 'p-4 opacity-90'} ${k.box}`}
      // The red card keeps white text in both themes (8.9:1 on red; 6.8:1 for the 85% lines).
      style={alert.kind === 'hangup' ? ({ '--color-paper': '#ffffff', '--color-paper-dim': 'rgba(255,255,255,0.85)' } as CSSProperties) : undefined}
    >
      <div className="flex items-start gap-3">
        <span className={`mt-1 shrink-0 ${big ? 'text-[34px]' : 'text-[26px]'} ${k.iconColor}`}>{k.icon}</span>
        <div className="flex flex-col gap-1">
          <Heading className={`${big ? 'text-[28px]' : 'text-[22px]'} leading-tight font-semibold text-paper`}>
            {k.title}
          </Heading>
          <p className="text-[16px] text-paper-dim">
            {clock(alert.receivedAt)} · {k.told(name)}
          </p>
        </div>
      </div>
      {passed && (
        <p className="flex items-center gap-2 rounded-xl bg-calm/20 px-3 py-2 text-[20px] font-semibold text-paper">
          <span className="text-calm-text">
            <CheckIcon />
          </span>
          They passed the code word
        </p>
      )}
      {big && (
        <>
          <p className="text-[20px] leading-snug text-paper">{alert.summary}</p>
          {alert.quotes.length > 0 && (
            <figure className="flex flex-col gap-2">
              <figcaption className="text-[16px] font-semibold text-paper-dim">What the caller said</figcaption>
              {alert.quotes.map((q) => (
                <blockquote key={q} className="border-l-4 border-paper/40 pl-3 text-[20px] text-paper">
                  “{q}”
                </blockquote>
              ))}
            </figure>
          )}
          {phone && (
            <a
              href={`tel:${phone}`}
              className={`btn-accent mt-1 flex min-h-[64px] items-center justify-center gap-3 text-[22px] ${focusRing}`}
            >
              <PhoneIcon />
              Call {name}
            </a>
          )}
        </>
      )}
    </article>
  )
}

function AllQuiet({ name }: { name: string }) {
  return (
    <div className="glass flex flex-col items-start gap-3 rounded-2xl p-6">
      <span className="text-[44px] text-calm-text">
        <CheckIcon />
      </span>
      <h2 className="subtitle text-[1.5rem]">All quiet</h2>
      <p className="text-[19px] text-paper-dim">
        If a call to {name} looks like a scam, you'll see it here with the caller's exact words.
        Keep this page open.
      </p>
    </div>
  )
}

function Connection({ feed, connection }: { feed: Feed; connection: string }) {
  if (feed.kind === 'fixture') return <>Sample call, not live</>
  if (feed.kind === 'none') return <>Not connected</>
  const words: Record<string, string> = {
    connecting: 'Connecting…',
    open: 'Connected',
    reconnecting: 'Reconnecting…',
    ended: 'Call over',
    error: 'Not connected',
  }
  return <>{words[connection] ?? 'Connecting…'}</>
}

export function clock(ms: number): string {
  return new Date(ms).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

/** Buzz once per new alert. Phones that can't vibrate (iPhone Safari) just skip it. */
function useBuzzOnNewAlert(count: number) {
  const seen = useRef(0)
  useEffect(() => {
    if (count > seen.current) {
      try {
        navigator.vibrate?.([300, 150, 300])
      } catch {
        // not allowed here: the card itself is the alert
      }
    }
    seen.current = count
  }, [count])
}

/** Keep the phone awake while watching, so the page doesn't sleep and drop the connection. */
export function useKeepScreenOn() {
  useEffect(() => {
    let lock: { release: () => Promise<void> } | null = null
    const request = async () => {
      try {
        lock = (await (navigator as Navigator & {
          wakeLock?: { request: (t: 'screen') => Promise<{ release: () => Promise<void> }> }
        }).wakeLock?.request('screen')) ?? null
      } catch {
        // not supported or not allowed: the page still works, the phone may just sleep
      }
    }
    const onVisible = () => document.visibilityState === 'visible' && request()
    request()
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      document.removeEventListener('visibilitychange', onVisible)
      lock?.release().catch(() => {})
    }
  }, [])
}
