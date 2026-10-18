import { useState, type FormEvent } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { errorMessage } from '../auth'

/** Ask for a password reset link. It is sent to the email address on file. */
export default function ForgotPasswordPage() {
  const location = useLocation()
  const [email, setEmail] = useState<string>(location.state?.email ?? '')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setMessage(null)
    setSubmitting(true)
    try {
      const res = await fetch('/api/password-reset/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      })
      if (!res.ok) throw new Error(await errorMessage(res))
      setMessage((await res.json()).message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send the reset link.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="page narrow">
      <h1>Reset your password</h1>
      <p>Enter the email address on your account and we'll email you a link to choose a new password.</p>
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
        {message && <p className="form-success">{message}</p>}
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? 'Sending…' : 'Send reset link'}
        </button>
      </form>
      <p>
        <Link to="/login">Back to log in</Link>
      </p>
    </main>
  )
}
