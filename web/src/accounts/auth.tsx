import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { ApiError, api, errorMessage, type User } from './api'

type Auth =
  | { status: 'loading' }
  | { status: 'in'; user: User }
  | { status: 'out' }
  | { status: 'error'; message: string } // couldn't check (accounts database or network down)

const AuthContext = createContext<{ auth: Auth; refresh: () => Promise<void>; logout: () => Promise<void> }>({
  auth: { status: 'loading' },
  refresh: async () => {},
  logout: async () => {},
})

/** One check of the login cookie (GET /auth/me) shared by the whole app. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<Auth>({ status: 'loading' })

  const refresh = useCallback(async () => {
    try {
      const r = await api<{ user: User }>('GET', '/auth/me')
      setAuth({ status: 'in', user: r.user })
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setAuth({ status: 'out' })
      else setAuth({ status: 'error', message: errorMessage(e) })
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await api('POST', '/auth/logout')
    } finally {
      setAuth({ status: 'out' })
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return <AuthContext.Provider value={{ auth, refresh, logout }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

/**
 * Pages behind the login: logged out → /account?next=<this page>. If the login can't be checked
 * (accounts database down), say so instead of showing the page: the site fails closed.
 * Not used on /elder, /family or /pair: those open from per-call or pairing links, never a login.
 */
export function RequireAuth({ children, unlessSample = false }: { children: ReactNode; unlessSample?: boolean }) {
  const { auth, refresh } = useAuth()
  const where = useLocation()
  // A recorded sample holds no one's data, and must work with the server down (the runbook's fallback).
  if (unlessSample && new URLSearchParams(where.search).has('fixture')) return <>{children}</>
  if (auth.status === 'loading') return null
  if (auth.status === 'out') {
    const next = encodeURIComponent(where.pathname + where.search)
    return <Navigate to={`/account?next=${next}`} replace />
  }
  if (auth.status === 'error') {
    return (
      <main className="mx-auto flex min-h-dvh max-w-xl flex-col justify-center gap-4 px-5">
        <h1 className="title">Can't check your login right now</h1>
        <p role="alert" className="text-[18px] text-paper-dim">{auth.message}</p>
        <button type="button" onClick={refresh}
                className="btn-accent min-h-[52px] self-start px-6 text-[18px] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent">
          Try again
        </button>
      </main>
    )
  }
  return <>{children}</>
}
