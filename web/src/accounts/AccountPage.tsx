import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router'
import { useAuth } from './auth'
import { api, errorMessage, type User } from './api'
import { Button, Field, Notice, Page, focusRing } from './ui'

/** /account: log in or sign up (family members only; the grandparent never logs in). */
export function AccountPage() {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()
  const { auth, refresh } = useAuth()
  const [search] = useSearchParams()
  // Only same-site paths ("/evidence"), never "//other.site" or a full URL.
  const raw = search.get('next') ?? '/'
  const next = raw.startsWith('/') && !raw.startsWith('//') ? raw : '/'

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    const body =
      mode === 'login'
        ? { email: f.get('email'), password: f.get('password') }
        : { email: f.get('email'), password: f.get('password'), display_name: f.get('name') }
    setBusy(true)
    setError(null)
    try {
      await api<{ user: User }>('POST', mode === 'login' ? '/auth/login' : '/auth/signup', body)
      await refresh()
      navigate(next, { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (auth.status === 'in') return <Navigate to={next} replace />

  return (
    <Page>
      <h1 className="title">
        {mode === 'login' ? 'Log in' : 'Create your account'}
      </h1>
      <p className="text-[18px] text-paper-dim">
        For family members who watch over a grandparent. The grandparent never needs an account.
      </p>
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate={false}>
        {mode === 'signup' && (
          <Field label="Your name" name="name" autoComplete="name" required maxLength={80} />
        )}
        <Field label="Email" name="email" type="email" autoComplete="email" required maxLength={254} />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          required
          minLength={8}
          maxLength={256}
          hint={mode === 'signup' ? '8 characters or more.' : undefined}
        />
        {error && <Notice tone="error">{error}</Notice>}
        <Button type="submit" disabled={busy}>
          {busy ? 'One moment…' : mode === 'login' ? 'Log in' : 'Create account'}
        </Button>
      </form>
      <p className="text-[17px] text-paper-dim">
        {mode === 'login' ? 'New here? ' : 'Already have an account? '}
        <button
          type="button"
          onClick={() => {
            setMode(mode === 'login' ? 'signup' : 'login')
            setError(null)
          }}
          className={`font-semibold text-paper underline underline-offset-4 ${focusRing}`}
        >
          {mode === 'login' ? 'Create an account' : 'Log in'}
        </button>
      </p>
    </Page>
  )
}
