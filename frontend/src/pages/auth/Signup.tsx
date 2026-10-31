import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { homeFor, useAuth } from '@/auth/context'
import { Alert, FormField, Input } from '@/components/forms'
import { PasswordField } from '@/components/PasswordField'
import { AuthPanel } from '@/components/AuthPanel'
import { Button } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { passwordIsValid } from '@/lib/password'

export default function Signup() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<ApiError>()
  const [pending, setPending] = useState(false)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    setError(undefined)
    if (!passwordIsValid(password)) return setError(new ApiError(422, 'Password too weak.', { password: 'Your password doesn’t meet all the rules below.' }))
    if (password !== confirm) return setError(new ApiError(422, 'The two passwords don’t match.', { password: 'The two passwords don’t match.' }))
    setPending(true)
    try {
      const user = await signup(String(f.get('name')), String(f.get('email')), password)
      navigate(homeFor(user.role), { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, 'Could not create the account. Try again.'))
    } finally {
      setPending(false)
    }
  }

  const fields = error?.fields ?? {}
  const unmapped = error && Object.keys(fields).length === 0

  return (
    <AuthPanel
      eyebrow="New account"
      title="Create your account."
      subtitle="Manage your subscriptions and invoices in one place."
      footer={<><span className="text-muted">Already have an account?</span><Link to="/login" className="hover:underline">Sign in</Link></>}
    >
      <form onSubmit={onSubmit} className="grid gap-4" noValidate>
        <FormField label="Name" htmlFor="name" error={fields.name}>
          <Input id="name" name="name" autoComplete="name" required error={!!fields.name} />
        </FormField>
        <FormField label="Email" htmlFor="email" error={fields.email}>
          <Input id="email" name="email" type="email" autoComplete="email" required error={!!fields.email} />
        </FormField>
        <PasswordField id="password" value={password} onChange={setPassword} confirm={confirm} onConfirm={setConfirm} error={fields.password} />
        {unmapped && <Alert>{error.message}</Alert>}
        <Button type="submit" disabled={pending}>
          {pending ? 'Creating account…' : 'Create account'}
        </Button>
      </form>
    </AuthPanel>
  )
}
