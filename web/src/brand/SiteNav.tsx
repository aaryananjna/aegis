import { Link, useLocation, useNavigate } from 'react-router'
import { useAuth } from '../accounts/auth'
import { AegisWordmark } from './AegisWordmark'
import { ThemeToggle } from './ThemeToggle'

const pill =
  'glass inline-flex min-h-[44px] items-center rounded-full px-4 text-[15px] font-semibold text-paper ' +
  'focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent'

/**
 * The top bar on every page except /elder. A back arrow returns to the page you came from (only
 * when there is one in this tab); the wordmark is the way home, and the front page hides it
 * because its big wordmark is already there. Logged in: "My family" and "Log out". Logged out:
 * "Log in".
 */
export function SiteNav({
  section,
  brand = true,
  login = true,
}: {
  section?: string
  brand?: boolean
  login?: boolean
}) {
  const { auth, logout } = useAuth()
  const navigate = useNavigate()
  useLocation() // redraw on every move, so the back arrow appears once there's somewhere to go
  // React Router numbers this tab's history entries; 0 is the first page opened in it.
  const canGoBack = ((window.history.state as { idx?: number } | null)?.idx ?? 0) > 0

  return (
    <nav aria-label="Aegis" className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        {canGoBack && (
          <button
            type="button"
            onClick={() => navigate(-1)}
            aria-label="Back to the previous page"
            title="Back"
            className={`${pill} w-[44px] justify-center !px-0 text-[22px]`}
          >
            <svg aria-hidden width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M11 6l-6 6 6 6" />
            </svg>
          </button>
        )}
        {brand && (
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
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {auth.status === 'in' ? (
          <>
            <Link to="/home" className={pill}>
              My family
            </Link>
            <button
              type="button"
              className={pill}
              onClick={async () => {
                await logout()
                navigate('/account', { replace: true })
              }}
            >
              Log out
            </button>
          </>
        ) : (
          login && (
            <Link to="/account" className={pill}>
              Log in
            </Link>
          )
        )}
        <ThemeToggle />
      </div>
    </nav>
  )
}
