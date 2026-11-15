import qrcode from 'qrcode-generator'
import { useMemo, useState, type FormEvent } from 'react'
import { cleanTunnel, isPhoneReady, phoneUrl, tunnel } from './familyLink'

/**
 * The family link as a QR code for the phone to scan (#63), drawn here with no network call.
 * Dark modules on white in both themes, because that's what phone cameras read best.
 * The tunnel address (from `cloudflared`) is asked once and remembered on this laptop.
 */
export function FamilyQr({ familyUrl }: { familyUrl: string }) {
  const [origin, setOrigin] = useState(() => tunnel.get())
  const [editing, setEditing] = useState(false)
  const [bad, setBad] = useState(false)
  const link = phoneUrl(familyUrl, origin)
  const ready = isPhoneReady(familyUrl) // the server put it on the tunnel: nothing to set here

  const svg = useMemo(() => {
    const qr = qrcode(0, 'M')
    qr.addData(link)
    qr.make()
    return qr.createSvgTag({ cellSize: 6, margin: 3, scalable: true })
  }, [link])

  const save = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const raw = String(new FormData(e.currentTarget).get('tunnel') ?? '')
    const clean = raw.trim() === '' ? null : cleanTunnel(raw)
    if (raw.trim() !== '' && !clean) return setBad(true)
    tunnel.set(clean)
    setOrigin(clean)
    setBad(false)
    setEditing(false)
  }

  return (
    <div className="flex flex-col gap-4">
      <div
        role="img"
        aria-label="QR code of the family link"
        className="mx-auto w-full max-w-[240px] rounded-2xl bg-white p-2 [&>svg]:block [&>svg]:h-auto [&>svg]:w-full"
        dangerouslySetInnerHTML={{ __html: svg }}
      />
      {!ready && !origin && (
        <p className="text-[15px] text-care-text">
          This link only opens on this laptop. Add the tunnel address so a phone can open it.
        </p>
      )}
      <p className="text-[15px] break-all text-mist">{link}</p>
      {ready ? null : editing ? (
        <form onSubmit={save} className="flex flex-col gap-2">
          <label htmlFor="tunnel" className="text-[15px] font-semibold text-paper">
            Tunnel address
          </label>
          <input
            id="tunnel"
            name="tunnel"
            defaultValue={origin ?? ''}
            placeholder="https://some-words.trycloudflare.com"
            aria-invalid={bad}
            aria-describedby={bad ? 'tunnel-err' : undefined}
            className="min-h-[44px] rounded-xl border border-paper/25 bg-dusk-raised px-3 text-[16px] text-paper
                       focus-visible:outline-2 focus-visible:outline-accent"
          />
          {bad && (
            <p id="tunnel-err" className="text-[15px] text-alarm-text">
              Use the https address cloudflared printed.
            </p>
          )}
          <button type="submit" className="btn-accent min-h-[44px] px-4 text-[16px] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent">
            Save
          </button>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="self-start text-[15px] font-semibold text-paper underline underline-offset-4
                     focus-visible:outline-2 focus-visible:outline-accent"
        >
          {origin ? 'Change the tunnel address' : 'Add the tunnel address'}
        </button>
      )}
    </div>
  )
}
