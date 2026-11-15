// The family link for a live call (#63): the server hands it out as http://localhost:5173/...,
// which a phone can't open, so the phone's copy uses the tunnel address instead.

const TUNNEL_KEY = 'aegis_tunnel'

/** A tunnel address is an https origin, e.g. https://some-words.trycloudflare.com. */
export function cleanTunnel(raw: string): string | null {
  try {
    const u = new URL(raw.trim())
    return u.protocol === 'https:' ? u.origin : null
  } catch {
    return null
  }
}

export const tunnel = {
  get(): string | null {
    try {
      return cleanTunnel(localStorage.getItem(TUNNEL_KEY) ?? '')
    } catch {
      return null
    }
  },
  set(origin: string | null) {
    try {
      if (origin) localStorage.setItem(TUNNEL_KEY, origin)
      else localStorage.removeItem(TUNNEL_KEY)
    } catch {
      // storage blocked: it applies to this visit only
    }
  },
}

/** The link as the phone should open it: same path and token, on the tunnel when there is one. */
export function phoneUrl(familyUrl: string, tunnelOrigin: string | null): string {
  if (!tunnelOrigin) return familyUrl
  const u = new URL(familyUrl)
  return tunnelOrigin + u.pathname + u.search
}

/** "/elder?session=…&token=…" from the server's full elder_url, so it opens on this site. */
export function localPath(url: string): string {
  const u = new URL(url)
  return u.pathname + u.search
}
