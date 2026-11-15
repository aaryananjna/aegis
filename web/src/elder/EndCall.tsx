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
        className="m-auto w-[min(90vw,34rem)] rounded-3xl border border-[var(--glass-border-hot)]
                   bg-dusk-raised p-0 text-paper shadow-[0_24px_60px_-20px_rgba(0,0,0,0.6)]
                   backdrop:bg-black/55 backdrop:backdrop-blur-sm"
      >
        <div className="flex flex-col items-center gap-5 px-8 pt-8 pb-7 text-center">
          <span className="grid size-14 place-items-center rounded-full bg-accent/12 text-[28px] text-heading ring-1 ring-accent/30">
            <PhoneDownIcon />
          </span>
          <div className="flex flex-col gap-2">
            <h2 id="end-title" className="font-display text-[length:clamp(26px,2.2vw,32px)] leading-tight font-bold text-balance">
              Are you sure this call is over?
            </h2>
            {hangupShowing && (
              <p id="end-note" className="text-[length:clamp(19px,1.5vw,22px)] text-paper-dim">
                Did you hang up on them? Good.
              </p>
            )}
          </div>
          <div className="grid w-full gap-3 sm:grid-cols-2">
            <button
              ref={no}
              type="button"
              autoFocus
              onClick={close}
              className={`btn-accent min-h-[60px] rounded-2xl px-4 text-[length:clamp(19px,1.5vw,22px)] font-semibold ${focusRing}`}
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
              className={`min-h-[60px] rounded-2xl border-2 border-paper/35 px-4 text-[length:clamp(19px,1.5vw,22px)]
                          font-semibold text-paper hover:border-paper/70 hover:bg-paper/5 motion-safe:transition-colors ${focusRing}`}
            >
              Yes, the call is over
            </button>
          </div>
        </div>
      </dialog>
    </>
  )
}
