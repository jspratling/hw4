import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

export type User = {
  id: number
  first_name: string
  last_name: string
  email: string
}

type AuthState = {
  user: User | null
  token: string | null
  /** Logs in and returns the last product this shopper looked at, if any (Problem 8). */
  login: (email: string, password: string) => Promise<string | null>
  logout: () => void
  /** Goes up by one on every successful log-in (the chat opens when it changes). */
  loginCount: number
}

const TOKEN_KEY = 'campus-customs-token'

const AuthContext = createContext<AuthState | null>(null)

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage unavailable (e.g. private mode): stay logged in for this tab only.
  }
}

/** Turns a FastAPI error response into a readable message. */
export async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail.length > 0) {
      const first = body.detail[0]
      const field = String(first.loc?.at(-1) ?? '').replace('_', ' ')
      return `${field ? field[0].toUpperCase() + field.slice(1) + ' ' : ''}${String(first.msg).replace(/^Value error, /, '')}`
    }
  } catch {
    // Fall through to the generic message.
  }
  return `Something went wrong (error ${res.status}).`
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(readToken)
  const [user, setUser] = useState<User | null>(null)
  const [loginCount, setLoginCount] = useState(0)

  // Restore the logged-in user after a page reload.
  useEffect(() => {
    if (!token || user) return
    fetch('/api/me', { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then(setUser)
      .catch(() => {
        writeToken(null)
        setToken(null)
      })
  }, [token, user])

  async function login(email: string, password: string) {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) throw new Error(await errorMessage(res))
    const data: { token: string; user: User; last_viewed_product_id: string | null } = await res.json()
    writeToken(data.token)
    setToken(data.token)
    setUser(data.user)
    setLoginCount((n) => n + 1)
    return data.last_viewed_product_id ?? null
  }

  function logout() {
    writeToken(null)
    setToken(null)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, token, login, logout, loginCount }}>{children}</AuthContext.Provider>
}

/** Remember that a logged-in shopper opened a product (Problem 8). Guests are not tracked. */
export function recordView(token: string | null, productId: string) {
  if (!token) return
  fetch('/api/views', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ product_id: productId }),
  }).catch(() => {})
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
