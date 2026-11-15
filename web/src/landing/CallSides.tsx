import type { ReactNode } from 'react'

/**
 * The two sides of a call, side by side and labelled so nobody mixes them up: what the
 * grandparent sees on the laptop, and what the family gets on their phone, which the
 * grandparent never sees. Used by the demo and by a live call.
 */
export function CallSides({ grandparent, family }: { grandparent: ReactNode; family: ReactNode }) {
  return (
    <div className="grid items-start gap-6 lg:grid-cols-[1fr_360px]">
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <h3 className="subtitle text-[1.4rem]">The grandparent’s screen</h3>
          <p className="text-[16px] text-mist">On the laptop next to the phone. This is all they see.</p>
        </div>
        {grandparent}
      </div>
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-1">
          <h3 className="subtitle text-[1.4rem]">The family’s phone</h3>
          <p className="text-[16px] text-mist">
            <span className="font-semibold text-paper">The grandparent can’t see this.</span> It runs in the
            background, and when Aegis spots a scam it sends an alert to their phone.
          </p>
        </div>
        {family}
      </div>
    </div>
  )
}
