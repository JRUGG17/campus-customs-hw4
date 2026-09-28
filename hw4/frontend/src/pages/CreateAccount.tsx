import { useState, type ChangeEvent, type SubmitEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import type { SignupInput } from '../api'
import { useAuth } from '../auth'

const EMPTY: SignupInput = {
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  confirm_password: '',
}

export default function CreateAccount() {
  const { user, signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<SignupInput>(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/" replace />

  const update = (e: ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value })
    setError(null)
  }

  const mismatch = form.confirm_password !== '' && form.password !== form.confirm_password

  async function handleSubmit(e: SubmitEvent<HTMLFormElement>) {
    e.preventDefault()
    if (mismatch) return
    setError(null)
    setSubmitting(true)
    try {
      await signup(form)
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="container auth-page">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Create an account</h1>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="form-row">
          <label>
            First name
            <input name="first_name" required autoComplete="given-name" value={form.first_name} onChange={update} />
          </label>
          <label>
            Last name
            <input name="last_name" required autoComplete="family-name" value={form.last_name} onChange={update} />
          </label>
        </div>
        <label>
          Email
          <input type="email" name="email" required autoComplete="email" value={form.email} onChange={update} />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={form.password}
            onChange={update}
          />
          <span className="hint">At least 8 characters.</span>
        </label>
        <label>
          Confirm password
          <input
            type="password"
            name="confirm_password"
            required
            autoComplete="new-password"
            value={form.confirm_password}
            onChange={update}
            aria-invalid={mismatch}
          />
          {mismatch && <span className="field-error">Passwords don't match.</span>}
        </label>
        <button type="submit" className="btn btn-primary" disabled={submitting || mismatch}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
        <p className="small">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  )
}
