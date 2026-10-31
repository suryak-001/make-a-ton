import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { homeFor, useAuth } from '@/auth/context'
import { AuthPanel } from '@/components/AuthPanel'
import { Button, Field } from '@/components/ui'
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
    <AuthPanel
      eyebrow="Workspace access"
      title="Welcome back."
      subtitle="Sign in to continue to your workspace."
      footer={<>
        <Link to="/forgot-password" className="text-muted hover:underline">Forgot password?</Link>
        <Link to="/signup" className="hover:underline">Create account</Link>
      </>}
    >
      <form onSubmit={onSubmit} className="grid gap-4">
        <Field id="email" name="email" label="Email" type="text" inputMode="email" autoComplete="email" required />
        <Field id="password" name="password" label="Password" type="password" autoComplete="current-password" required />
        {error && <p className="border-l-4 border-danger bg-danger/5 px-3 py-2 text-[12px] text-danger">{error}</p>}
        <Button type="submit" disabled={pending}>
          {pending ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
    </AuthPanel>
  )
}
