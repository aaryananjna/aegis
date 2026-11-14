import { highlightPieces, type Caption, type ElderState } from './state'

const VISIBLE_LINES = 4

export function CaptionPane({
  state,
  speakerLabel,
}: {
  state: ElderState
  speakerLabel: (speakerRaw: string | null) => string | null
}) {
  const shown = state.order.slice(-VISIBLE_LINES).map((uid) => state.captions[uid])

  return (
    <section
      aria-label="Live captions"
      className="relative flex min-h-0 flex-col justify-end overflow-hidden px-[5vw] pb-6
                 [mask-image:linear-gradient(to_bottom,transparent,black_18%)]"
    >
      {shown.length === 0 ? (
        <p className="text-[length:clamp(32px,3vw,44px)] text-mist">
          Captions of the call will show here.
        </p>
      ) : (
        <ol aria-live="polite" aria-relevant="additions text" className="flex flex-col gap-5">
          {shown.map((c) => (
            <CaptionLine
              key={c.utteranceId}
              caption={c}
              label={speakerLabel(c.speakerRaw)}
              highlight={state.highlights[c.utteranceId]}
            />
          ))}
        </ol>
      )}
    </section>
  )
}

function CaptionLine({
  caption,
  label,
  highlight,
}: {
  caption: Caption
  label: string | null
  highlight: ElderState['highlights'][string] | undefined
}) {
  const own = label === 'You'
  const pieces = highlightPieces(caption.text, highlight?.evidence ?? [])
  const markClass = highlight?.provisional
    ? 'bg-transparent text-inherit underline decoration-glow decoration-dotted decoration-[5px] underline-offset-[10px]'
    : 'rounded-md bg-glow/90 px-1.5 text-glow-ink [box-decoration-break:clone]'

  return (
    <li className="flex flex-col gap-1">
      {(label || caption.typed) && (
        <span className="flex items-center gap-3 text-[length:clamp(20px,1.6vw,26px)] font-medium text-mist">
          {label}
          {caption.typed && (
            <span className="rounded-full border-2 border-mist px-3 text-[0.8em] leading-snug">
              typed
            </span>
          )}
        </span>
      )}
      <p
        className={[
          'leading-[1.22] font-medium text-balance',
          own ? 'text-[length:clamp(44px,3.6vw,56px)]' : 'text-[length:clamp(48px,4.4vw,68px)]',
          caption.isFinal ? (own ? 'text-paper-dim' : 'text-paper') : 'text-mist',
        ].join(' ')}
      >
        {pieces.map((p, i) =>
          p.marked ? (
            <mark key={i} className={markClass}>
              {p.text}
            </mark>
          ) : (
            <span key={i}>{p.text}</span>
          ),
        )}
      </p>
    </li>
  )
}
