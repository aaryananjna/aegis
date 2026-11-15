import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { ApiError, api, errorMessage, type ElderRef, type User } from './api'
import { Button, Field, Notice, Page } from './ui'
import { useAuth } from './auth'
import { FamilyQr } from '../live/FamilyQr'
import { fetchTunnelOrigin } from '../live/familyLink'

/** /home: the logged-in family member's grandparents, adding one, and pairing a laptop. */
export function HomePage() {
  const navigate = useNavigate()
  const [me, setMe] = useState<{ user: User; elders: ElderRef[] } | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Any 401 means the login is gone: back to the login screen (#35).
  const guard = useCallback(
    (e: unknown) => {
      if (e instanceof ApiError && e.status === 401) navigate('/account', { replace: true })
      else setError(errorMessage(e))
    },
    [navigate],
  )

  const load = useCallback(async () => {
    try {
      setMe(await api('GET', '/auth/me'))
    } catch (e) {
      guard(e)
    }
  }, [guard])

  useEffect(() => {
    load()
  }, [load])

  const { logout: endLogin } = useAuth()
  const logout = async () => {
    await endLogin()
    navigate('/account', { replace: true })
  }

  return (
    <Page>
      <header className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="title">
          {me ? `Hi, ${me.user.display_name}` : 'Your family'}
        </h1>
        <Button kind="plain" onClick={logout}>
          Log out
        </Button>
      </header>
      {error && <Notice tone="error">{error}</Notice>}
      {me && (
        <>
          <section aria-labelledby="elders-h" className="flex flex-col gap-4">
            <h2 id="elders-h" className="subtitle">
              Who you watch over
            </h2>
            {me.elders.length === 0 ? (
              <p className="text-[18px] text-paper-dim">No one yet. Add the person you look out for below.</p>
            ) : (
              me.elders.map((e) => <ElderCard key={e.id} elder={e} onError={guard} />)
            )}
          </section>
          {me.elders.length > 0 && <WatchQrSection />}
          <AddElder
            onAdded={load}
            onError={guard}
          />
        </>
      )}
    </Page>
  )
}

function ElderCard({ elder, onError }: { elder: ElderRef; onError: (e: unknown) => void }) {
  const [pairUrl, setPairUrl] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const owner = elder.role === 'owner'

  const pair = async () => {
    setBusy(true)
    try {
      const r = await api<{ device_token: string; pair_url: string }>('POST', `/elders/${elder.id}/devices`)
      setPairUrl(r.pair_url)
    } catch (e) {
      onError(e)
    } finally {
      setBusy(false)
    }
  }

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(pairUrl ?? '')
      setCopied(true)
    } catch {
      setCopied(false) // clipboard blocked: the link is selectable below
    }
  }

  return (
    <article className="flex flex-col gap-3 rounded-2xl bg-dusk-raised p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="subtitle text-[1.4rem]">{elder.display_name}</h3>
        <span className="shrink-0 whitespace-nowrap rounded-full border border-paper/25 px-3 py-0.5 text-[15px] text-paper-dim">
          {owner ? 'You added them' : 'You can view'}
        </span>
      </div>
      <p className="text-[17px] text-paper-dim">
        When a call to {elder.display_name} looks like a scam, the alert goes to everyone here.
      </p>
      {owner && !pairUrl && (
        <Button kind="plain" onClick={pair} disabled={busy}>
          {busy ? 'One moment…' : `Pair ${elder.display_name}'s laptop`}
        </Button>
      )}
      {pairUrl && (
        <div className="flex flex-col gap-2 rounded-xl border-2 border-calm/60 bg-calm/10 p-4">
          <p className="text-[17px] font-semibold text-paper">
            Open this link once on {elder.display_name}'s laptop:
          </p>
          <code className="break-all rounded-lg bg-dusk px-3 py-2 text-[15px] text-paper select-all">{pairUrl}</code>
          <p className="text-[15px] text-mist">
            It's shown only this once, and works like a key, so send it only to that laptop.
          </p>
          <Button kind="plain" onClick={copy}>
            {copied ? 'Copied' : 'Copy link'}
          </Button>
        </div>
      )}
    </article>
  )
}

function AddElder({ onAdded, onError }: { onAdded: () => void; onError: (e: unknown) => void }) {
  const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget
    const name = String(new FormData(form).get('name') ?? '').trim()
    if (!name) return
    setBusy(true)
    try {
      await api('POST', '/elders', { display_name: name })
      form.reset()
      onAdded()
    } catch (err) {
      onError(err)
    } finally {
      setBusy(false)
    }
  }
  return (
    <section aria-labelledby="add-h" className="flex flex-col gap-3">
      <h2 id="add-h" className="subtitle">Add someone to protect</h2>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <Field label="Their name" name="name" required maxLength={80} placeholder="Rose" />
        <Button type="submit" disabled={busy}>
          {busy ? 'Adding…' : 'Add'}
        </Button>
      </form>
    </section>
  )
}

/**
 * One fixed QR code for the family's phone (#94): it opens /watch, they log in once, and every
 * call after that shows up there by itself. No new code per call.
 */
function WatchQrSection() {
  // The server knows the tunnel's address (#96): use it, so nobody has to type it in.
  const [origin, setOrigin] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    const check = () => fetchTunnelOrigin().then((o) => live && setOrigin(o))
    check()
    const id = window.setInterval(check, 15_000)
    return () => {
      live = false
      window.clearInterval(id)
    }
  }, [])
  return (
    <section aria-labelledby="watch-h" className="flex flex-col gap-3">
      <h2 id="watch-h" className="subtitle">Follow calls on your phone</h2>
      <p className="text-[18px] text-paper-dim">
        Scan this once with your phone and log in. Keep the page open, and each call shows up there
        by itself, with alerts if it looks like a scam.
      </p>
      <div className="max-w-sm">
        <FamilyQr familyUrl={`${origin ?? window.location.origin}/watch`} />
      </div>
    </section>
  )
}
