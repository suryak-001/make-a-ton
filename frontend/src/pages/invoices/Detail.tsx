import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { InvoiceView } from '@/components/InvoiceView'
import { Alert, FormField, Input, Select } from '@/components/forms'
import { Button, Card, PageHeader } from '@/components/ui'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { api, ApiError } from '@/lib/api'
import { money, todayISO } from '@/lib/format'
import type { Invoice } from '@/lib/types'

export default function InvoiceDetail() {
  const { id } = useParams(); const qc = useQueryClient(); const [error, setError] = useState<string>(); const [confirmCancel, setConfirmCancel] = useState(false); const [payment, setPayment] = useState({ method: 'UPI', amount: '', payment_date: todayISO(), note: '' })
  const invoice = useQuery({ queryKey: ['/invoices', Number(id)], queryFn: () => api.get<Invoice>(`/invoices/${id}`) })
  const action = useMutation({ mutationFn: (name: string) => api.post<Invoice>(`/invoices/${id}/${name}`), onSuccess: (value) => { qc.setQueryData(['/invoices', Number(id)], value); qc.invalidateQueries({ queryKey: ['/invoices'] }); setError(undefined); setConfirmCancel(false) }, onError: (e) => setError(e instanceof ApiError ? e.message : 'The action failed.') })
  const pay = useMutation({ mutationFn: () => api.post('/payments', { invoice_id: Number(id), ...payment }), onSuccess: () => { setPayment({ ...payment, amount: '', note: '' }); qc.invalidateQueries({ queryKey: ['/invoices'] }); qc.invalidateQueries({ queryKey: ['/payments'] }) }, onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not record payment.') })
  const data = invoice.data
  return <><PageHeader title={data?.number ?? 'Invoice detail'} actions={<Link to="/invoices" className="text-sm text-muted hover:underline">← All invoices</Link>} />
    {invoice.isPending ? <p className="text-sm text-muted">Loading…</p> : invoice.isError || !data ? <Alert>Could not load this invoice.</Alert> : <div className="grid gap-5">
      <div className="flex flex-wrap gap-2">{data.status === 'DRAFT' && <Button disabled={action.isPending} onClick={() => action.mutate('confirm')}>Confirm invoice</Button>}{['DRAFT', 'CONFIRMED'].includes(data.status) && Number(data.amount_paid) === 0 && <Button variant="outline" className="text-danger" disabled={action.isPending} onClick={() => setConfirmCancel(true)}>Cancel</Button>}{['CONFIRMED', 'PAID'].includes(data.status) && <><Button variant="outline" disabled={action.isPending} onClick={() => action.mutate('send')}>Send</Button><a className="inline-flex h-9 items-center border border-ink/25 bg-paper px-3 text-[13px] font-medium hover:bg-yellow" href={`/api/invoices/${id}/print`} target="_blank" rel="noreferrer">Print / PDF</a></>}</div>
      {error && <Alert>{error}</Alert>}<InvoiceView invoice={data} />
      {data.status === 'CONFIRMED' && Number(data.outstanding) > 0 && <Card className="max-w-5xl p-5"><h2 className="font-semibold">Record payment</h2><p className="mt-1 text-sm text-muted">Outstanding {money(data.outstanding)}</p><form className="mt-4 grid items-end gap-3 sm:grid-cols-4" onSubmit={(e) => { e.preventDefault(); pay.mutate() }}><FormField label="Method" htmlFor="pay-method"><Select id="pay-method" value={payment.method} onChange={(e) => setPayment({ ...payment, method: e.target.value })}><option value="UPI">UPI</option><option value="BANK_TRANSFER">Bank transfer</option><option value="CARD">Card</option><option value="CASH">Cash</option><option value="CHEQUE">Cheque</option><option value="OTHER">Other</option></Select></FormField><FormField label="Amount" htmlFor="pay-amount"><Input id="pay-amount" type="number" min="0.01" step="0.01" max={data.outstanding} required value={payment.amount} onChange={(e) => setPayment({ ...payment, amount: e.target.value })} /></FormField><FormField label="Date" htmlFor="pay-date"><Input id="pay-date" type="date" required value={payment.payment_date} onChange={(e) => setPayment({ ...payment, payment_date: e.target.value })} /></FormField><Button type="submit" disabled={pay.isPending}>{pay.isPending ? 'Recording…' : 'Record payment'}</Button></form></Card>}
    </div>}
    <ConfirmDialog open={confirmCancel} onClose={() => setConfirmCancel(false)} onConfirm={() => action.mutate('cancel')} pending={action.isPending} title="Cancel this invoice?" confirmLabel="Cancel invoice">This action cannot be undone. The invoice will remain in the ledger as cancelled.</ConfirmDialog>
  </>
}
