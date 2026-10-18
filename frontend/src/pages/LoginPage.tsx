import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const registeredEmail: string | undefined = location.state?.registeredEmail
  const returnTo: string | undefined = location.state?.from

  const [email, setEmail] = useState(registeredEmail ?? '')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const lastViewed = await login(email.trim(), password)
      // Problem 8: land on the last product they looked at, unless they were sent here
      // from another page (for example checkout), which they should go back to.
      navigate(returnTo ?? (lastViewed ? `/products/${encodeURIComponent(lastViewed)}` : '/'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not log in.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="page narrow">
      <h1>Log in</h1>
      {registeredEmail && (
        <p className="form-success">Your account was created. Log in to continue.</p>
      )}
      <form className="auth-form" onSubmit={handleSubmit}>
        <label>
          Email address
          <input
            type="email"
            name="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus={Boolean(registeredEmail)}
            required
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? 'Logging in…' : 'Log in'}
        </button>
      </form>
      <p>
        New to Campus Customs? <Link to="/register">Create an account</Link>
      </p>
    </main>
  )
}
