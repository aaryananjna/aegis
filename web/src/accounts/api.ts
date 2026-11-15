// Family accounts (option D, #34/#35). Calls go to our own origin and Vite forwards them to the
// server, so the httpOnly login cookie stays first-party and the phone works through the tunnel.

export class ApiError extends Error {
  status: number
  retryAfter: number | null
  constructor(status: number, detail: string, retryAfter: number | null) {
    super(detail)
    this.status = status
    this.retryAfter = retryAfter
  }
}

export async function api<T>(
  method: 'GET' | 'POST' | 'DELETE',
  path: string,
  body?: unknown,
  headers: Record<string, string> = {},
): Promise<T> {
  let r: Response
  try {
    r = await fetch(path, {
      method,
      credentials: 'include',
      headers: { ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}), ...headers },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'network', null)
  }
  if (r.status === 204) return undefined as T
  const data = await r.json().catch(() => ({}))
  if (!r.ok) {
    const retry = Number(r.headers.get('Retry-After'))
    const detail = typeof data?.detail === 'string' ? data.detail : ''
    throw new ApiError(r.status, detail, Number.isFinite(retry) && retry > 0 ? retry : null)
  }
  return data as T
}

/** Plain words for every error the accounts endpoints return (#35). */
export function errorMessage(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Something went wrong. Try again.'
  switch (e.status) {
    case 0:
      return "Can't reach Aegis. Check the connection and try again."
    case 401:
      return e.message === 'wrong email or password' ? 'Wrong email or password.' : 'Please log in again.'
    case 403:
      return 'Only the person who added them can do that.'
    case 404:
      return e.message === 'that person needs to sign up first'
        ? 'That person needs to sign up first.'
        : "We couldn't find that person on your account."
    case 409:
      return e.message.includes('email') ? 'An account with that email already exists. Log in instead.'
        : 'Already done.'
    case 422:
      return 'Check the details: a valid email and a password of 8 characters or more.'
    case 429:
      return e.retryAfter
        ? `Too many attempts. Try again in ${e.retryAfter < 120 ? `${e.retryAfter} seconds` : `${Math.ceil(e.retryAfter / 60)} minutes`}.`
        : 'Too many attempts. Try again later.'
    case 503:
      return 'Accounts are offline right now. Live calls still work.'
    default:
      return 'Something went wrong. Try again.'
  }
}

export interface User {
  id: string
  email: string
  display_name: string
}
export interface ElderRef {
  id: string
  display_name: string
  role: 'owner' | 'viewer'
}

/**
 * True for a link that carries its own way in, so it opens without a login: a recorded sample
 * (`?fixture=`), or one live call's link with that call's token (`?session=…&token=…`), which
 * is all /elder asks for too. The server still checks the token on every connect.
 */
export function opensWithoutLogin(search: string): boolean {
  const q = new URLSearchParams(search)
  return q.has('fixture') || Boolean(q.get('session') && q.get('token'))
}

const DEVICE_KEY = 'aegis_device_token'

/** The pairing token from a /pair#<token> link, or null. */
export function tokenFromHash(hash: string): string | null {
  const t = hash.replace(/^#/, '').trim()
  return /^[A-Za-z0-9_-]{16,}$/.test(t) ? t : null
}

export const deviceToken = {
  get(): string | null {
    try {
      return localStorage.getItem(DEVICE_KEY)
    } catch {
      return null
    }
  },
  set(t: string) {
    try {
      localStorage.setItem(DEVICE_KEY, t)
    } catch {
      // storage blocked: pairing works for this visit only
    }
  },
}
