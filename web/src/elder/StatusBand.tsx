import type { ReactNode } from 'react'
import type { ElderState } from './state'

// Words only, never numbers: the grandparent reads a feeling, not a score.
export const LEVEL = {
  low: { word: 'Normal call', dot: 'bg-calm', text: 'text-calm' },
  elevated: { word: 'Be careful', dot: 'bg-care', text: 'text-care' },
  high: { word: 'Warning', dot: 'bg-alarm', text: 'text-alarm-text' },
} as const

export function StatusBand({
  level,
  notes,
  children,
}: {
  level: ElderState['level']
  notes: string[]
  children?: ReactNode
}) {
  const look = level ? LEVEL[level] : null

  return (
    <div
      className="flex shrink-0 flex-wrap items-center justify-between gap-x-8 gap-y-2
                 border-t-2 border-white/10 px-[5vw] py-3"
    >
      <p role="status" className="flex items-center gap-4 text-[length:clamp(26px,2.2vw,36px)] font-semibold">
        <span aria-hidden className={`size-[0.7em] rounded-full ${look ? look.dot : 'bg-mist'}`} />
        <span className={look ? look.text : 'text-mist'}>{look ? look.word : 'Listening'}</span>
      </p>
      {children}
      {notes.length > 0 && (
        <p className="text-[length:clamp(18px,1.4vw,22px)] text-mist">{notes.join(' · ')}</p>
      )}
    </div>
  )
}
