import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { DataTable, Pagination } from '@/components/DataTable'
import { Alert, Checkbox, Select } from '@/components/forms'
import { StatusBadge } from '@/components/StatusBadge'
import { Button, Card, PageHeader } from '@/components/ui'
import { Sheet } from '@/components/Sheet'
import { InvoiceView } from '@/components/InvoiceView'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { DateField } from '@/components/DateField'
import { useToast } from '@/components/Toast'
import { api, ApiError, type Page, qs } from '@/lib/api'
import { formatDate, money, todayISO } from '@/lib/format'
import type { Invoice } from '@/lib/types'

export default function InvoiceList() {
  const qc = useQueryClient(); const { toast } = useToast()
  const [page, setPage] = useState(1); const [status, setStatus] = useState(''); const [overdue, setOverdue] = useState(false); const [asOf, setAsOf] = useState(todayISO()); const [selectedId, setSelectedId] = useState<number>(); const [confirmCancel, setConfirmCancel] = useState(false)
  const list = useQuery({ queryKey: ['/invoices', page, status, overdue], queryFn: () => api.get<Page<Invoice>>(`/invoices${qs({ page, status, overdue: overdue || undefined })}`), placeholderData: keepPreviousData })
  const selected = useQuery({ queryKey: ['/invoices', selectedId], queryFn: () => api.get<Invoice>(`/invoices/${selectedId}`), enabled: Boolean(selectedId) })
  const run = useMutation({ mutationFn: () => api.post<{ created: number; skipped: number; errors: { error: string }[] }>('/invoices/run-billing', { as_of: asOf }), onSuccess: (r) => { toast(`Created ${r.created} invoice${r.created === 1 ? '' : 's'} · ${r.skipped} skipped`); qc.invalidateQueries({ queryKey: ['/invoices'] }); qc.invalidateQueries({ queryKey: ['/reports'] }) }, onError: (e) => toast(e instanceof ApiError ? e.message : 'Billing run failed.') })
  const action = useMutation({ mutationFn: (name: string) => api.post<Invoice>(`/invoices/${selectedId}/${name}`), onSuccess: (value) => { qc.setQueryData(['/invoices', selectedId], value); qc.invalidateQueries({ queryKey: ['/invoices'] }); setConfirmCancel(false); toast('Invoice updated') }, onError: (e) => toast(e instanceof ApiError ? e.message : 'The action failed.') })
  return <>
    <PageHeader title="Invoices" description="Generate recurring invoices, collect payment, and track what is overdue." />
    <Card className="mb-5 flex flex-wrap items-end gap-3 border-ink p-4"><DateField id="billing-date" label="Bill through" value={asOf} onChange={setAsOf} /><Button disabled={run.isPending} onClick={() => run.mutate()}>{run.isPending ? 'Running billing…' : 'Run billing now'}</Button><p className="max-w-lg text-[11px] text-muted">Creates every due period through this date. Running it again is safe.</p></Card>
    <div className="mb-4 flex flex-wrap gap-3 rounded-md border border-line bg-paper p-3"><Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} className="w-full sm:w-48" aria-label="Invoice status"><option value="">All statuses</option><option value="DRAFT">Draft</option><option value="CONFIRMED">Confirmed</option><option value="PAID">Paid</option><option value="CANCELLED">Cancelled</option></Select><Checkbox label="Overdue only" checked={overdue} onChange={(e) => { setOverdue(e.target.checked); setPage(1) }} /></div>
    <DataTable loading={list.isPending} rows={list.data?.items} rowKey={(i) => i.id} onRowClick={(i) => setSelectedId(i.id)} empty="No invoices yet. Run billing when an active subscription is due." columns={[
      { header: 'Invoice', cell: (i) => <span className="font-medium">{i.number ?? `Draft #${i.id}`}</span> }, { header: 'Customer', cell: (i) => i.customer.name }, { header: 'Period', cell: (i) => `${formatDate(i.period_start)} – ${formatDate(i.period_end)}` }, { header: 'Due', cell: (i) => <span className={i.overdue ? 'font-medium text-danger' : ''}>{formatDate(i.due_date)}</span> }, { header: 'Status', cell: (i) => <StatusBadge status={i.status} /> }, { header: 'Total', className: 'text-right', cell: (i) => money(i.total) }, { header: 'Outstanding', className: 'text-right', cell: (i) => money(i.outstanding) },
    ]} />{list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}
    <Sheet open={Boolean(selectedId)} onClose={() => setSelectedId(undefined)} title={selected.data?.number ?? 'Invoice detail'} subtitle="Review and act without losing your place.">
      {selected.isPending ? <p className="text-[13px] text-muted">Loading invoice…</p> : selected.data ? <div className="grid gap-4">
        <div className="flex flex-wrap gap-2">{selected.data.status === 'DRAFT' && <Button disabled={action.isPending} onClick={() => action.mutate('confirm')}>Confirm invoice</Button>}{['DRAFT', 'CONFIRMED'].includes(selected.data.status) && Number(selected.data.amount_paid) === 0 && <Button variant="outline" className="text-danger" disabled={action.isPending} onClick={() => setConfirmCancel(true)}>Cancel</Button>}{['CONFIRMED', 'PAID'].includes(selected.data.status) && <><Button variant="outline" disabled={action.isPending} onClick={() => action.mutate('send')}>Send</Button><a className="inline-flex h-9 items-center border border-ink/25 bg-paper px-3 text-[13px] font-medium hover:bg-yellow" href={`/api/invoices/${selectedId}/print`} target="_blank" rel="noreferrer">Print / PDF</a></>}</div>
        <InvoiceView invoice={selected.data} />
      </div> : <Alert>Could not load this invoice.</Alert>}
    </Sheet>
    <ConfirmDialog open={confirmCancel} onClose={() => setConfirmCancel(false)} onConfirm={() => action.mutate('cancel')} pending={action.isPending} title="Cancel this invoice?" confirmLabel="Cancel invoice">This action cannot be undone. The invoice will remain in the ledger as cancelled.</ConfirmDialog>
  </>
}
