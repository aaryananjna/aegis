import { useRef, type KeyboardEvent, type MouseEvent } from 'react'
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
        className="m-auto w-[min(90vw,44rem)] rounded-3xl border-2 border-paper/20 bg-dusk-raised p-0 text-paper
                   backdrop:bg-black/60"
      >
        <div className="flex flex-col gap-6 p-[clamp(1.5rem,3vw,2.5rem)]">
          <h2 id="end-title" className="text-[length:clamp(30px,2.8vw,42px)] leading-tight font-semibold">
            Are you sure this call is over?
          </h2>
          {hangupShowing && (
            <p className="text-[length:clamp(22px,1.8vw,28px)] text-paper-dim">Did you hang up on them? Good.</p>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <button
              ref={no}
              type="button"
              autoFocus
              onClick={close}
              className={`min-h-[80px] rounded-2xl border-4 border-calm bg-calm/15 px-4
                          text-[length:clamp(24px,2.2vw,32px)] font-semibold text-paper ${focusRing}`}
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
              className={`min-h-[80px] rounded-2xl border-4 border-paper/40 px-4
                          text-[length:clamp(24px,2.2vw,32px)] font-semibold text-paper ${focusRing}`}
            >
              Yes, the call is over
            </button>
          </div>
        </div>
      </dialog>
    </>
  )
}
