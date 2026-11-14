import { Link } from 'react-router'
import { AegisWordmark } from './AegisWordmark'
import { ThemeToggle } from './ThemeToggle'

const pill =
  'glass inline-flex min-h-[44px] items-center rounded-full px-4 text-[15px] font-semibold text-paper ' +
  'focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent'

/**
 * The top bar on every page except /elder: the wordmark (links home), the section name in the
 * same display face, a visible way back home, log in, and the theme toggle.
 */
export function SiteNav({
  section,
  home = true,
  login = true,
}: {
  section?: string
  home?: boolean
  login?: boolean
}) {
  return (
    <nav aria-label="Aegis" className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-baseline gap-3">
        <Link to="/" aria-label="Aegis home" className="rounded-lg focus-visible:outline-2 focus-visible:outline-accent">
          <AegisWordmark size="nav" />
        </Link>
        {section && (
          <span className="font-display text-[1.6rem] leading-none font-semibold text-mist">
            <span aria-hidden className="mr-3 text-paper/30">/</span>
            {section}
          </span>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {home && (
          <Link to="/" className={pill}>
            <span aria-hidden className="mr-1.5">←</span> Home
          </Link>
        )}
        {login && (
          <Link to="/account" className={pill}>
            Log in
          </Link>
        )}
        <ThemeToggle />
      </div>
    </nav>
  )
}
