import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { ActiveBadge } from '@/components/ActiveBadge'
import { buttonClass } from '@/components/button-class'
import { DataTable, Pagination } from '@/components/DataTable'
import { Input, Select } from '@/components/forms'
import { PageHeader } from '@/components/ui'
import { api, type Page, qs } from '@/lib/api'
import { discountValueLabel } from '@/lib/discounts'
import { formatDate } from '@/lib/format'
import { useDebounced } from '@/lib/hooks'
import type { Discount } from '@/lib/types'

const usage = (d: Discount) => (d.usage_limit ? `${d.used_count} of ${d.usage_limit}` : `${d.used_count} (no limit)`)
const validity = (d: Discount) => `${formatDate(d.start_date)} → ${d.end_date ? formatDate(d.end_date) : 'open-ended'}`

export default function DiscountList() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [active, setActive] = useState('')
  const [page, setPage] = useState(1)
  const q = useDebounced(search)

  const list = useQuery({
    queryKey: ['/discounts', q, active, page],
    queryFn: () => api.get<Page<Discount>>(`/discounts${qs({ q, active, page })}`),
    placeholderData: keepPreviousData,
  })

  return (
    <>
      <PageHeader
        title="Discounts"
        description="An eligible discount appears on the next invoice by itself, and stops when it expires or its limit is used up."
        actions={<Link to="new" className={buttonClass()}>New discount</Link>}
      />
      <div className="mb-4 flex gap-3">
        <Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} placeholder="Search discounts…" aria-label="Search discounts" className="max-w-sm" />
        <Select value={active} onChange={(e) => { setActive(e.target.value); setPage(1) }} aria-label="Filter by status" className="w-40">
          <option value="">All</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </Select>
      </div>
      <DataTable
        loading={list.isPending}
        rows={list.data?.items}
        rowKey={(d) => d.id}
        onRowClick={(d) => navigate(String(d.id))}
        empty="No discounts found."
        columns={[
          { header: 'Rule', cell: (d) => <div><p className="font-medium">{d.name}</p><p className="text-xs text-muted">{d.scope === 'PRODUCT' ? 'Specific products' : 'Specific subscriptions'}</p></div> },
          { header: 'Value', cell: discountValueLabel },
          { header: 'Window', cell: validity },
          { header: 'Used', cell: usage },
          { header: 'Status', cell: (d) => <ActiveBadge active={d.active} /> },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}
    </>
  )
}
