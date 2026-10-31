import { useMutation, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { api, ApiError } from '@/lib/api'
import { money, todayISO } from '@/lib/format'
import { PAYMENT_METHODS } from '@/lib/invoices'
import type { Invoice, Payment } from '@/lib/types'
import { Alert, FormField, Input, Select } from './forms'
import { Button, Card } from './ui'

const FIELDS = ['amount', 'payment_date', 'method', 'note']

const emptyPayment = (invoice: Invoice) => ({ method: 'UPI', amount: invoice.outstanding, payment_date: todayISO(), note: '' })

/** Records a payment against a confirmed invoice. The amount starts as the full balance; partial is fine.
 * The page re-mounts it (via `key`) after each payment, so it starts again from the new balance. */
export function PaymentForm({ invoice }: { invoice: Invoice }) {
  const queryClient = useQueryClient()
  const [payment, setPayment] = useState(emptyPayment(invoice))
  const [error, setError] = useState<ApiError>()
  const set = (patch: Partial<typeof payment>) => setPayment((p) => ({ ...p, ...patch }))

  const record = useMutation({
    mutationFn: () => api.post<Payment>('/payments', { invoice_id: invoice.id, ...payment }),
    onSuccess: () => {
      for (const key of ['/invoices', '/payments', '/reports']) queryClient.invalidateQueries({ queryKey: [key] })
    },
    onError: (e) => setError(e instanceof ApiError ? e : new ApiError(0, 'Could not record the payment.')),
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    record.mutate()
  }

  const f = error?.fields ?? {}
  const unshown = error && !Object.keys(f).some((name) => FIELDS.includes(name))
  return (
    <Card className="max-w-5xl p-5">
      <h2 className="font-semibold">Record payment</h2>
      <p className="mt-1 text-sm text-muted">Outstanding {money(invoice.outstanding)}. A smaller amount is a partial payment.</p>
      <form onSubmit={onSubmit} noValidate className="mt-4 grid items-start gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <FormField label="Method" htmlFor="pay-method">
          <Select id="pay-method" value={payment.method} onChange={(e) => set({ method: e.target.value })}>
            {Object.entries(PAYMENT_METHODS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </Select>
        </FormField>
        <FormField label="Amount" htmlFor="pay-amount" error={f.amount}>
          <Input id="pay-amount" inputMode="decimal" value={payment.amount} onChange={(e) => set({ amount: e.target.value })} error={!!f.amount} />
        </FormField>
        <FormField label="Date" htmlFor="pay-date" error={f.payment_date}>
          <Input id="pay-date" type="date" max={todayISO()} value={payment.payment_date} onChange={(e) => set({ payment_date: e.target.value })} error={!!f.payment_date} />
        </FormField>
        <FormField label="Note" htmlFor="pay-note" error={f.note}>
          <Input id="pay-note" value={payment.note} onChange={(e) => set({ note: e.target.value })} placeholder="Optional" />
        </FormField>
        <div className="xl:pt-[26px]">
          <Button type="submit" disabled={record.isPending} className="w-full">{record.isPending ? 'Recording…' : 'Record payment'}</Button>
        </div>
      </form>
      {unshown && <div className="mt-3"><Alert>{error.message}</Alert></div>}
    </Card>
  )
}
