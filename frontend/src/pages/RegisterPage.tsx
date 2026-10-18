import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { errorMessage } from '../auth'

const MIN_PASSWORD_LENGTH = 8

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm_password: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const passwordsMismatch =
    form.confirm_password.length > 0 && form.password !== form.confirm_password

  function update(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error(await errorMessage(res))
      navigate('/login', { state: { registeredEmail: form.email.trim() } })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create account.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="page narrow">
      <h1>Create account</h1>
      <form className="auth-form" onSubmit={handleSubmit} noValidate={false}>
        <div className="form-row">
          <label>
            First name
            <input
              name="first_name"
              autoComplete="given-name"
              value={form.first_name}
              onChange={update('first_name')}
              required
            />
          </label>
          <label>
            Last name
            <input
              name="last_name"
              autoComplete="family-name"
              value={form.last_name}
              onChange={update('last_name')}
              required
            />
          </label>
        </div>
        <label>
          Email address
          <input
            type="email"
            name="email"
            autoComplete="email"
            value={form.email}
            onChange={update('email')}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="new-password"
            minLength={MIN_PASSWORD_LENGTH}
            value={form.password}
            onChange={update('password')}
            required
          />
          <span className="field-hint">At least {MIN_PASSWORD_LENGTH} characters.</span>
        </label>
        <label>
          Confirm password
          <input
            type="password"
            name="confirm_password"
            autoComplete="new-password"
            value={form.confirm_password}
            onChange={update('confirm_password')}
            aria-invalid={passwordsMismatch}
            required
          />
          {passwordsMismatch && <span className="field-error">Passwords do not match.</span>}
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="button" disabled={submitting || passwordsMismatch}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </main>
  )
}
