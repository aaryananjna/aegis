// The family link for a live call (#63): the server hands it out as http://localhost:5173/...,
// which a phone can't open, so the phone's copy uses the tunnel address instead.

const TUNNEL_KEY = 'aegis_tunnel'
const familyKey = (sessionId: string) => `aegis_family_url:${sessionId}`

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

/** True when the server already built the link on the tunnel (#90), so it opens on a phone as-is. */
export function isPhoneReady(familyUrl: string): boolean {
  try {
    return new URL(familyUrl).protocol === 'https:'
  } catch {
    return false
  }
}

/**
 * The link as the phone should open it. The server's own https link wins (it follows tunnel
 * restarts); a saved tunnel address only stands in for a localhost link.
 */
export function phoneUrl(familyUrl: string, tunnelOrigin: string | null): string {
  if (isPhoneReady(familyUrl) || !tunnelOrigin) return familyUrl
  const u = new URL(familyUrl)
  return tunnelOrigin + u.pathname + u.search
}

/** Kept for this tab only, so Grandma's full-size screen can show the same QR code. */
export const savedFamilyUrl = {
  get(sessionId: string): string | null {
    try {
      return sessionStorage.getItem(familyKey(sessionId))
    } catch {
      return null
    }
  },
  set(sessionId: string, url: string) {
    try {
      sessionStorage.setItem(familyKey(sessionId), url)
    } catch {
      // storage blocked: the QR code shows on the front page only
    }
  },
}

/** "/elder?session=…&token=…" from the server's full elder_url, so it opens on this site. */
export function localPath(url: string): string {
  const u = new URL(url)
  return u.pathname + u.search
}

/**
 * The tunnel's public address as the server sees it (GET /tunnel, #96), checked every 15 s so
 * a restarted tunnel is picked up. null when there's no tunnel or the server can't say.
 */
export async function fetchTunnelOrigin(): Promise<string | null> {
  try {
    const r = await fetch('/tunnel', { credentials: 'include' })
    if (!r.ok) return null
    const data = (await r.json()) as { origin?: unknown }
    return typeof data.origin === 'string' ? cleanTunnel(data.origin) : null
  } catch {
    return null
  }
}
