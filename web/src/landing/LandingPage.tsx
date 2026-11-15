import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { useAuth } from '../accounts/auth'
import { LiveCall } from '../live/LiveCall'
import { AegisWordmark } from '../brand/AegisWordmark'
import { SiteNav } from '../brand/SiteNav'
import { CallSides } from './CallSides'
import { ScaledFrame } from './ScaledFrame'

const STEPS = [
  {
    title: 'Captions they can read',
    body: 'Every word of the call shows up on the laptop in large type as it’s spoken, so a quiet or fast caller is easy to follow.',
  },
  {
    title: 'Listens for the script, not the voice',
    body: 'Scammers follow the same playbook: pretend to be family or the bank, invent an emergency, ask for secrecy, then gift cards or a transfer. Aegis flags those moves, so a cloned voice doesn’t get past it.',
  },
  {
    title: 'One step for them, an alert for you',
    body: 'The grandparent gets a single instruction, like asking for the family code word or hanging up. The family’s phone gets an alert quoting what the caller said.',
  },
]

// What it runs on. Plain text on purpose: judges asked, and it should be checkable.
const STACK = [
  ['Speech to text', 'Deepgram Nova-3, streamed from the laptop microphone'],
  ['Scam detection', 'Python rules for 8 scam tactics and a running risk score, plus an AI check alongside them (Groq, with Google Gemini as backup)'],
  ['Server', 'Python, FastAPI and WebSockets'],
  ['Accounts and call history', 'TigerDB (PostgreSQL), passwords hashed with Argon2'],
  ['Screens', 'React, TypeScript, Vite and Tailwind CSS'],
  ['Family phone link', 'Cloudflare Tunnel'],
] as const

const linkClass =
  'glass rounded-2xl px-5 py-4 text-[18px] font-semibold text-paper focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent'

/**
 * "/": open to everyone. Logged out: what Aegis does and the recorded demo call, with Log in
 * up top. Logged in: no demo; start a live call and watch its captions here, plus Evidence.
 */
export function LandingPage() {
  const { auth } = useAuth()
  const loggedIn = auth.status === 'in'
  // The demo plays right here: nothing loads until "Watch a demo call", and Restart replays it.
  const [run, setRun] = useState(0)
  // Ties this run's two screens together (a tap on the grandparent's reaches the phone), per page load.
  const [demoId] = useState(() => Math.random().toString(36).slice(2, 10))
  const demo = useRef<HTMLElement>(null)
  const start = () => {
    setRun((n) => n + 1)
    requestAnimationFrame(() => demo.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  return (
    <main className="mx-auto flex min-h-dvh max-w-6xl flex-col gap-14 px-[5vw] py-10">
      <SiteNav brand={false} />

      <section className="flex max-w-4xl flex-col gap-6">
        <h1>
          <AegisWordmark size="hero" />
        </h1>
        <p className="font-display text-[length:clamp(1.75rem,3.2vw,2.75rem)] leading-tight font-bold text-heading">
          Real-time scam alerts for every call.
        </p>
        <p className="max-w-2xl text-[21px] leading-relaxed text-paper-dim">
          Aegis sits next to a grandparent’s phone while it’s on speaker. It turns the call into
          big captions and listens for the moves scammers use: a family emergency, a rush, a
          secret, a gift card. When it hears them, it tells the grandparent what to do and alerts
          the family.
        </p>
        {!loggedIn && (
        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={start}
            className="btn-accent inline-flex min-h-[56px] items-center px-7 text-[19px]
                       focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
          >
            {run ? 'Restart the demo' : 'Watch a demo call'}
          </button>
          <span className="text-[16px] text-mist">A recorded sample call, not live.</span>
        </div>
        )}
      </section>

      {loggedIn && <LiveCall />}

      {!loggedIn && run > 0 && (
        <section ref={demo} aria-labelledby="demo-h" className="flex scroll-mt-6 flex-col gap-4">
          <div className="flex flex-col gap-1">
            <h2 id="demo-h" className="subtitle text-[1.6rem]">The demo call</h2>
            <p className="text-[16px] text-mist">A recorded sample, not live: a fake grandson asks for bail money.</p>
          </div>
          <CallSides
            grandparent={
              <ScaledFrame
                key={`elder-${run}`}
                title="The grandparent's screen, demo call"
                src={`/elder?fixture=scam-grandson-ai&embed=1&demo=${demoId}-${run}`}
                width={1280}
                height={800}
                className="w-full rounded-2xl"
              />
            }
            family={
              <ScaledFrame
                key={`family-${run}`}
                title="The family's phone, demo call"
                src={`/family?fixture=scam-grandson-ai&embed=1&demo=${demoId}-${run}`}
                width={390}
                height={844}
                fit
                className="mx-auto w-full max-w-[380px] rounded-[2rem]"
              />
            }
          />
        </section>
      )}

      <section aria-labelledby="how-h" className="flex flex-col gap-5">
        <h2 id="how-h" className="text-[15px] font-semibold tracking-[0.12em] text-heading uppercase">
          How it works
        </h2>
        <ul className="grid gap-5 md:grid-cols-3">
          {STEPS.map((s) => (
            <li key={s.title} className="glass flex flex-col gap-2 rounded-2xl p-6">
              <h3 className="subtitle">{s.title}</h3>
              <p className="text-[17px] leading-relaxed text-paper-dim">{s.body}</p>
            </li>
          ))}
        </ul>
        <div className="glass flex flex-col gap-4 rounded-2xl p-6">
          <h3 className="subtitle">Tech stack</h3>
          <dl className="grid gap-x-8 gap-y-3 sm:grid-cols-[max-content_1fr]">
            {STACK.map(([what, how]) => (
              <div key={what} className="contents">
                <dt className="text-[16px] font-semibold text-paper">{what}</dt>
                <dd className="text-[16px] text-paper-dim">{how}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {loggedIn && (
        <nav aria-label="Other screens" className="flex flex-wrap gap-4">
          <Link to="/evidence?fixture=scam-grandson-ai" className={linkClass}>
            Evidence for judges <span aria-hidden>→</span>
          </Link>
        </nav>
      )}
    </main>
  )
}
