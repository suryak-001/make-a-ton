import { type FormEvent, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { Alert } from '@/components/forms'
import { PasswordField } from '@/components/PasswordField'
import { Button, Card } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { passwordIsValid } from '@/lib/password'

export default function ResetPassword() {
  const token = useSearchParams()[0].get('token')
  const [done, setDone] = useState(false)
  const [error, setError] = useState<ApiError>()
  const [pending, setPending] = useState(false)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(undefined)
    if (!passwordIsValid(password)) return setError(new ApiError(422, 'Password too weak.', { password: 'Your password doesn’t meet all the rules below.' }))
    if (password !== confirm) return setError(new ApiError(422, 'The two passwords don’t match.', { password: 'The two passwords don’t match.' }))
    setPending(true)
    try {
      await api.post('/auth/reset-password', { token, password })
      setDone(true)
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, 'Could not reset the password. Try again.'))
    } finally {
      setPending(false)
    }
  }

  const fields = error?.fields ?? {}

  return (
    <Card className="p-6">
      <h1 className="text-lg font-semibold">Choose a new password</h1>
      {!token ? (
        <div className="mt-4 grid gap-3">
          <Alert>This link is missing its token. Open the link from your email again, or request a new one.</Alert>
          <Link to="/forgot-password" className="text-sm hover:underline">
            Request a new link
          </Link>
        </div>
      ) : done ? (
        <div className="mt-4 grid gap-3">
          <Alert kind="success">Your password has been changed.</Alert>
          <Link to="/login" className="text-sm font-medium hover:underline">
            Sign in
          </Link>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="mt-4 grid gap-4">
          <PasswordField id="password" label="New password" value={password} onChange={setPassword} confirm={confirm} onConfirm={setConfirm} error={fields.password} />
          {error && !fields.password && (
            <>
              <Alert>{error.message}</Alert>
              <Link to="/forgot-password" className="text-sm hover:underline">
                Request a new link
              </Link>
            </>
          )}
          <Button type="submit" disabled={pending}>
            {pending ? 'Saving…' : 'Change password'}
          </Button>
        </form>
      )}
    </Card>
  )
}
