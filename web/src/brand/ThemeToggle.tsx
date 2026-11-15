import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'
const KEY = 'aegis_theme'

/** The theme in force: a saved choice, else the system setting. */
export function currentTheme(): Theme {
  const set = document.documentElement.dataset.theme
  if (set === 'light' || set === 'dark') return set
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

/** Apply a saved choice before React draws (called from main.tsx). Storage may be blocked. */
export function applySavedTheme() {
  try {
    const saved = localStorage.getItem(KEY)
    if (saved === 'light' || saved === 'dark') document.documentElement.dataset.theme = saved
  } catch {
    // no storage: follow the system setting
  }
}

/** Light/dark switch for the nav. The choice is saved; with none, the system setting wins. */
export function ThemeToggle({ className = '' }: { className?: string }) {
  const [theme, setTheme] = useState<Theme>('dark')
  useEffect(() => setTheme(currentTheme()), [])

  const next: Theme = theme === 'dark' ? 'light' : 'dark'
  const flip = () => {
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem(KEY, next)
    } catch {
      // not saved: still switches for this visit
    }
    setTheme(next)
  }

  return (
    <button
      type="button"
      onClick={flip}
      aria-label={`Switch to ${next} mode`}
      className={`glass inline-flex min-h-[44px] items-center gap-2 rounded-full px-4 text-[15px] font-semibold
                  text-paper focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent ${className}`}
    >
      <span aria-hidden>{theme === 'dark' ? '☀︎' : '☾'}</span>
      {theme === 'dark' ? 'Light' : 'Dark'}
    </button>
  )
}
