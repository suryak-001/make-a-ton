import { KeyRound, LogOut, Mail, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/auth/context'
import { useSignOut } from '@/auth/useSignOut'
import { Alert } from '@/components/forms'
import { Button, Card, PageHeader } from '@/components/ui'
import { api, ApiError } from '@/lib/api'

const ROLE = { ADMIN: 'Admin', STAFF: 'Staff', CUSTOMER: 'Customer' } as const

/** Opened from the avatar: who you are signed in as, and the account actions that belong to you. */
export default function Profile() {
  const { user } = useAuth()
  const signOut = useSignOut()
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string>()
  const [pending, setPending] = useState(false)
  if (!user) return null

  async function sendReset() {
    setPending(true)
    setError(undefined)
    try {
      await api.post('/auth/forgot-password', { email: user!.email })
      setSent(true)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not send the link. Try again.')
    } finally {
      setPending(false)
    }
  }

  return (
    <>
      <PageHeader title="Profile" description="The account you are signed in with." />
      <div className="grid max-w-2xl gap-5">
        <Card className="flex items-center gap-4 p-5">
          <span className="grid size-16 shrink-0 place-items-center rounded-full bg-brand text-[20px] font-medium text-white">{user.name.slice(0, 2).toUpperCase()}</span>
          <div className="min-w-0">
            <p className="truncate text-[18px] font-medium">{user.name}</p>
            <p className="mt-0.5 flex items-center gap-1.5 truncate text-[13px] text-muted"><Mail className="size-3.5" /> {user.email}</p>
            <p className="mt-0.5 flex items-center gap-1.5 text-[13px] text-muted"><ShieldCheck className="size-3.5" /> {ROLE[user.role]}</p>
          </div>
        </Card>
        <Card className="grid gap-3 p-5">
          <h2 className="flex items-center gap-2 font-medium"><KeyRound className="size-4" /> Password</h2>
          <p className="text-[13px] text-muted">We’ll email you a link to choose a new password. It works for one hour.</p>
          {sent && <Alert kind="success">If the email is registered, a reset link is on its way.</Alert>}
          {error && <Alert>{error}</Alert>}
          <div><Button variant="outline" disabled={pending || sent} onClick={sendReset}>{pending ? 'Sending…' : sent ? 'Link sent' : 'Email me a reset link'}</Button></div>
        </Card>
        <div><Button variant="outline" onClick={signOut}><LogOut className="mr-2 size-4" /> Sign out</Button></div>
      </div>
    </>
  )
}
