import { Link, useNavigate } from 'react-router'
import { useAuth } from '../accounts/auth'
import { AegisWordmark } from './AegisWordmark'
import { ThemeToggle } from './ThemeToggle'

const pill =
  'glass inline-flex min-h-[44px] items-center rounded-full px-4 text-[15px] font-semibold text-paper ' +
  'focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent'

/**
 * The top bar on every page except /elder. The wordmark is the way home (no separate Home
 * button); the front page hides it because its big wordmark is already there. Logged in:
 * "My family" and "Log out". Logged out: "Log in".
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

  return (
    <nav aria-label="Aegis" className={`flex flex-wrap items-center gap-3 ${brand ? 'justify-between' : 'justify-end'}`}>
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
