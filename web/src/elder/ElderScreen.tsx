import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router'
import { feedFromSearch, useEvents, type Feed } from '../events/useEvents'
import { CaptionPane } from './CaptionPane'
import { CardPane, type Reply } from './CardPane'
import { StartProtection } from './StartProtection'
import { initialElderState, noVoiceLabels, reduceElder, type Voice } from './state'
import { Wordmark } from '../brand/Wordmark'
import { StatusBand } from './StatusBand'
import { GuessedVoice, VoicePicker } from './VoicePicker'

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
  // Default: listen to everyone (no speaker labels). On one shared laptop mic the labels drift,
  // and tapping the wrong "Voice 1" would mark the caller as Grandma (#40). ?voices=pick brings
  // back the voice picker for setups where labels are reliable.
  const pickVoices = search.get('voices') === 'pick'
  // A new call (or sample) starts the screen fresh, including the voice choice.
  return <ElderCall key={JSON.stringify(feed) + pickVoices} feed={feed} pickVoices={pickVoices} />
}

function ElderCall({ feed, pickVoices }: { feed: Feed; pickVoices: boolean }) {
  const { events, connection, error, send } = useEvents(feed)
  const state = useMemo(() => events.reduce(reduceElder, initialElderState), [events])
  const [tapped, setTapped] = useState<{ speakerRaw: string | null } | null>(null)
  const [reply, setReply] = useState<Reply>('none')

  // Who the grandparent is. Settled by a tap here, by elder_set "tap" (a tap that reached the
  // detector), or by elder_set null (labels off: everyone is scored, #40). A server guess for a
  // named voice ("Hello?" first) is used for labels but stays correctable with a tap.
  const es = state.elderSet
  const picked = !pickVoices
    ? { speakerRaw: null }
    : tapped ?? (es && (es.by === 'tap' || es.speakerRaw === null) ? { speakerRaw: es.speakerRaw } : null)
  const guess = !picked && es?.by === 'server' ? es.speakerRaw : null
  const elder = picked ?? (guess !== null ? { speakerRaw: guess } : null)

  const voiceNumber = (raw: string | null) => state.voices.findIndex((v) => v.speakerRaw === raw) + 1
  const speakerLabel = (raw: string | null): string | null => {
    if (raw === null) return null
    if (!elder) return `Voice ${voiceNumber(raw)}`
    if (elder.speakerRaw === null) return null // no voice labels: don't guess
    return raw === elder.speakerRaw ? 'You' : 'Caller'
  }
  const voiceLabel = (v: Voice, i: number) =>
    v.speakerRaw === null ? 'Everyone (no voice labels)' : `Voice ${i + 1}`

  const pickVoice = (speakerRaw: string | null) => {
    setTapped({ speakerRaw })
    send({ type: 'set_elder', speaker_raw: speakerRaw }) // a sample call has nowhere to send it
  }

  // No speaker labels: one "Start protection" button instead of the voice picker, and it
  // starts by itself 10 s after the first caption so nobody has to remember to tap.
  const unlabeled = noVoiceLabels(state)
  const heardSomething = state.order.length > 0
  useEffect(() => {
    if (picked || guess !== null || !unlabeled || !heardSomething) return
    const id = window.setTimeout(() => {
      setTapped({ speakerRaw: null })
      send({ type: 'set_elder', speaker_raw: null })
    }, AUTO_START_MS)
    return () => window.clearTimeout(id)
  }, [picked, guess, unlabeled, heardSomething, send])
  const startProtection = () => pickVoice(null)

  // Listen-to-everyone mode tells the server once, so cards fire even if it runs with labels on.
  const toldServer = useRef(false)
  useEffect(() => {
    if (pickVoices || connection !== 'open' || toldServer.current) return
    toldServer.current = send({ type: 'set_elder', speaker_raw: null })
  }, [pickVoices, connection, send])

  const answerCodeword = (ok: boolean) => {
    if (feed.kind !== 'live') return setReply('sample')
    setReply(send({ type: 'codeword_result', ok }) ? (ok ? 'sent-yes' : 'sent-no') : 'not-sent')
  }

  const notes: string[] = []
  if (feed.kind === 'fixture') notes.push('Sample call')
  if (connection === 'connecting') notes.push('Connecting…')
  if (connection === 'reconnecting') notes.push('Reconnecting…')
  if (picked?.speakerRaw === null) notes.push('Listening to everyone on the call')
  if (state.ended) notes.push('Call ended')
  if (state.warning) notes.push(state.warning)
  if (reply === 'sample') notes.push('Sample call: your answer was not sent')
  if (reply === 'not-sent') notes.push('Answer not sent: no connection. Tap again in a moment.')

  const problem =
    feed.kind === 'none'
      ? 'No call connected. Open this screen from the link the server prints.'
      : error

  return (
    <main className="grid h-dvh grid-rows-[60fr_40fr] overflow-hidden">
      <h1 className="sr-only">Aegis call captions</h1>
      <CaptionPane state={state} speakerLabel={speakerLabel} />
      <div
        className={`flex min-h-0 flex-col motion-safe:transition-colors motion-safe:duration-[1500ms]
                    ${TINT[state.level ?? 'none']}`}
      >
        <StatusBand level={state.level} notes={notes} brand={<Wordmark className="text-[length:clamp(22px,1.8vw,30px)]" />}>
          {!picked && state.card && (guess !== null ? (
            <VoicePicker voices={state.voices.filter((v) => v.speakerRaw !== guess)}
                         label={(v) => voiceLabel(v, state.voices.indexOf(v))}
                         onPick={pickVoice} compact prompt="Not you? Tap your voice:" />
          ) : unlabeled ? (
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
            ) : !picked && guess !== null ? (
              <GuessedVoice voices={state.voices} guess={guess} label={voiceLabel} onPick={pickVoice} />
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
