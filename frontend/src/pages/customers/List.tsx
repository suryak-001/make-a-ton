import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router'
import { DataTable, Pagination } from '@/components/DataTable'
import { ExportLink } from '@/components/ExportLink'
import { Input } from '@/components/forms'
import { Modal } from '@/components/Modal'
import { Badge, Button, PageHeader } from '@/components/ui'
import { api, type Page, qs } from '@/lib/api'
import { useDebounced } from '@/lib/hooks'
import type { Customer } from '@/lib/types'
import { CustomerForm } from './Form'

export default function CustomerList() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState<'new' | null>(null)
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
        actions={
          <>
            <ExportLink path="/customers" params={{ q: debounced }} />
            <Button onClick={() => setEditing('new')}>New customer</Button>
          </>
        }
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
        onRowClick={(c) => navigate(String(c.id))}
        empty={debounced ? 'No customers match your search.' : 'No customers yet.'}
        columns={[
          { header: 'Name', cell: (c) => <span className="font-medium">{c.name}</span> },
          { header: 'Email', cell: (c) => c.email },
          { header: 'Phone', cell: (c) => c.phone ?? '—' },
          { header: 'Portal', cell: (c) => (c.has_login ? <Badge className="bg-green-50 text-green-800">Has login</Badge> : <span className="text-muted">—</span>) },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}

      <Modal open={editing !== null} onClose={() => setEditing(null)} title="New customer">
        {editing !== null && <CustomerForm onDone={() => setEditing(null)} />}
      </Modal>
    </>
  )
}
