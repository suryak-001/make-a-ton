import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Plus } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { buttonClass } from '@/components/button-class'
import { DataTable, Pagination } from '@/components/DataTable'
import { EntityRowMenu, EntityStatus } from '@/components/EntityRow'
import { useFlashId } from '@/lib/flash'
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
  const flash = useFlashId()
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
        actions={<Link to="/discounts/new" className={buttonClass('primary', 'gap-1.5')}><Plus className="size-4" /> New discount</Link>}
      />
      <div className="mb-5 flex flex-wrap gap-3">
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
        onRowClick={(d) => navigate(`/discounts/${d.id}`)}
        empty="No discounts found."
        flashId={flash}
        actions={(d) => <EntityRowMenu path="/discounts" id={d.id} name={d.name} active={d.active} label="this discount" />}
        columns={[
          { header: 'Rule', cell: (d) => <div><p className="font-medium">{d.name}</p><p className="text-xs text-muted">{d.scope === 'PRODUCT' ? 'Specific products' : 'Specific subscriptions'}</p></div> },
          { header: 'Value', cell: discountValueLabel },
          { header: 'Window', cell: validity },
          { header: 'Used', cell: usage },
          { header: 'Status', cell: (d) => <EntityStatus path="/discounts" id={d.id} active={d.active} /> },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}
    </>
  )
}
