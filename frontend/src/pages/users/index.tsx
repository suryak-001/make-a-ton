import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Copy, MessageCircle, Plus } from 'lucide-react'
import { type FormEvent, useState } from 'react'
import { DataTable, Pagination } from '@/components/DataTable'
import { Alert, FormField, Input, Select } from '@/components/forms'
import { PasswordField } from '@/components/PasswordField'
import { Modal } from '@/components/Modal'
import { Badge, Button, PageHeader } from '@/components/ui'
import { api, ApiError, type Page, qs } from '@/lib/api'
import { useDebounced } from '@/lib/hooks'
import { passwordIsValid } from '@/lib/password'
import { formatDate } from '@/lib/format'
import type { UserRow } from '@/lib/types'

const ROLE_TONE = { ADMIN: 'bg-brand/10 text-brand', STAFF: 'bg-sky-50 text-sky-800', CUSTOMER: 'bg-surface text-muted' } as const

export default function UsersPage() {
  const [q, setQ] = useState('')
  const [role, setRole] = useState('')
  const [page, setPage] = useState(1)
  const [adding, setAdding] = useState(false)
  const debounced = useDebounced(q)

  const list = useQuery({
    queryKey: ['users', debounced, role, page],
    queryFn: () => api.get<Page<UserRow>>(`/users${qs({ q: debounced, role, page })}`),
    placeholderData: keepPreviousData,
  })

  return (
    <>
      <PageHeader
        title="Users"
        description="Only an admin can add staff. Customers create their own accounts when they sign up."
        actions={<Button onClick={() => setAdding(true)}><Plus className="mr-1.5 size-4" /> Add staff member</Button>}
      />
      <div className="mb-4 flex gap-3">
        <Input
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setPage(1)
          }}
          placeholder="Search by name or email…"
          aria-label="Search users"
          className="max-w-sm"
        />
        <Select
          value={role}
          onChange={(e) => {
            setRole(e.target.value)
            setPage(1)
          }}
          aria-label="Filter by role"
          className="w-40"
        >
          <option value="">All roles</option>
          <option value="ADMIN">Admin</option>
          <option value="STAFF">Staff</option>
          <option value="CUSTOMER">Customer</option>
        </Select>
      </div>
      <DataTable
        loading={list.isPending}
        rows={list.data?.items}
        rowKey={(u) => u.id}
        columns={[
          { header: 'Name', cell: (u) => <span className="font-medium">{u.name}</span> },
          { header: 'Email', cell: (u) => u.email },
          { header: 'Role', cell: (u) => <Badge className={ROLE_TONE[u.role]}>{u.role.charAt(0) + u.role.slice(1).toLowerCase()}</Badge> },
          { header: 'Joined', cell: (u) => formatDate(u.created_at) },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}

      <Modal open={adding} onClose={() => setAdding(false)} title="Add staff member">
        {adding && <AddStaffForm onDone={() => setAdding(false)} />}
      </Modal>
    </>
  )
}

function AddStaffForm({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient()
  const [error, setError] = useState<ApiError>()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [invite, setInvite] = useState<{ name: string; email: string; password: string }>()
  const add = useMutation({
    mutationFn: (body: Record<string, string>) => api.post<UserRow>('/users', body),
    onSuccess: (user) => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setInvite({ name: user.name, email: user.email, password })
    },
    onError: (e) => setError(e instanceof ApiError ? e : new ApiError(0, 'Could not add the staff member. Try again.')),
  })

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(undefined)
    if (!passwordIsValid(password)) return setError(new ApiError(422, 'Password too weak.', { password: 'The password doesn’t meet all the rules below.' }))
    if (password !== confirm) return setError(new ApiError(422, 'The two passwords don’t match.', { password: 'The two passwords don’t match.' }))
    add.mutate({ ...(Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>), password })
  }

  if (invite) return <InviteCard invite={invite} onDone={onDone} />

  const fields = error?.fields ?? {}
  return (
    <form onSubmit={onSubmit} className="grid gap-4" noValidate>
      <FormField label="Name" htmlFor="name" error={fields.name}>
        <Input id="name" name="name" required error={!!fields.name} />
      </FormField>
      <FormField label="Email" htmlFor="email" error={fields.email}>
        <Input id="email" name="email" type="email" required error={!!fields.email} />
      </FormField>
      <PasswordField id="password" label="Initial password" value={password} onChange={setPassword} confirm={confirm} onConfirm={setConfirm} error={fields.password} />
      {error && Object.keys(fields).length === 0 && <Alert>{error.message}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={add.isPending}>
          {add.isPending ? 'Adding…' : 'Add staff member'}
        </Button>
      </div>
    </form>
  )
}

/** Shown right after a staff member is added: a ready message to paste into WhatsApp, email or chat. */
function InviteCard({ invite, onDone }: { invite: { name: string; email: string; password: string }; onDone: () => void }) {
  const [copied, setCopied] = useState(false)
  const message = [
    `Hi ${invite.name}, welcome to Brightloop! You have been added as a staff member.`,
    '',
    `Sign in: ${window.location.origin}/login`,
    `Email: ${invite.email}`,
    `Password: ${invite.password}`,
    '',
    'This password is temporary: you will choose your own the first time you sign in.',
  ].join('\n')

  async function copy() {
    try {
      await navigator.clipboard.writeText(message)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="grid gap-4">
      <p className="flex items-center gap-2 text-[13px] font-medium text-green"><Check className="size-4" /> {invite.name} was added as staff.</p>
      <p className="text-[13px] text-muted">Send them this message. The password is only shown now, so copy it before you close this window.</p>
      <pre className="whitespace-pre-wrap rounded-md border border-line bg-surface p-3 text-[12px] leading-5">{message}</pre>
      <div className="flex flex-wrap justify-end gap-2">
        <a href={`https://wa.me/?text=${encodeURIComponent(message)}`} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center gap-1.5 rounded-md border border-line px-3 text-[13px] font-medium hover:bg-surface"><MessageCircle className="size-4" /> WhatsApp</a>
        <Button type="button" variant="outline" onClick={copy}>{copied ? <><Check className="mr-1.5 size-4" /> Copied</> : <><Copy className="mr-1.5 size-4" /> Copy invite</>}</Button>
        <Button type="button" onClick={onDone}>Done</Button>
      </div>
    </div>
  )
}
