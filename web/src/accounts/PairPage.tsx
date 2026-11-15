import { useEffect, useState } from 'react'
import { ReadyScreen } from '../elder/ReadyScreen'
import { api, deviceToken, errorMessage, tokenFromHash } from './api'
import { Page } from './ui'

type State =
  | { kind: 'checking' }
  | { kind: 'paired'; name: string }
  | { kind: 'not-paired' }
  | { kind: 'error'; message: string }

/**
 * /pair: opened once on the grandparent's laptop from the link a family member made (#35).
 * The token arrives in the #hash (never sent to a server in a URL), is kept in localStorage
 * and wiped from the address bar. No login on this laptop, ever.
 */
export function PairPage() {
  const [state, setState] = useState<State>({ kind: 'checking' })

  useEffect(() => {
    const fromLink = tokenFromHash(window.location.hash)
    if (fromLink) {
      deviceToken.set(fromLink)
      window.history.replaceState(null, '', window.location.pathname)
    }
    const token = fromLink ?? deviceToken.get()
    if (!token) {
      setState({ kind: 'not-paired' })
      return
    }
    api<{ elder: { id: string; display_name: string } }>('GET', '/device/me', undefined, {
      'X-Device-Token': token,
    })
      .then((r) => setState({ kind: 'paired', name: r.elder.display_name }))
      .catch((e) =>
        setState(
          e?.status === 401
            ? { kind: 'error', message: "This pairing link didn't work, or the laptop was unpaired. Ask your family to send a new one." }
            : { kind: 'error', message: errorMessage(e) },
        ),
      )
  }, [])

  // Paired: straight to the one-button Start screen (#107). Nothing else for her to find.
  if (state.kind === 'paired') return <ReadyScreen name={state.name} />

  return (
    <Page>
      {state.kind === 'checking' && <p className="text-[22px] text-paper-dim">Checking this laptop…</p>}
      {state.kind === 'not-paired' && (
        <section className="flex flex-col gap-3">
          <h1 className="title">This laptop isn't set up yet</h1>
          <p className="text-[20px] text-paper-dim">
            Open the pairing link a family member sent you, on this laptop.
          </p>
        </section>
      )}
      {state.kind === 'error' && (
        <section className="flex flex-col gap-3">
          <h1 className="title">Couldn't set up this laptop</h1>
          <p role="alert" className="text-[20px] text-paper-dim">{state.message}</p>
        </section>
      )}
    </Page>
  )
}
