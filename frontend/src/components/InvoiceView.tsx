import { Link } from 'react-router'
import { DataTable } from './DataTable'
import { StatusBadge } from './StatusBadge'
import { Card } from './ui'
import { formatDate, money } from '@/lib/format'
import type { Invoice } from '@/lib/types'

/** `staff` links the customer to their page; the portal shows plain text. */
export function InvoiceView({ invoice, staff = false }: { invoice: Invoice; staff?: boolean }) {
  return (
    <div className="grid max-w-5xl gap-4">
      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line p-5">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted">Invoice</p>
            <h2 className="mt-1 text-xl font-semibold">{invoice.number ?? `Draft #${invoice.id}`}</h2>
            <p className="mt-1 text-sm text-muted">{staff ? <Link to={`/customers/${invoice.customer.id}`} className="text-brand hover:underline">{invoice.customer.name}</Link> : invoice.customer.name} · {invoice.customer.email}</p>
          </div>
          <div className="text-right">
            <StatusBadge status={invoice.status} />
            {invoice.overdue && <p className="mt-2 text-xs font-medium text-danger">Overdue</p>}
          </div>
        </div>
        <div className="grid gap-4 p-5 text-sm sm:grid-cols-4">
          <div><p className="text-xs text-muted">Billing period</p><p>{formatDate(invoice.period_start)} – {formatDate(invoice.period_end)}</p></div>
          <div><p className="text-xs text-muted">Invoice date</p><p>{formatDate(invoice.invoice_date)}</p></div>
          <div><p className="text-xs text-muted">Due date</p><p>{formatDate(invoice.due_date)}</p></div>
          <div><p className="text-xs text-muted">Subscription</p><p>{invoice.subscription.number}</p></div>
        </div>
      </Card>
      <DataTable
        rows={invoice.lines}
        rowKey={(line) => line.id}
        columns={[
          { header: 'Description', cell: (line) => line.description },
          { header: 'Qty', className: 'text-right', cell: (line) => line.quantity },
          { header: 'Unit price', className: 'text-right', cell: (line) => money(line.unit_price) },
          { header: 'Discount', className: 'text-right', cell: (line) => money(line.discount_amount) },
          { header: 'Tax', className: 'text-right', cell: (line) => money(line.tax_amount) },
          { header: 'Total', className: 'text-right font-medium', cell: (line) => money(line.total) },
        ]}
      />
      <Card className="ml-auto w-full max-w-sm p-5 text-sm">
        <div className="grid grid-cols-2 gap-y-2"><span className="text-muted">Subtotal</span><span className="text-right">{money(invoice.subtotal)}</span><span className="text-muted">Discount</span><span className="text-right">− {money(invoice.discount_total)}</span><span className="text-muted">Tax</span><span className="text-right">{money(invoice.tax_total)}</span><span className="border-t border-line pt-3 font-semibold">Total</span><span className="border-t border-line pt-3 text-right font-semibold">{money(invoice.total)}</span><span className="text-muted">Paid</span><span className="text-right">{money(invoice.amount_paid)}</span><span className="font-medium">Outstanding</span><span className="text-right font-medium">{money(invoice.outstanding)}</span></div>
      </Card>
    </div>
  )
}
