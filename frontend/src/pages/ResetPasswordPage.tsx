import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { errorMessage } from '../auth'
import PasswordInput from '../components/PasswordInput'

const MIN_PASSWORD_LENGTH = 8

/** Opened from the link in the reset email: /reset-password?token=... */
export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const mismatch = confirm.length > 0 && password !== confirm

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch('/api/password-reset/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password, confirm_password: confirm }),
      })
      if (!res.ok) throw new Error(await errorMessage(res))
      setPassword('')
      setConfirm('')
      navigate('/login', { state: { passwordChanged: true } })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not change the password.')
    } finally {
      setSubmitting(false)
    }
  }

  if (!token) {
    return (
      <main className="page narrow">
        <h1>Choose a new password</h1>
        <p className="form-error">This reset link is missing its code.</p>
        <p>
          <Link to="/forgot-password">Ask for a new reset link</Link>
        </p>
      </main>
    )
  }

  return (
    <main className="page narrow">
      <h1>Choose a new password</h1>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label>
          New password
          <PasswordInput
            name="new_password"
            minLength={MIN_PASSWORD_LENGTH}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <span className="field-hint">At least {MIN_PASSWORD_LENGTH} characters.</span>
        </label>
        <label>
          Confirm new password
          <PasswordInput
            name="confirm_password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            aria-invalid={mismatch}
            required
          />
          {mismatch && <span className="field-error">Passwords do not match.</span>}
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="button" disabled={submitting || mismatch}>
          {submitting ? 'Saving…' : 'Change password'}
        </button>
      </form>
      <p>
        <Link to="/forgot-password">Need a new link?</Link>
      </p>
    </main>
  )
}
