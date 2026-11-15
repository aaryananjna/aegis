import type { ReactNode } from 'react'
import { PhoneIcon, ShieldIcon } from './Icons'
import { callFamilyLine } from './state'

/**
 * The ended screen after a call that reached Warning or showed a card (#107). She is shaken right
 * now, so it says the two things to do, numbered, and nothing else. The laptop can't place a
 * call, so both steps are instructions to read, not buttons, and the screen says so. Both steps
 * get the same size, frame and icon slot so neither looks like the only one that matters.
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
      <div className="flex min-h-0 flex-1 flex-col justify-center gap-[clamp(1rem,2.5vh,2rem)] px-[clamp(1rem,5vw,6rem)] pb-[clamp(1.5rem,5vh,4rem)]">
        <p className="text-[length:clamp(30px,min(3vw,5vh),52px)] font-bold text-paper">
          What to do now (do these yourself):
        </p>
        <ol aria-label="What to do now" className="flex flex-col gap-[clamp(1.25rem,3vh,2.5rem)]">
          <Instruction
            n={1}
            icon={<PhoneIcon />}
            title={callFamilyLine(familyName)}
            detail="Tell them about this call."
          />
          <Instruction
            n={2}
            icon={<ShieldIcon />}
            title="Did you give them anything?"
            detail="Call your bank on the number on your card."
          />
        </ol>
      </div>
    </main>
  )
}

function Instruction({ n, icon, title, detail }: { n: number; icon: ReactNode; title: string; detail: string }) {
  return (
    <li className="room-reset flex items-center gap-[clamp(1.25rem,2.5vw,3rem)] rounded-3xl border-4 border-paper/25
                   bg-dusk-raised p-[clamp(1.5rem,3.5vw,4rem)] select-none">
      <Step n={n} />
      <span aria-hidden className="shrink-0 text-[length:clamp(56px,6vw,104px)] text-heading">
        {icon}
      </span>
      <span className="flex flex-col gap-2">
        <span className="text-[length:clamp(36px,min(4vw,6.6vh),76px)] leading-[1.08] font-bold text-heading">
          {title}
        </span>
        <span className="text-[length:clamp(26px,min(2.4vw,4vh),42px)] leading-[1.15] text-paper-dim">
          {detail}
        </span>
      </span>
    </li>
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
