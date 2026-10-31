import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
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
        actions={<Button onClick={() => setAdding(true)}>Add staff member</Button>}
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
  const add = useMutation({
    mutationFn: (body: Record<string, string>) => api.post<UserRow>('/users', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      onDone()
    },
    onError: (e) => setError(e instanceof ApiError ? e : new ApiError(0, 'Could not add the staff member. Try again.')),
  })

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(undefined)
    if (!passwordIsValid(password)) return setError(new ApiError(422, 'Password too weak.', { password: 'The password doesn’t meet all the rules below.' }))
    add.mutate({ ...(Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>), password })
  }

  const fields = error?.fields ?? {}
  return (
    <form onSubmit={onSubmit} className="grid gap-4" noValidate>
      <FormField label="Name" htmlFor="name" error={fields.name}>
        <Input id="name" name="name" required error={!!fields.name} />
      </FormField>
      <FormField label="Email" htmlFor="email" error={fields.email}>
        <Input id="email" name="email" type="email" required error={!!fields.email} />
      </FormField>
      <PasswordField id="password" label="Initial password" value={password} onChange={setPassword} error={fields.password} />
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
