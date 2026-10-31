import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { buttonClass } from '@/components/button-class'
import { DateField } from '@/components/DateField'
import { DataTable, Pagination } from '@/components/DataTable'
import { ExportLink } from '@/components/ExportLink'
import { FormField, Select } from '@/components/forms'
import { PageHeader } from '@/components/ui'
import { api, type Page, qs } from '@/lib/api'
import { formatDate, money } from '@/lib/format'
import { PAYMENT_METHODS } from '@/lib/invoices'
import type { Payment } from '@/lib/types'

export default function PaymentsPage() {
  const [method, setMethod] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [page, setPage] = useState(1)
  const filter = (apply: () => void) => {
    apply()
    setPage(1)
  }

  const list = useQuery({
    queryKey: ['/payments', method, from, to, page],
    queryFn: () => api.get<Page<Payment>>(`/payments${qs({ method, from_date: from, to_date: to, page })}`),
    placeholderData: keepPreviousData,
  })

  return (
    <>
      <PageHeader
        title="Payments"
        description="Money received and the invoices it settled. Record a payment from the invoice itself, or match a bank statement."
        actions={
          <>
            <ExportLink path="/payments" params={{ method, from_date: from, to_date: to }} />
            <Link to="/reconciliation" className={buttonClass()}>Match bank statement</Link>
          </>
        }
      />
      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-md border border-line bg-paper p-3">
        <FormField label="Method" htmlFor="payment-method">
          <Select id="payment-method" value={method} onChange={(e) => filter(() => setMethod(e.target.value))} className="w-44">
            <option value="">All methods</option>
            {Object.entries(PAYMENT_METHODS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </Select>
        </FormField>
        <DateField id="payment-from" label="From" value={from} onChange={(v) => filter(() => setFrom(v))} optional />
        <DateField id="payment-to" label="To" value={to} onChange={(v) => filter(() => setTo(v))} optional />
      </div>
      <DataTable
        loading={list.isPending}
        rows={list.data?.items}
        rowKey={(p) => p.id}
        empty="No payments match."
        columns={[
          { header: 'Date', cell: (p) => formatDate(p.payment_date) },
          { header: 'Invoice', cell: (p) => <Link to={`/invoices/${p.invoice_id}`} className="text-brand hover:underline">{p.invoice_number ?? `Draft #${p.invoice_id}`}</Link> },
          { header: 'Customer', cell: (p) => p.customer_name },
          { header: 'Method', cell: (p) => PAYMENT_METHODS[p.method] },
          { header: 'Note', cell: (p) => p.note ?? '—' },
          { header: 'Recorded by', cell: (p) => p.recorded_by ?? '—' },
          { header: 'Amount', className: 'text-right font-medium', cell: (p) => money(p.amount) },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}
    </>
  )
}
