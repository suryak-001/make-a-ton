import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router'
import { homeFor, useAuth } from '@/auth/context'
import { useSignOut } from '@/auth/useSignOut'
import { Alert, FormField, Input } from '@/components/forms'
import { AuthPanel } from '@/components/AuthPanel'
import { PasswordField } from '@/components/PasswordField'
import { Button } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { passwordIsValid } from '@/lib/password'

/** First sign-in for staff an admin added: replace the password the admin chose. */
export default function ChangePassword() {
  const { user, refresh } = useAuth()
  const signOut = useSignOut()
  const navigate = useNavigate()
  const [current, setCurrent] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<ApiError>()
  const [pending, setPending] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    if (!passwordIsValid(password)) return setError(new ApiError(422, 'Password too weak.', { new_password: 'Your password doesn’t meet all the rules below.' }))
    if (password !== confirm) return setError(new ApiError(422, 'The two passwords don’t match.', { new_password: 'The two passwords don’t match.' }))
    setPending(true)
    try {
      await api.post('/auth/change-password', { current_password: current, new_password: password })
      await refresh()
      navigate(homeFor(user!.role), { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err : new ApiError(0, 'Could not change the password. Try again.'))
    } finally {
      setPending(false)
    }
  }

  const fields = error?.fields ?? {}
  return (
    <AuthPanel
      eyebrow="First sign-in"
      title="Choose your password."
      subtitle={`Hi ${user?.name ?? ''}, the password you were given is temporary. Pick one only you know.`}
      footer={<button type="button" className="text-muted hover:underline" onClick={signOut}>Sign out</button>}
    >
      <form onSubmit={onSubmit} className="grid gap-4" noValidate>
        <FormField label="Password you were given" htmlFor="current" error={fields.current_password}>
          <Input id="current" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} required error={!!fields.current_password} />
        </FormField>
        <PasswordField id="new-password" label="New password" value={password} onChange={setPassword} confirm={confirm} onConfirm={setConfirm} error={fields.new_password} />
        {error && Object.keys(fields).length === 0 && <Alert>{error.message}</Alert>}
        <Button type="submit" disabled={pending}>{pending ? 'Saving…' : 'Save and continue'}</Button>
      </form>
    </AuthPanel>
  )
}
