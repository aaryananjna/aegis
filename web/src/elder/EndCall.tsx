import { useRef, type KeyboardEvent, type MouseEvent } from 'react'
import { PhoneDownIcon } from './Icons'
import { focusRing } from './VoicePicker'

/**
 * "End call" on the elder screen (#42). Ending is final (links die, history is deleted), so it
 * always asks first. "No, keep listening" is the default and focused; Escape or a tap outside
 * the box also means no. Only "Yes" calls onEnd, which sends {"type": "end"}.
 */
export function EndCall({ onEnd, hangupShowing }: { onEnd: () => void; hangupShowing: boolean }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const no = useRef<HTMLButtonElement>(null)
  const yes = useRef<HTMLButtonElement>(null)

  const open = () => {
    dialog.current?.showModal()
    no.current?.focus()
  }
  const close = () => dialog.current?.close()

  // Keep Tab inside the box: it only ever moves between the two answers.
  const trap = (e: KeyboardEvent<HTMLDialogElement>) => {
    if (e.key !== 'Tab') return
    e.preventDefault()
    ;(document.activeElement === no.current ? yes : no).current?.focus()
  }
  // A tap on the dimmed area outside the box (the dialog element itself) counts as "No".
  const outside = (e: MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialog.current) close()
  }

  return (
    <>
      <button
        type="button"
        onClick={open}
        className={`min-h-[48px] rounded-xl border-2 border-paper/30 px-5 text-[length:clamp(18px,1.4vw,22px)]
                    font-semibold text-paper hover:border-paper/60 ${focusRing}`}
      >
        End call
      </button>
      <dialog
        ref={dialog}
        onKeyDown={trap}
        onClick={outside}
        aria-labelledby="end-title"
        aria-describedby={hangupShowing ? 'end-note' : undefined}
        className="m-auto w-[min(90vw,60rem)] overflow-hidden rounded-[2rem] border border-[var(--glass-border-hot)]
                   bg-dusk-raised p-0 text-paper shadow-[0_30px_80px_-20px_rgba(0,0,0,0.6)]
                   backdrop:bg-black/55 backdrop:backdrop-blur-sm"
      >
        <div className="flex flex-col items-center gap-8 px-[clamp(1.75rem,4.5vw,4rem)] pt-[clamp(2rem,4.5vw,3.5rem)] pb-[clamp(1.75rem,4vw,3.25rem)] text-center">
          <span className="grid size-[clamp(72px,6.5vw,104px)] place-items-center rounded-full bg-accent/12
                           text-[length:clamp(36px,3.4vw,52px)] text-heading ring-1 ring-accent/30">
            <PhoneDownIcon />
          </span>
          <div className="flex flex-col gap-3">
            <h2 id="end-title" className="font-display text-[length:clamp(40px,4.2vw,64px)] leading-[1.08] font-semibold tracking-[-0.01em] text-balance">
              Are you sure this call is over?
            </h2>
            {hangupShowing && (
              <p id="end-note" className="font-display text-[length:clamp(26px,2.5vw,36px)] text-paper-dim italic">
                Did you hang up on them? Good.
              </p>
            )}
          </div>
          <div className="grid w-full gap-4 sm:grid-cols-2">
            <button
              ref={no}
              type="button"
              autoFocus
              onClick={close}
              className={`btn-accent min-h-[clamp(80px,11vh,112px)] rounded-2xl px-5
                          font-display text-[length:clamp(26px,2.6vw,38px)] font-semibold ${focusRing}`}
            >
              No, keep listening
            </button>
            <button
              ref={yes}
              type="button"
              onClick={() => {
                close()
                onEnd()
              }}
              className={`min-h-[clamp(80px,11vh,112px)] rounded-2xl border-2 border-paper/35 px-5
                          font-display text-[length:clamp(26px,2.6vw,38px)] font-semibold text-paper
                          hover:border-paper/70 hover:bg-paper/5 motion-safe:transition-colors ${focusRing}`}
            >
              Yes, the call is over
            </button>
          </div>
        </div>
      </dialog>
    </>
  )
}
