import { focusRing } from './VoicePicker'

/**
 * Shown instead of the voice picker when the screen can't tell voices apart (no speaker
 * labels). One tap sends set_elder {speaker_raw: null}: score everyone.
 */
export function StartProtection({ onStart, compact = false }: { onStart: () => void; compact?: boolean }) {
  if (compact) {
    return (
      <button
        type="button"
        onClick={onStart}
        className={`rounded-xl border-2 border-paper/40 px-4 py-1 text-[length:clamp(20px,1.6vw,26px)]
                    font-semibold text-paper hover:border-paper/80 ${focusRing}`}
      >
        Start protection
      </button>
    )
  }
  return (
    <section aria-labelledby="start-heading" className="flex flex-col items-start gap-4">
      <h2 id="start-heading" className="text-[length:clamp(26px,2.2vw,34px)] font-semibold text-paper">
        This call doesn't show who is talking.
      </h2>
      <button
        type="button"
        onClick={onStart}
        className={`min-h-[clamp(72px,9vh,112px)] rounded-2xl border-4 border-calm bg-calm/15 px-[4vw]
                    text-[length:clamp(30px,2.6vw,42px)] font-semibold text-paper hover:bg-calm/25
                    motion-safe:transition-colors ${focusRing}`}
      >
        Start protection
      </button>
      <p className="text-[length:clamp(20px,1.6vw,26px)] text-mist">
        Aegis will listen to everyone. It starts by itself in a few seconds.
      </p>
    </section>
  )
}
