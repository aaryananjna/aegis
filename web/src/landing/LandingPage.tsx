import { Link } from 'react-router'
import { Wordmark } from '../brand/Wordmark'

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
  return (
    <main className="mx-auto flex min-h-dvh max-w-6xl flex-col gap-14 px-[5vw] py-10">
      <header>
        <Wordmark className="text-[28px]" />
      </header>

      <section className="flex max-w-4xl flex-col gap-6">
        <h1 className="title text-paper">Scam calls, caught by what they say.</h1>
        <p className="max-w-2xl text-[21px] leading-relaxed text-paper-dim">
          Aegis sits beside a grandparent’s phone on speaker. It captions the call, spots the
          moves scammers make, tells Grandma one calm thing to do, and alerts the family.
        </p>
        <div className="flex flex-wrap items-center gap-4">
          <Link
            to="/elder?fixture=scam-grandson"
            className="btn-accent inline-flex min-h-[56px] items-center px-7 text-[19px]
                       focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
          >
            Watch a demo call
          </Link>
          <span className="text-[16px] text-mist">A recorded sample call, not live.</span>
        </div>
      </section>

      <section aria-labelledby="how-h" className="flex flex-col gap-5">
        <h2 id="how-h" className="text-[15px] font-semibold tracking-[0.12em] text-accent uppercase">
          How it works
        </h2>
        <ul className="grid gap-5 md:grid-cols-3">
          {STEPS.map((s) => (
            <li key={s.title} className="glass flex flex-col gap-2 rounded-2xl p-6">
              <h3 className="text-[21px] font-bold text-paper">{s.title}</h3>
              <p className="text-[17px] leading-relaxed text-paper-dim">{s.body}</p>
            </li>
          ))}
        </ul>
      </section>

      <nav aria-label="Other screens" className="flex flex-wrap gap-4">
        <Link to="/family?fixture=scam-grandson" className={linkClass}>
          Family phone view <span aria-hidden>→</span>
        </Link>
        <Link to="/evidence?fixture=scam-grandson" className={linkClass}>
          Evidence for judges <span aria-hidden>→</span>
        </Link>
      </nav>
    </main>
  )
}
