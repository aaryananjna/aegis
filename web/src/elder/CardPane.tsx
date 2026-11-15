import { useEffect, useRef, type ReactNode } from 'react'
import { KeyIcon, PhoneDownIcon, ShieldIcon } from './Icons'
import type { ElderState } from './state'
import { focusRing } from './VoicePicker'

export type Reply = 'none' | 'sent-yes' | 'sent-no' | 'not-sent' | 'sample'

/** The one card the grandparent needs, or what goes there before a card (picker, idle line). */
export function CardPane({
  state,
  reply,
  onCodeword,
  empty,
}: {
  state: ElderState
  reply: Reply
  onCodeword: (ok: boolean) => void
  empty: ReactNode
}) {
  return (
    <div
      aria-live="assertive"
      aria-atomic
      className="flex min-h-0 flex-1 flex-col px-[5vw] pt-1 pb-[2.5vh]"
    >
      {state.card ? (
        <Card
          kind={state.card.kind}
          text={state.card.text}
          codewordOk={state.codewordOk}
          reply={reply}
          onCodeword={onCodeword}
        />
      ) : (
        empty
      )}
    </div>
  )
}

const CARD_LOOK = {
  codeword: { icon: <KeyIcon />, box: 'room-reset bg-dusk-raised text-paper', iconColor: 'text-care-text' },
  verify: { icon: <ShieldIcon />, box: 'room-reset bg-dusk-raised text-paper', iconColor: 'text-care-text' },
  // White edge: on the Warning red the card is the same red, so the border marks it out.
  hangup: { icon: <PhoneDownIcon />, box: 'bg-alarm-deep text-white border-4 border-white/90', iconColor: 'text-white' },
} as const

function Card({
  kind,
  text,
  codewordOk,
  reply,
  onCodeword,
}: {
  kind: keyof typeof CARD_LOOK
  text: string
  codewordOk: boolean
  reply: Reply
  onCodeword: (ok: boolean) => void
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => ref.current?.focus(), [kind])
  const look = CARD_LOOK[kind]
  const answered = codewordOk || reply === 'sent-yes' || reply === 'sent-no'

  return (
    <div
      ref={ref}
      tabIndex={-1}
      role="group"
      aria-label={kind === 'hangup' ? 'Hang up now' : 'What to do'}
      className={`flex min-h-0 flex-1 flex-col justify-center gap-[clamp(1rem,2vw,1.75rem)] rounded-3xl p-[clamp(1.25rem,2.5vw,2.5rem)]
                  ${look.box} ${focusRing}`}
    >
      <p className="flex items-center gap-[2vw]">
        <span className={`shrink-0 text-[length:clamp(48px,4.4vw,80px)] ${look.iconColor}`}>
          {look.icon}
        </span>
        {/* Bigger than any caption (#78): the instruction is the one thing to read. "Hang up." most of all. */}
        {/* Sized by height too, so it fits the 40% band on wide, short screens and keeps equal padding. */}
        <span className={`${kind === 'hangup' ? 'text-[length:clamp(36px,min(5vw,6vh),76px)] font-bold' : 'text-[length:clamp(30px,min(3.6vw,4.8vh),56px)] font-semibold'}
                          leading-[1.12] text-balance`}>
          {text}
        </span>
      </p>

      {kind === 'codeword' && !answered && (
        <div className="grid grid-cols-2 gap-[2vw]">
          <AnswerButton tone="yes" onClick={() => onCodeword(true)}>
            They knew it
          </AnswerButton>
          <AnswerButton tone="no" onClick={() => onCodeword(false)}>
            They didn't
          </AnswerButton>
        </div>
      )}
      {kind === 'codeword' && answered && (
        <p className="text-[length:clamp(26px,2.2vw,34px)] text-paper-dim">
          {codewordOk
            ? 'Good. They knew the code word. Aegis is still listening.'
            : 'Thanks. One moment.'}
        </p>
      )}
    </div>
  )
}

function AnswerButton({
  tone,
  onClick,
  children,
}: {
  tone: 'yes' | 'no'
  onClick: () => void
  children: string
}) {
  const colors =
    tone === 'yes'
      ? 'border-calm bg-calm/15 hover:bg-calm/25'
      : 'border-alarm bg-alarm/15 hover:bg-alarm/25'
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-[clamp(72px,9vh,112px)] rounded-2xl border-4 text-[length:clamp(30px,2.6vw,42px)]
                  font-semibold text-paper motion-safe:transition-colors ${colors} ${focusRing}`}
    >
      {children}
    </button>
  )
}
