import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '@/auth/context'
import { DataTable, Pagination } from '@/components/DataTable'
import { Input, Select } from '@/components/forms'
import { buttonClass } from '@/components/button-class'
import { Badge, PageHeader } from '@/components/ui'
import { api, type Page, qs } from '@/lib/api'
import { availability, money } from '@/lib/format'
import { useDebounced } from '@/lib/hooks'
import { PERIOD_LABEL, type Plan } from '@/lib/types'

export default function PlanList() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [active, setActive] = useState('')
  const [page, setPage] = useState(1)
  const debounced = useDebounced(q)

  const list = useQuery({
    queryKey: ['plans', debounced, active, page],
    queryFn: () => api.get<Page<Plan>>(`/plans${qs({ q: debounced, active, page })}`),
    placeholderData: keepPreviousData,
  })

  const isAdmin = user?.role === 'ADMIN'
  return (
    <>
      <PageHeader
        title="Plans"
        description={isAdmin ? 'How often a subscription bills, when it is on sale, and what customers or staff can do with it.' : 'Billing plans. Only an admin can change them.'}
        actions={isAdmin && <Link to="new" className={buttonClass()}>New plan</Link>}
      />
      <div className="mb-4 flex gap-3">
        <Input
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setPage(1)
          }}
          placeholder="Search plans…"
          aria-label="Search plans"
          className="max-w-sm"
        />
        <Select
          value={active}
          onChange={(e) => {
            setActive(e.target.value)
            setPage(1)
          }}
          aria-label="Filter by status"
          className="w-40"
        >
          <option value="">All</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </Select>
      </div>
      <DataTable
        loading={list.isPending}
        rows={list.data?.items}
        rowKey={(p) => p.id}
        onRowClick={(p) => navigate(String(p.id))}
        empty="No plans found."
        columns={[
          { header: 'Name', cell: (p) => <span className="font-medium">{p.name}</span> },
          { header: 'Billing', cell: (p) => PERIOD_LABEL[p.billing_period] },
          { header: 'Price', className: 'text-right', cell: (p) => money(p.price) },
          { header: 'Min qty', className: 'text-right', cell: (p) => p.min_quantity },
          { header: 'Available', cell: availability },
          {
            header: 'Rules',
            cell: (p) => (
              <span className="flex flex-wrap gap-1">
                {p.auto_close && <Badge>Auto-closes</Badge>}
                {p.closable && <Badge>Closable</Badge>}
                {p.pausable && <Badge>Pausable</Badge>}
                {p.renewable && <Badge>Renewable</Badge>}
              </span>
            ),
          },
          { header: 'Status', cell: (p) => (p.active ? <Badge className="bg-green-50 text-green-800">Active</Badge> : <Badge className="bg-zinc-100 text-zinc-600">Inactive</Badge>) },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}
    </>
  )
}
