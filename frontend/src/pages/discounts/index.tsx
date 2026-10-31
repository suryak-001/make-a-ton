import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { DataTable } from '@/components/DataTable'
import { Alert, Checkbox, FormField, Input, Select } from '@/components/forms'
import { Button, Card, PageHeader } from '@/components/ui'
import { api, ApiError, type Page } from '@/lib/api'
import { formatDate, todayISO } from '@/lib/format'
import { useProducts } from '@/lib/queries'
import type { Discount, SubListItem } from '@/lib/types'

export default function DiscountsPage() {
  const qc = useQueryClient()
  const products = useProducts()
  const subs = useQuery({ queryKey: ['/subscriptions', 'discount-options'], queryFn: () => api.get<Page<SubListItem>>('/subscriptions?page_size=100') })
  const list = useQuery({ queryKey: ['/discounts'], queryFn: () => api.get<Page<Discount>>('/discounts?page_size=100') })
  const [form, setForm] = useState({ name: '', kind: 'PERCENT', value: '', min_purchase: '', min_quantity: '', start_date: todayISO(), end_date: '', usage_limit: '', scope: 'PRODUCT', target_id: '', active: true })
  const [error, setError] = useState<string>()
  const save = useMutation({
    mutationFn: () => api.post('/discounts', { ...form, min_purchase: form.min_purchase || null, min_quantity: form.min_quantity ? Number(form.min_quantity) : null, end_date: form.end_date || null, usage_limit: form.usage_limit ? Number(form.usage_limit) : null, product_ids: form.scope === 'PRODUCT' ? [Number(form.target_id)] : [], subscription_ids: form.scope === 'SUBSCRIPTION' ? [Number(form.target_id)] : [] }),
    onSuccess: () => { setError(undefined); setForm({ ...form, name: '', value: '', target_id: '' }); qc.invalidateQueries({ queryKey: ['/discounts'] }) },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not save the discount.'),
  })
  const targets = form.scope === 'PRODUCT' ? products.data?.map((p) => ({ id: p.id, label: p.name })) : subs.data?.items.map((s) => ({ id: s.id, label: `${s.number} · ${s.customer.name}` }))
  return <>
    <PageHeader title="Discounts" description="Automatic product and subscription offers with date and usage controls." />
    <div className="grid items-start gap-5 2xl:grid-cols-[1fr_380px]">
      <DataTable loading={list.isPending} rows={list.data?.items} rowKey={(d) => d.id} empty="No discount rules yet." columns={[
        { header: 'Rule', cell: (d) => <div><p className="font-medium">{d.name}</p><p className="text-xs text-muted">{d.scope.toLowerCase()}</p></div> },
        { header: 'Value', cell: (d) => d.kind === 'PERCENT' ? `${d.value}%` : `₹${d.value}` },
        { header: 'Window', cell: (d) => `${formatDate(d.start_date)} – ${formatDate(d.end_date)}` },
        { header: 'Usage', cell: (d) => `${d.used_count}${d.usage_limit ? ` / ${d.usage_limit}` : ''}` },
        { header: 'Status', cell: (d) => d.active ? 'Active' : 'Inactive' },
      ]} />
      <Card className="p-5"><h2 className="font-semibold">New discount</h2><form className="mt-4 grid gap-4" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
        <FormField label="Name" htmlFor="discount-name"><Input id="discount-name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></FormField>
        <div className="grid grid-cols-2 gap-3"><FormField label="Type" htmlFor="discount-kind"><Select id="discount-kind" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}><option value="PERCENT">Percentage</option><option value="FIXED">Fixed</option></Select></FormField><FormField label="Value" htmlFor="discount-value"><Input id="discount-value" type="number" min="0" step="0.01" required value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} /></FormField></div>
        <div className="grid grid-cols-2 gap-3"><FormField label="Scope" htmlFor="discount-scope"><Select id="discount-scope" value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value, target_id: '' })}><option value="PRODUCT">Product</option><option value="SUBSCRIPTION">Subscription</option></Select></FormField><FormField label="Applies to" htmlFor="discount-target"><Select id="discount-target" required value={form.target_id} onChange={(e) => setForm({ ...form, target_id: e.target.value })}><option value="">Select…</option>{targets?.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}</Select></FormField></div>
        <div className="grid grid-cols-2 gap-3"><FormField label="Starts" htmlFor="discount-start"><Input id="discount-start" type="date" required value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} /></FormField><FormField label="Ends" htmlFor="discount-end"><Input id="discount-end" type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></FormField></div>
        <div className="grid grid-cols-3 gap-3"><FormField label="Min amount" htmlFor="discount-min"><Input id="discount-min" type="number" min="0" value={form.min_purchase} onChange={(e) => setForm({ ...form, min_purchase: e.target.value })} /></FormField><FormField label="Min qty" htmlFor="discount-qty"><Input id="discount-qty" type="number" min="1" value={form.min_quantity} onChange={(e) => setForm({ ...form, min_quantity: e.target.value })} /></FormField><FormField label="Use limit" htmlFor="discount-limit"><Input id="discount-limit" type="number" min="1" value={form.usage_limit} onChange={(e) => setForm({ ...form, usage_limit: e.target.value })} /></FormField></div>
        <Checkbox label="Active" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />{error && <Alert>{error}</Alert>}<Button type="submit" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Create discount'}</Button>
      </form></Card>
    </div>
  </>
}
