import { useLayoutEffect, useRef, useState } from 'react'
import { highlightPieces, type Caption, type ElderState } from './state'

// Within this many pixels of the bottom counts as "reading the latest line".
const NEAR_BOTTOM = 48

/**
 * The whole call so far, newest at the bottom. It follows new lines on its own; scroll up to
 * read what was said earlier, and it stays put until you come back down (or tap "Latest").
 */
export function CaptionPane({
  state,
  speakerLabel,
}: {
  state: ElderState
  speakerLabel: (speakerRaw: string | null) => string | null
}) {
  const shown = state.order.map((uid) => state.captions[uid])
  const scroller = useRef<HTMLDivElement>(null)
  const [following, setFollowing] = useState(true)
  const last = shown[shown.length - 1]

  useLayoutEffect(() => {
    const el = scroller.current
    if (el && following) el.scrollTop = el.scrollHeight
  }, [following, shown.length, last?.text, last?.isFinal])

  const onScroll = () => {
    const el = scroller.current
    if (el) setFollowing(el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM)
  }
  const toLatest = () => {
    const el = scroller.current
    el?.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    setFollowing(true)
  }

  return (
    <section aria-label="Live captions" className="relative flex min-h-0 flex-col">
      <div
        ref={scroller}
        onScroll={onScroll}
        tabIndex={shown.length ? 0 : -1}
        aria-label="Call captions, scroll to read earlier lines"
        className="caption-scroll flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain px-[5vw] pt-[6vh] pb-6
                   [mask-image:linear-gradient(to_bottom,transparent,black_12%)]
                   focus-visible:outline-4 focus-visible:-outline-offset-4 focus-visible:outline-paper"
      >
        {shown.length === 0 ? (
          <p className="mt-auto text-[length:clamp(32px,3vw,44px)] text-mist">
            Captions of the call will show here.
          </p>
        ) : (
          <ol aria-live="polite" aria-relevant="additions text" className="mt-auto flex flex-col gap-5">
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
      </div>
      {!following && (
        <button
          type="button"
          onClick={toLatest}
          className="glass absolute right-[5vw] bottom-4 min-h-[56px] rounded-full px-6
                     text-[length:clamp(20px,1.6vw,26px)] font-semibold text-paper
                     focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-paper"
        >
          <span aria-hidden>↓ </span>Latest
        </button>
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
          caption.isFinal ? 'text-caption' : 'text-mist', // final captions: white (dark) / #0B1220 (light)
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
