import { useRef } from 'react'
import { FamilyQr } from '../live/FamilyQr'
import { focusRing } from './VoicePicker'

/** "Family link" on Grandma's full-size screen: the link as a QR code for the phone (#63). */
export function FamilyLinkButton({ familyUrl }: { familyUrl: string }) {
  const dialog = useRef<HTMLDialogElement>(null)
  return (
    <>
      <button
        type="button"
        onClick={() => dialog.current?.showModal()}
        className={`min-h-[48px] rounded-xl border-2 border-paper/30 px-5 text-[length:clamp(18px,1.4vw,22px)]
                    font-semibold text-paper hover:border-paper/60 ${focusRing}`}
      >
        Family link
      </button>
      <dialog
        ref={dialog}
        onClick={(e) => e.target === dialog.current && dialog.current?.close()}
        aria-labelledby="fam-link-title"
        className="m-auto w-[min(90vw,26rem)] rounded-3xl border border-[var(--glass-border-hot)] bg-dusk-raised p-0
                   text-paper backdrop:bg-black/55 backdrop:backdrop-blur-sm"
      >
        <div className="flex flex-col gap-4 p-7">
          <h2 id="fam-link-title" className="font-display text-[26px] leading-tight font-bold">Family phone</h2>
          <p className="text-[17px] text-paper-dim">Scan to follow this call and get alerts.</p>
          <FamilyQr familyUrl={familyUrl} />
          <button
            type="button"
            autoFocus
            onClick={() => dialog.current?.close()}
            className={`btn-accent min-h-[52px] text-[18px] ${focusRing}`}
          >
            Done
          </button>
        </div>
      </dialog>
    </>
  )
}
