import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { LoginError, useAuth } from '../auth'
import PasswordInput from '../components/PasswordInput'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const registeredEmail: string | undefined = location.state?.registeredEmail
  const passwordChanged: boolean = Boolean(location.state?.passwordChanged)
  const returnTo: string | undefined = location.state?.from

  const [email, setEmail] = useState(registeredEmail ?? '')
  // The password always starts empty. It is never pre-filled or saved by the site.
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [resetPrompt, setResetPrompt] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setResetPrompt(false)
    setSubmitting(true)
    try {
      const lastViewed = await login(email.trim(), password)
      setPassword('')
      // Problem 8: land on the last product they looked at, unless they were sent here
      // from another page (for example checkout), which they should go back to.
      navigate(returnTo ?? (lastViewed ? `/products/${encodeURIComponent(lastViewed)}` : '/'))
    } catch (err) {
      setPassword('') // clear a wrong password so it is not left on screen
      setError(err instanceof Error ? err.message : 'Could not log in.')
      setResetPrompt(err instanceof LoginError && err.resetPrompt)
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
      {passwordChanged && (
        <p className="form-success">Your password has been changed. Log in with your new password.</p>
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
          <PasswordInput
            name="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus={Boolean(registeredEmail)}
            required
          />
        </label>
        {resetPrompt ? (
          <div className="reset-prompt" role="alert">
            <p>
              <strong>Please change your password.</strong> {error}
            </p>
            <Link to="/forgot-password" state={{ email: email.trim() }}>
              Didn't get the email? Send a new reset link
            </Link>
          </div>
        ) : (
          error && <p className="form-error">{error}</p>
        )}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? 'Logging in…' : 'Log in'}
        </button>
      </form>
      <p className="form-links">
        <span>
          New to Campus Customs? <Link to="/register">Create an account</Link>
        </span>
        <Link to="/forgot-password" state={{ email: email.trim() }}>
          Forgot password?
        </Link>
      </p>
    </main>
  )
}
