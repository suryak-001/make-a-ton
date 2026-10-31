import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { useAuth } from '@/auth/context'
import { DataTable, Pagination } from '@/components/DataTable'
import { Input, Select } from '@/components/forms'
import { buttonClass } from '@/components/button-class'
import { Badge, PageHeader } from '@/components/ui'
import { api, type Page, qs } from '@/lib/api'
import { money } from '@/lib/format'
import { useDebounced } from '@/lib/hooks'
import type { Product } from '@/lib/types'

export default function ProductList() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [active, setActive] = useState('')
  const [page, setPage] = useState(1)
  const debounced = useDebounced(q)

  const list = useQuery({
    queryKey: ['products', debounced, active, page],
    queryFn: () => api.get<Page<Product>>(`/products${qs({ q: debounced, active, page })}`),
    placeholderData: keepPreviousData,
  })

  const isAdmin = user?.role === 'ADMIN'
  return (
    <>
      <PageHeader
        title="Products"
        description={isAdmin ? 'What you sell, with variants that change the price.' : 'What you sell. Only an admin can change products.'}
        actions={isAdmin && <Link to="new" className={buttonClass()}>New product</Link>}
      />
      <div className="mb-4 flex gap-3">
        <Input
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setPage(1)
          }}
          placeholder="Search products…"
          aria-label="Search products"
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
        empty="No products found."
        columns={[
          { header: 'Name', cell: (p) => <span className="font-medium">{p.name}</span> },
          { header: 'Type', cell: (p) => (p.type === 'SERVICE' ? 'Service' : 'Goods') },
          { header: 'Variants', cell: (p) => (p.variants.length ? p.variants.map((v) => `${v.attribute}: ${v.value}`).join(', ') : <span className="text-muted">—</span>) },
          { header: 'Sales price', className: 'text-right', cell: (p) => money(p.sales_price) },
          { header: 'Cost price', className: 'text-right', cell: (p) => money(p.cost_price) },
          { header: 'Status', cell: (p) => (p.active ? <Badge className="bg-green-50 text-green-800">Active</Badge> : <Badge className="bg-zinc-100 text-zinc-600">Inactive</Badge>) },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}
    </>
  )
}
