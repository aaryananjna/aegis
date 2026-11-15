import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { AegisWordmark } from '../brand/AegisWordmark'
import { SiteNav } from '../brand/SiteNav'
import { ScaledFrame } from './ScaledFrame'

const STEPS = [
  {
    title: 'Huge live captions',
    body: 'The call on speaker becomes large, clear text on the laptop beside the phone, for every call.',
  },
  {
    title: 'Reads the scam, not the voice',
    body: 'It watches what the caller does: pretending to be family, rushing, asking for secrecy or gift cards. A perfect voice clone doesn’t fool it.',
  },
  {
    title: 'One calm step, and family knows',
    body: 'Grandma sees one plain instruction. Family get an alert on their phone with the caller’s exact words.',
  },
]

const linkClass =
  'glass rounded-2xl px-5 py-4 text-[18px] font-semibold text-paper focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent'

/** "/": what Aegis does, and a way into the demo. */
export function LandingPage() {
  // The demo plays right here: nothing loads until "Watch a demo call", and Restart replays it.
  const [run, setRun] = useState(0)
  // Ties this run's two screens together (a tap on Grandma's reaches the phone), per page load.
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
          Scam calls, caught by what they say.
        </p>
        <p className="max-w-2xl text-[21px] leading-relaxed text-paper-dim">
          Aegis sits beside a grandparent’s phone on speaker. It captions the call, spots the
          moves scammers make, tells Grandma one calm thing to do, and alerts the family.
        </p>
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
      </section>

      {run > 0 && (
        <section ref={demo} aria-labelledby="demo-h" className="flex scroll-mt-6 flex-col gap-4">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 id="demo-h" className="subtitle text-[1.6rem]">The demo call</h2>
            <p className="text-[16px] text-mist">
              A recorded sample: a fake grandson asks for bail money. Left: Grandma’s laptop. Right: the family’s phone.
            </p>
          </div>
          <div className="grid items-start gap-5 lg:grid-cols-[1fr_360px]">
            <ScaledFrame
              key={`elder-${run}`}
              title="Grandma's screen, demo call"
              src={`/elder?fixture=scam-grandson&embed=1&demo=${demoId}-${run}`}
              width={1280}
              height={800}
              className="w-full rounded-2xl"
            />
            <ScaledFrame
              key={`family-${run}`}
              title="Family phone, demo call"
              src={`/family?fixture=scam-grandson&embed=1&demo=${demoId}-${run}`}
              width={390}
              height={844}
              fit
              className="mx-auto w-full max-w-[360px] rounded-[2rem]"
            />
          </div>
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
      </section>

      <nav aria-label="Other screens" className="flex flex-wrap gap-4">
        <Link to="/evidence?fixture=scam-grandson" className={linkClass}>
          Evidence for judges <span aria-hidden>→</span>
        </Link>
      </nav>
    </main>
  )
}
