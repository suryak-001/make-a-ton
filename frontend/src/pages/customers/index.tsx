import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { DataTable, Pagination } from '@/components/DataTable'
import { Alert, FormField, Input, Textarea } from '@/components/forms'
import { Modal } from '@/components/Modal'
import { Badge, Button, PageHeader } from '@/components/ui'
import { api, ApiError, type Page, qs } from '@/lib/api'
import { useDebounced } from '@/lib/hooks'
import type { Customer } from '@/lib/types'

export default function CustomersPage() {
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<Customer | 'new' | null>(null)
  const debounced = useDebounced(q)

  const list = useQuery({
    queryKey: ['customers', debounced, page],
    queryFn: () => api.get<Page<Customer>>(`/customers${qs({ q: debounced, page })}`),
    placeholderData: keepPreviousData,
  })

  return (
    <>
      <PageHeader
        title="Customers"
        description="People and companies you bill. A customer can sign in to the portal once they have an account."
        actions={<Button onClick={() => setEditing('new')}>New customer</Button>}
      />
      <Input
        value={q}
        onChange={(e) => {
          setQ(e.target.value)
          setPage(1)
        }}
        placeholder="Search by name or email…"
        aria-label="Search customers"
        className="mb-4 max-w-sm"
      />
      <DataTable
        loading={list.isPending}
        rows={list.data?.items}
        rowKey={(c) => c.id}
        onRowClick={setEditing}
        empty={debounced ? 'No customers match your search.' : 'No customers yet.'}
        columns={[
          { header: 'Name', cell: (c) => <span className="font-medium">{c.name}</span> },
          { header: 'Email', cell: (c) => c.email },
          { header: 'Phone', cell: (c) => c.phone ?? '—' },
          { header: 'Portal', cell: (c) => (c.has_login ? <Badge className="bg-green-50 text-green-800">Has login</Badge> : <span className="text-muted">—</span>) },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}

      <Modal open={editing !== null} onClose={() => setEditing(null)} title={editing === 'new' ? 'New customer' : 'Edit customer'}>
        {editing !== null && <CustomerForm customer={editing === 'new' ? undefined : editing} onDone={() => setEditing(null)} />}
      </Modal>
    </>
  )
}

function CustomerForm({ customer, onDone }: { customer?: Customer; onDone: () => void }) {
  const qc = useQueryClient()
  const [error, setError] = useState<ApiError>()

  const save = useMutation({
    mutationFn: (body: Record<string, string>) =>
      customer ? api.put<Customer>(`/customers/${customer.id}`, body) : api.post<Customer>('/customers', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['customers'] })
      onDone()
    },
    onError: (e) => setError(e instanceof ApiError ? e : new ApiError(0, 'Could not save. Try again.')),
  })

  const remove = useMutation({
    mutationFn: () => api.delete(`/customers/${customer!.id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['customers'] })
      onDone()
    },
    onError: (e) => setError(e instanceof ApiError ? e : new ApiError(0, 'Could not delete. Try again.')),
  })

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(undefined)
    save.mutate(Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>)
  }

  const fields = error?.fields ?? {}
  return (
    <form onSubmit={onSubmit} className="grid gap-4" noValidate>
      <FormField label="Name" htmlFor="name" error={fields.name}>
        <Input id="name" name="name" defaultValue={customer?.name} required error={!!fields.name} />
      </FormField>
      <FormField label="Email" htmlFor="email" error={fields.email}>
        <Input id="email" name="email" type="email" defaultValue={customer?.email} required error={!!fields.email} />
      </FormField>
      <FormField label="Phone" htmlFor="phone" error={fields.phone}>
        <Input id="phone" name="phone" defaultValue={customer?.phone ?? ''} />
      </FormField>
      <FormField label="Address" htmlFor="address" error={fields.address}>
        <Textarea id="address" name="address" defaultValue={customer?.address ?? ''} />
      </FormField>
      {error && Object.keys(fields).length === 0 && <Alert>{error.message}</Alert>}
      <div className="flex items-center justify-between gap-2">
        <div>
          {customer && (
            <Button
              type="button"
              variant="ghost"
              className="text-danger"
              disabled={remove.isPending}
              onClick={() => confirm(`Delete ${customer.name}?`) && remove.mutate()}
            >
              Delete
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={onDone}>
            Cancel
          </Button>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
        </div>
      </div>
    </form>
  )
}
