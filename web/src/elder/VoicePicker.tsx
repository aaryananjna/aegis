import { CheckIcon } from './Icons'
import type { Voice } from './state'

export const focusRing =
  'focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-paper'

/**
 * "Who is the grandparent?" Each voice heard so far, with its latest line. Tapping one sends
 * set_elder. `compact` is a single row for the status band, used when a card needs the space.
 */
export function VoicePicker({
  voices,
  label,
  onPick,
  compact = false,
  prompt,
}: {
  voices: Voice[]
  label: (v: Voice, i: number) => string
  onPick: (speakerRaw: string | null) => void
  compact?: boolean
  prompt?: string
}) {
  if (compact) {
    return (
      <section aria-labelledby="who-heading" className="flex flex-wrap items-center gap-3">
        <h2 id="who-heading" className="text-[length:clamp(20px,1.6vw,26px)] font-semibold text-paper">
          {prompt ?? 'Tap the voice that is you:'}
        </h2>
        {voices.map((v, i) => (
          <button
            key={v.speakerRaw ?? 'none'}
            type="button"
            onClick={() => onPick(v.speakerRaw)}
            className={`rounded-xl border-2 border-paper/40 px-4 py-1 text-[length:clamp(20px,1.6vw,26px)]
                        font-semibold text-paper hover:border-paper/80 ${focusRing}`}
          >
            {label(v, i)}
          </button>
        ))}
      </section>
    )
  }

  return (
    <section aria-labelledby="who-heading" className="flex flex-col gap-3">
      <h2 id="who-heading" className="text-[length:clamp(30px,2.6vw,42px)] font-semibold text-paper">
        Tap the voice that is you.
      </h2>
      {voices.length === 0 ? (
        <p className="text-[length:clamp(22px,1.8vw,28px)] text-mist">
          Voices show up here once people start talking.
        </p>
      ) : (
        <ul className="flex flex-wrap gap-4">
          {voices.map((v, i) => (
            <li key={v.speakerRaw ?? 'none'} className="min-w-0 flex-1 basis-[18rem]">
              <button
                type="button"
                onClick={() => onPick(v.speakerRaw)}
                aria-label={label(v, i)}
                aria-describedby={`voice-line-${i}`}
                className={`flex w-full flex-col items-start gap-1 rounded-2xl border-4 border-paper/25
                            bg-dusk-raised px-6 py-4 text-left hover:border-paper/60
                            motion-safe:transition-colors ${focusRing}`}
              >
                <span className="text-[length:clamp(24px,2vw,32px)] font-semibold text-paper">
                  {label(v, i)}
                </span>
                <span id={`voice-line-${i}`} className="line-clamp-2 text-[length:clamp(20px,1.6vw,26px)] text-paper-dim">
                  “{v.lastText}”
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/**
 * The server guessed the grandparent's voice from her first "Hello?" (elder_set by "server",
 * #40). Say so quietly, and keep the other voices tappable in case the guess is wrong.
 */
export function GuessedVoice({
  voices,
  guess,
  label,
  onPick,
}: {
  voices: Voice[]
  guess: string
  label: (v: Voice, i: number) => string
  onPick: (speakerRaw: string | null) => void
}) {
  const i = voices.findIndex((v) => v.speakerRaw === guess)
  const mine = voices[i]
  const others = voices.filter((v) => v.speakerRaw !== guess)
  return (
    <section aria-labelledby="guess-heading" className="flex flex-col gap-4">
      <h2 id="guess-heading" className="flex items-center gap-3 text-[length:clamp(26px,2.2vw,34px)] font-semibold text-paper">
        <span className="text-calm-text">
          <CheckIcon />
        </span>
        We think this voice is you
      </h2>
      {mine && (
        <p className="rounded-2xl border-4 border-calm/60 bg-calm/10 px-6 py-3 text-[length:clamp(22px,1.8vw,28px)] text-paper-dim">
          <span className="font-semibold text-paper">{label(mine, i)}</span> “{mine.lastText}”
        </p>
      )}
      {others.length > 0 && (
        <VoicePicker voices={others} label={(v) => label(v, voices.indexOf(v))} onPick={onPick}
                     compact prompt="Not you? Tap your voice:" />
      )}
    </section>
  )
}
