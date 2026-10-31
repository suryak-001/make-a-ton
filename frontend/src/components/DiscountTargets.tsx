import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type Page, qs } from '@/lib/api'
import { useDebounced } from '@/lib/hooks'
import { useProducts } from '@/lib/queries'
import type { SubListItem } from '@/lib/types'
import { CheckList } from './CheckList'
import { Input } from './forms'

export function ProductTargets({ selected, onChange }: { selected: number[]; onChange: (ids: number[]) => void }) {
  const products = useProducts()
  const options = (products.data ?? []).map((p) => ({ id: p.id, label: p.name }))
  return <CheckList options={options} selected={selected} onChange={onChange} empty={products.isPending ? 'Loading products…' : 'No products yet.'} />
}

/** Subscriptions are too many to list at once, so they are found by searching. */
export function SubscriptionTargets({ selected, onChange }: { selected: number[]; onChange: (ids: number[]) => void }) {
  const [search, setSearch] = useState('')
  const q = useDebounced(search)
  const found = useQuery({
    queryKey: ['/subscriptions', 'discount-targets', q],
    queryFn: () => api.get<Page<SubListItem>>(`/subscriptions${qs({ q, page_size: 20 })}`),
  })
  const options = (found.data?.items ?? []).map((s) => ({ id: s.id, label: `${s.number} · ${s.customer.name}` }))
  return (
    <div className="grid gap-2">
      <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by number or customer…" aria-label="Search subscriptions" />
      <CheckList options={options} selected={selected} onChange={onChange} empty={found.isPending ? 'Searching…' : 'No subscriptions found.'} />
      <p className="text-xs text-muted">{selected.length} selected</p>
    </div>
  )
}
