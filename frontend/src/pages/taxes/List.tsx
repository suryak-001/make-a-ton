import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { buttonClass } from '@/components/button-class'
import { DataTable, Pagination } from '@/components/DataTable'
import { Input, Select } from '@/components/forms'
import { ActiveBadge } from '@/components/ActiveBadge'
import { PageHeader } from '@/components/ui'
import { api, type Page, qs } from '@/lib/api'
import { useDebounced } from '@/lib/hooks'
import { taxRateLabel } from '@/lib/tax'
import type { TaxRule } from '@/lib/types'

export default function TaxList() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [active, setActive] = useState('')
  const [page, setPage] = useState(1)
  const q = useDebounced(search)

  const list = useQuery({
    queryKey: ['/taxes', q, active, page],
    queryFn: () => api.get<Page<TaxRule>>(`/taxes${qs({ q, active, page })}`),
    placeholderData: keepPreviousData,
  })

  return (
    <>
      <PageHeader
        title="Taxes"
        description="Tax rules are attached to products and applied to every quote and invoice line automatically."
        actions={<Link to="new" className={buttonClass()}>New tax</Link>}
      />
      <div className="mb-4 flex gap-3">
        <Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1) }} placeholder="Search taxes…" aria-label="Search taxes" className="max-w-sm" />
        <Select value={active} onChange={(e) => { setActive(e.target.value); setPage(1) }} aria-label="Filter by status" className="w-40">
          <option value="">All</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </Select>
      </div>
      <DataTable
        loading={list.isPending}
        rows={list.data?.items}
        rowKey={(tax) => tax.id}
        onRowClick={(tax) => navigate(String(tax.id))}
        empty="No taxes found."
        columns={[
          { header: 'Name', cell: (tax) => <span className="font-medium">{tax.name}</span> },
          { header: 'Type', cell: (tax) => (tax.kind === 'PERCENT' ? 'Percentage' : 'Fixed per unit') },
          { header: 'Rate', className: 'text-right', cell: taxRateLabel },
          { header: 'Status', cell: (tax) => <ActiveBadge active={tax.active} /> },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}
    </>
  )
}
