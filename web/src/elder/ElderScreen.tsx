import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { feedFromSearch, useEvents, type Feed } from '../events/useEvents'
import { CaptionPane } from './CaptionPane'
import { CardPane, type Reply } from './CardPane'
import { StartProtection } from './StartProtection'
import { initialElderState, noVoiceLabels, reduceElder, type Voice } from './state'
import { StatusBand } from './StatusBand'
import { VoicePicker } from './VoicePicker'

// The room's light: the lower part of the screen takes on the status color.
const TINT = {
  none: 'bg-dusk',
  low: 'bg-[color-mix(in_oklab,var(--color-calm)_10%,var(--color-dusk))]',
  elevated: 'bg-[color-mix(in_oklab,var(--color-care)_14%,var(--color-dusk))]',
  high: 'bg-[color-mix(in_oklab,var(--color-alarm)_20%,var(--color-dusk))]',
} as const

const idleText = 'text-[length:clamp(28px,2.4vw,36px)] text-mist'

// With no speaker labels, protection starts by itself this long after the first caption.
const AUTO_START_MS = 10_000

export function ElderScreen() {
  const [search] = useSearchParams()
  const feed = feedFromSearch(search, 'elder')
  // A new call (or sample) starts the screen fresh, including the voice choice.
  return <ElderCall key={JSON.stringify(feed)} feed={feed} />
}

function ElderCall({ feed }: { feed: Feed }) {
  const { events, connection, error, send } = useEvents(feed)
  const state = useMemo(() => events.reduce(reduceElder, initialElderState), [events])
  const [picked, setPicked] = useState<{ speakerRaw: string | null } | null>(null)
  const [reply, setReply] = useState<Reply>('none')

  const voiceNumber = (raw: string | null) => state.voices.findIndex((v) => v.speakerRaw === raw) + 1
  const speakerLabel = (raw: string | null): string | null => {
    if (raw === null) return null
    if (!picked) return `Voice ${voiceNumber(raw)}`
    if (picked.speakerRaw === null) return null // no voice labels: don't guess
    return raw === picked.speakerRaw ? 'You' : 'Caller'
  }
  const voiceLabel = (v: Voice, i: number) =>
    v.speakerRaw === null ? 'Everyone (no voice labels)' : `Voice ${i + 1}`

  const pickVoice = (speakerRaw: string | null) => {
    setPicked({ speakerRaw })
    send({ type: 'set_elder', speaker_raw: speakerRaw }) // a sample call has nowhere to send it
  }

  // No speaker labels: one "Start protection" button instead of the voice picker, and it
  // starts by itself 10 s after the first caption so nobody has to remember to tap.
  const unlabeled = noVoiceLabels(state)
  const heardSomething = state.order.length > 0
  useEffect(() => {
    if (picked || !unlabeled || !heardSomething) return
    const id = window.setTimeout(() => {
      setPicked({ speakerRaw: null })
      send({ type: 'set_elder', speaker_raw: null })
    }, AUTO_START_MS)
    return () => window.clearTimeout(id)
  }, [picked, unlabeled, heardSomething, send])
  const startProtection = () => pickVoice(null)

  const answerCodeword = (ok: boolean) => {
    if (feed.kind !== 'live') return setReply('sample')
    setReply(send({ type: 'codeword_result', ok }) ? (ok ? 'sent-yes' : 'sent-no') : 'not-sent')
  }

  const notes: string[] = []
  if (feed.kind === 'fixture') notes.push('Sample call')
  if (connection === 'connecting') notes.push('Connecting…')
  if (connection === 'reconnecting') notes.push('Reconnecting…')
  if (picked?.speakerRaw === null) notes.push("Can't tell voices apart: listening to everyone")
  if (state.ended) notes.push('Call ended')
  if (state.warning) notes.push(state.warning)
  if (reply === 'sample') notes.push('Sample call: your answer was not sent')
  if (reply === 'not-sent') notes.push('Answer not sent: no connection. Tap again in a moment.')

  const problem =
    feed.kind === 'none'
      ? 'No call connected. Open this screen from the link the server prints.'
      : error

  return (
    <main className="grid h-dvh grid-rows-[60fr_40fr] overflow-hidden bg-dusk">
      <h1 className="sr-only">Aegis call captions</h1>
      <CaptionPane state={state} speakerLabel={speakerLabel} />
      <div
        className={`flex min-h-0 flex-col motion-safe:transition-colors motion-safe:duration-[1500ms]
                    ${TINT[state.level ?? 'none']}`}
      >
        <StatusBand level={state.level} notes={notes}>
          {!picked && state.card && (unlabeled ? (
            <StartProtection onStart={startProtection} compact />
          ) : (
            <VoicePicker voices={state.voices} label={voiceLabel} onPick={pickVoice} compact />
          ))}
        </StatusBand>
        <CardPane
          state={state}
          reply={reply}
          onCodeword={answerCodeword}
          empty={
            problem ? (
              <p className={idleText}>{problem}</p>
            ) : !picked && unlabeled ? (
              <StartProtection onStart={startProtection} />
            ) : !picked ? (
              <VoicePicker voices={state.voices} label={voiceLabel} onPick={pickVoice} />
            ) : (
              <p className={idleText}>
                {state.ended
                  ? 'The call has ended.'
                  : state.order.length === 0
                    ? 'Waiting for the call to start.'
                    : 'Aegis is listening.'}
              </p>
            )
          }
        />
      </div>
    </main>
  )
}
