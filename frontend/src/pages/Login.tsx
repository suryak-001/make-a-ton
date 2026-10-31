import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { homeFor, useAuth } from '@/auth/context'
import { Button, Card, Field } from '@/components/ui'
import { ApiError } from '@/lib/api'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string>()
  const [pending, setPending] = useState(false)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    setPending(true)
    setError(undefined)
    try {
      const user = await login(String(form.get('email')), String(form.get('password')))
      navigate(homeFor(user.role), { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in. Try again.')
    } finally {
      setPending(false)
    }
  }

  return (
    <Card className="p-6">
      <h1 className="text-lg font-semibold">Sign in</h1>
      <p className="mb-4 text-sm text-muted">Welcome back.</p>
      <form onSubmit={onSubmit} className="grid gap-4">
        <Field id="email" name="email" label="Email" type="text" inputMode="email" autoComplete="email" required />
        <Field id="password" name="password" label="Password" type="password" autoComplete="current-password" required />
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button type="submit" disabled={pending}>
          {pending ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
      <div className="mt-4 flex justify-between text-sm">
        <Link to="/forgot-password" className="text-muted hover:underline">
          Forgot password?
        </Link>
        <Link to="/signup" className="hover:underline">
          Create account
        </Link>
      </div>
    </Card>
  )
}
