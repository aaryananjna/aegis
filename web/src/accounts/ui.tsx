import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'

// Shared pieces for the account pages: phone-first, same Aegis palette as /family.

export const focusRing =
  'focus-visible:outline-4 focus-visible:outline-offset-4 focus-visible:outline-paper'

export function Page({ children }: { children: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col gap-6 bg-dusk px-5
                     pt-[max(1.5rem,env(safe-area-inset-top))] pb-[max(1.5rem,env(safe-area-inset-bottom))]">
      <p className="text-[17px] font-semibold tracking-wide text-mist">Aegis</p>
      {children}
    </main>
  )
}

export function Field({
  label,
  hint,
  ...input
}: { label: string; hint?: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[17px] font-semibold text-paper">{label}</span>
      <input
        {...input}
        className={`min-h-[52px] rounded-xl border-2 border-white/20 bg-dusk-raised px-4 text-[19px]
                    text-paper placeholder:text-mist focus:border-paper/70 ${focusRing}`}
      />
      {hint && <span className="text-[15px] text-mist">{hint}</span>}
    </label>
  )
}

export function Button({
  children,
  kind = 'primary',
  ...rest
}: { kind?: 'primary' | 'plain' } & ButtonHTMLAttributes<HTMLButtonElement>) {
  const look =
    kind === 'primary'
      ? 'bg-paper text-dusk disabled:opacity-60'
      : 'border-2 border-white/25 text-paper hover:border-white/50'
  return (
    <button
      {...rest}
      className={`min-h-[52px] rounded-xl px-5 text-[19px] font-semibold ${look} ${focusRing} ${rest.className ?? ''}`}
    >
      {children}
    </button>
  )
}

export function Notice({ tone, children }: { tone: 'error' | 'ok'; children: ReactNode }) {
  return (
    <p
      role={tone === 'error' ? 'alert' : 'status'}
      className={`rounded-xl px-4 py-3 text-[17px] ${
        tone === 'error' ? 'bg-alarm/20 text-paper' : 'bg-calm/20 text-paper'
      }`}
    >
      {children}
    </p>
  )
}
