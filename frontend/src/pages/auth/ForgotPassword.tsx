import { type FormEvent, useState } from 'react'
import { Link } from 'react-router'
import { Alert, FormField, Input } from '@/components/forms'
import { AuthPanel } from '@/components/AuthPanel'
import { Button } from '@/components/ui'
import { api, ApiError } from '@/lib/api'

export default function ForgotPassword() {
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string>()
  const [pending, setPending] = useState(false)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const email = String(new FormData(e.currentTarget).get('email'))
    setPending(true)
    setError(undefined)
    try {
      await api.post('/auth/forgot-password', { email })
      setSent(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not send the link. Try again.')
    } finally {
      setPending(false)
    }
  }

  return (
    <AuthPanel
      eyebrow="Password help"
      title="Forgot your password?"
      subtitle="Enter your registered email and we’ll send you a link to reset it."
      footer={<Link to="/login" className="text-muted hover:underline">Back to sign in</Link>}
    >
      {sent ? (
        <Alert kind="success">If an account exists for that email, a reset link is on its way. It works for one hour.</Alert>
      ) : (
        <form onSubmit={onSubmit} className="grid gap-4">
          <FormField label="Email" htmlFor="email">
            <Input id="email" name="email" type="email" autoComplete="email" required />
          </FormField>
          {error && <Alert>{error}</Alert>}
          <Button type="submit" disabled={pending}>
            {pending ? 'Sending…' : 'Send reset link'}
          </Button>
        </form>
      )}
    </AuthPanel>
  )
}
