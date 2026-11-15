import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { api, deviceToken } from '../accounts/api'
import { AegisWordmark } from '../brand/AegisWordmark'
import { localPath, savedFamilyUrl } from '../live/familyLink'
import { startError } from '../live/LiveCall'
import { CheckIcon } from './Icons'
import { focusRing } from './VoicePicker'

/**
 * /ready, and /pair once the laptop is paired (#107): the grandparent's laptop opens straight to
 * this. No login and nothing to find: one big Start button. It starts a live call the same way
 * the family's front page does (POST /sessions, laptop mic, labels off, the paired laptop's
 * token for the history) and goes to her call screen, with the family link after '#family='.
 */
export function ReadyScreen({ name: knownName = null }: { name?: string | null }) {
  const navigate = useNavigate()
  const [name, setName] = useState<string | null>(knownName)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const token = deviceToken.get()

  useEffect(() => {
    if (knownName || !token) return
    api<{ elder: { display_name: string } }>('GET', '/device/me', undefined, { 'X-Device-Token': token })
      .then((r) => setName(r.elder.display_name))
      .catch(() => {}) // the call still starts; the family page just says "your family member"
  }, [knownName, token])

  const start = async () => {
    setBusy(true)
    setError(null)
    try {
      const r = await api<{ session_id: string; elder_url: string; family_url: string }>(
        'POST',
        '/sessions',
        { ...(name ? { name: name.slice(0, 40) } : {}), mic: true, labels: false },
        token ? { 'X-Device-Token': token } : {},
      )
      savedFamilyUrl.set(r.session_id, r.family_url)
      navigate(`${localPath(r.elder_url)}#family=${encodeURIComponent(r.family_url)}`)
    } catch (e) {
      setError(startError(e))
      setBusy(false)
    }
  }

  return (
    <main className="flex h-dvh flex-col overflow-hidden bg-dusk text-paper">
      <div className="flex justify-end px-[clamp(1rem,3vw,3rem)] py-[clamp(1rem,2.5vh,2rem)]">
        <AegisWordmark size="nav" />
      </div>
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-[clamp(1.5rem,4vh,3rem)] px-[5vw] pb-[8vh] text-center">
        <span aria-hidden className="text-[length:clamp(64px,7vw,120px)] text-calm-text">
          <CheckIcon />
        </span>
        <h1 className="font-display text-[length:clamp(52px,min(6vw,10vh),112px)] leading-none font-bold text-heading">
          Aegis is ready
        </h1>
        <ol className="flex flex-col gap-2 text-[length:clamp(26px,min(2.4vw,4vh),42px)] text-paper-dim">
          <li>1. Put your phone on speaker, next to this laptop.</li>
          <li>2. Press Start.</li>
        </ol>
        <button
          type="button"
          onClick={start}
          disabled={busy}
          autoFocus
          className={`btn-accent min-h-[clamp(96px,14vh,160px)] min-w-[min(80vw,36rem)] rounded-3xl px-[4vw]
                      text-[length:clamp(40px,min(4.4vw,7vh),80px)] font-bold disabled:opacity-70 ${focusRing}`}
        >
          {busy ? 'Starting…' : 'Start'}
        </button>
        {error && (
          <p role="alert" className="max-w-[40ch] text-[length:clamp(24px,2vw,32px)] text-alarm-text">
            {error}
          </p>
        )}
      </div>
    </main>
  )
}
