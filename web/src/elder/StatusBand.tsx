import type { ReactNode } from 'react'
import type { ElderState } from './state'

// Words only, never numbers: the grandparent reads a feeling, not a score.
export const LEVEL = {
  low: { word: 'Normal call', dot: 'bg-calm', text: 'text-calm-text' },
  elevated: { word: 'Be careful', dot: 'bg-care', text: 'text-care-text' },
  high: { word: 'Warning', dot: 'bg-alarm', text: 'text-alarm-text' },
} as const

export function StatusBand({
  level,
  notes,
  children,
  brand,
}: {
  level: ElderState['level']
  notes: string[]
  children?: ReactNode
  brand?: ReactNode
}) {
  const look = level ? LEVEL[level] : null

  return (
    <div
      className="flex shrink-0 flex-wrap items-center justify-between gap-x-8 gap-y-2
                 border-t-2 border-paper/10 px-[5vw] py-3"
    >
      <p role="status" className="flex items-center gap-4 text-[length:clamp(26px,2.2vw,36px)] font-semibold">
        <span aria-hidden data-dot className={`size-[0.7em] rounded-full ${look ? look.dot : 'bg-mist'}`} />
        <span className={look ? look.text : 'text-mist'}>{look ? look.word : 'Listening'}</span>
      </p>
      {children}
      {/* The notes wrap beside the bigger red button instead of squeezing it. */}
      <div className="flex min-w-0 flex-1 flex-wrap items-center justify-end gap-x-6 gap-y-2">
        {notes.length > 0 && (
          <p className="max-w-[28ch] text-right text-[length:clamp(17px,1.3vw,21px)] leading-snug text-mist">
            {notes.join(' · ')}
          </p>
        )}
        {brand}
      </div>
    </div>
  )
}
