import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { DataTable, Pagination } from '@/components/DataTable'
import { Alert, Checkbox, FormField, Input, Select } from '@/components/forms'
import { Button, Card, PageHeader } from '@/components/ui'
import { api, ApiError, type Page } from '@/lib/api'
import type { Tax } from '@/lib/types'

export default function TaxesPage() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [form, setForm] = useState({ name: '', kind: 'PERCENT', rate: '', active: true })
  const [error, setError] = useState<string>()
  const list = useQuery({ queryKey: ['/taxes', page], queryFn: () => api.get<Page<Tax & { active: boolean }>>(`/taxes?page=${page}`) })
  const save = useMutation({
    mutationFn: () => api.post('/taxes', form),
    onSuccess: () => { setForm({ name: '', kind: 'PERCENT', rate: '', active: true }); setError(undefined); qc.invalidateQueries({ queryKey: ['/taxes'] }) },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not save the tax.'),
  })
  return <>
    <PageHeader title="Taxes" description="Automatic percentage or fixed taxes used by products and invoices." />
    <div className="grid items-start gap-5 xl:grid-cols-[1fr_320px]">
      <div><DataTable loading={list.isPending} rows={list.data?.items} rowKey={(t) => t.id} empty="No tax rules yet." columns={[
        { header: 'Name', cell: (t) => <span className="font-medium">{t.name}</span> },
        { header: 'Type', cell: (t) => t.kind === 'PERCENT' ? 'Percentage' : 'Fixed per unit' },
        { header: 'Rate', className: 'text-right', cell: (t) => t.kind === 'PERCENT' ? `${t.rate}%` : `₹${t.rate}` },
        { header: 'Status', cell: (t) => t.active ? 'Active' : 'Inactive' },
      ]} />{list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}</div>
      <Card className="p-5"><h2 className="font-semibold">New tax rule</h2><form className="mt-4 grid gap-4" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
        <FormField label="Name" htmlFor="tax-name"><Input id="tax-name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></FormField>
        <FormField label="Type" htmlFor="tax-kind"><Select id="tax-kind" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}><option value="PERCENT">Percentage</option><option value="FIXED">Fixed per unit</option></Select></FormField>
        <FormField label={form.kind === 'PERCENT' ? 'Rate (%)' : 'Amount'} htmlFor="tax-rate"><Input id="tax-rate" type="number" min="0" step="0.01" required value={form.rate} onChange={(e) => setForm({ ...form, rate: e.target.value })} /></FormField>
        <Checkbox label="Active" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
        {error && <Alert>{error}</Alert>}<Button type="submit" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Create tax'}</Button>
      </form></Card>
    </div>
  </>
}
