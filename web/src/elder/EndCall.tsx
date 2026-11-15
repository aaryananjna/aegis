import { useRef, type KeyboardEvent, type MouseEvent } from 'react'
import { PhoneDownIcon } from './Icons'
import { focusRing } from './VoicePicker'

/**
 * "I've hung up" (End call, #42) on the elder screen. Named for what Grandma did: "End call"
 * next to "Hang up." read as if it hung up the phone (#78). Ending is final (links die, history
 * is deleted), so it always asks first. "No, keep listening" is the default and focused; Escape or a tap outside
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
        // Red, so ending the call stands out: white on #B3261E is 6.5:1 in both themes.
        className={`inline-flex min-h-[76px] items-center gap-3 rounded-2xl border-2 border-white/80 bg-[#b3261e] px-8
                    text-[length:clamp(26px,2.2vw,34px)] font-bold text-white shadow-sm
                    hover:bg-[#8e1f19] motion-safe:transition-colors ${focusRing}`}
      >
        <span aria-hidden className="text-[1.1em]"><PhoneDownIcon /></span>
        I've hung up
      </button>
      <dialog
        ref={dialog}
        onKeyDown={trap}
        onClick={outside}
        aria-labelledby="end-title"
        aria-describedby={hangupShowing ? 'end-note' : undefined}
        className="room-reset m-auto w-[min(92vw,46rem)] rounded-3xl border border-[var(--glass-border-hot)]
                   bg-dusk-raised p-0 text-paper shadow-[0_24px_60px_-20px_rgba(0,0,0,0.6)]
                   backdrop:bg-black/55 backdrop:backdrop-blur-sm"
      >
        <div className="flex flex-col items-center gap-7 px-10 pt-10 pb-9 text-center">
          <span className="grid size-20 place-items-center rounded-full bg-accent/12 text-[40px] text-heading ring-1 ring-accent/30">
            <PhoneDownIcon />
          </span>
          <div className="flex flex-col gap-2">
            <h2 id="end-title" className="text-[length:clamp(34px,3.2vw,46px)] leading-tight font-bold text-balance">
              Are you sure this call is over?
            </h2>
            {hangupShowing && (
              <p id="end-note" className="text-[length:clamp(24px,2vw,30px)] text-paper-dim">
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
              className={`btn-accent min-h-[84px] rounded-2xl px-5 text-[length:clamp(24px,2.1vw,30px)] font-semibold ${focusRing}`}
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
              className={`min-h-[84px] rounded-2xl border-2 border-paper/35 px-5 text-[length:clamp(24px,2.1vw,30px)]
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
