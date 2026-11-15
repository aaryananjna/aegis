import type { ReactNode } from 'react'
import { PhoneIcon } from './Icons'
import { callFamilyLine } from './state'

/**
 * The ended screen after a call that reached Warning or showed a card (#107). She is shaken right
 * now, so it says the two things to do, numbered, and nothing else. The laptop can't place a
 * call, so step 1 is a big instruction, not a button.
 */
export function AfterCall({ familyName, brand, sample }: { familyName: string | null; brand: ReactNode; sample: boolean }) {
  return (
    <main className="flex h-dvh flex-col overflow-hidden bg-dusk text-paper">
      <h1 className="sr-only">Call ended</h1>
      <div className="flex items-center justify-between gap-8 px-[clamp(1rem,3vw,3rem)] py-[clamp(1rem,2.5vh,2rem)]">
        <p className="text-[length:clamp(26px,2.2vw,36px)] font-semibold text-mist">
          Call ended{sample && <span className="ml-4 text-[0.6em] font-medium">Sample call</span>}
        </p>
        {brand}
      </div>
      <ol
        aria-label="What to do now"
        className="flex min-h-0 flex-1 flex-col justify-center gap-[clamp(1.25rem,3vh,2.5rem)] px-[clamp(1rem,5vw,6rem)] pb-[clamp(1.5rem,5vh,4rem)]"
      >
        <li className="room-reset flex items-center gap-[clamp(1.25rem,2.5vw,3rem)] rounded-3xl border-4 border-calm
                       bg-[color-mix(in_oklab,var(--color-calm)_14%,var(--color-dusk-raised))] p-[clamp(1.5rem,3.5vw,4rem)]">
          <Step n={1} />
          <span aria-hidden className="shrink-0 text-[length:clamp(56px,6vw,104px)] text-calm-text">
            <PhoneIcon />
          </span>
          <span className="flex flex-col gap-2">
            <span className="text-[length:clamp(44px,min(5.6vw,9vh),104px)] leading-[1.05] font-bold text-heading">
              {callFamilyLine(familyName)}
            </span>
            <span className="text-[length:clamp(26px,min(2.4vw,4vh),42px)] text-paper-dim">
              Tell them about this call.
            </span>
          </span>
        </li>
        <li className="room-reset flex items-center gap-[clamp(1.25rem,2.5vw,3rem)] rounded-3xl bg-dusk-raised p-[clamp(1.5rem,3.5vw,4rem)]">
          <Step n={2} />
          <span className="flex flex-col gap-2">
            <span className="text-[length:clamp(32px,min(3.4vw,5.6vh),64px)] leading-[1.1] font-semibold text-paper">
              Did you give them anything?
            </span>
            <span className="text-[length:clamp(26px,min(2.6vw,4.4vh),48px)] leading-[1.15] text-paper-dim">
              Call your bank on the number on your card.
            </span>
          </span>
        </li>
      </ol>
    </main>
  )
}

function Step({ n }: { n: number }) {
  return (
    <span
      aria-label={`Step ${n}`}
      className="grid size-[clamp(56px,5vw,96px)] shrink-0 place-items-center rounded-full border-4 border-paper/40
                 text-[length:clamp(30px,2.8vw,52px)] font-bold text-paper"
    >
      {n}
    </span>
  )
}
