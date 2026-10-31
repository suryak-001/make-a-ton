import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { formatDate, money } from '@/lib/format'
import { PERIOD_LABEL, PERIOD_UNIT, type PortalSubscription, type Subscription } from '@/lib/types'
import { EventHistory, StatusStepper } from './StatusTimeline'
import { StatusBadge } from './StatusBadge'
import { Card } from './ui'

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-[10px] font-medium uppercase tracking-[0.1em] text-muted">{label}</dt>
      <dd className="mt-1 text-[13px]">{children}</dd>
    </div>
  )
}

/** Read-only view of a subscription, shared by the staff detail page and the customer portal. */
/** `afterLines` sits right under the line items (the add-ons panel, which changes them). */
export function SubscriptionView({ sub, actions, afterLines, staff = false }: { sub: PortalSubscription | Subscription; actions?: ReactNode; afterLines?: ReactNode; staff?: boolean }) {
  const detail = sub as Partial<Subscription>
  const quoteLine =
    sub.status === 'DRAFT'
      ? detail.validity_days
        ? `${detail.validity_days} days from the day it’s sent`
        : '—'
      : formatDate(sub.quotation_valid_until)

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-[18px] font-medium tracking-[-0.025em]">{sub.number}</h2>
        <StatusBadge status={sub.status} />
        <span className="text-[12px] text-muted">
          {staff ? <Link to={`/customers/${sub.customer.id}`} className="text-brand hover:underline">{sub.customer.name}</Link> : sub.customer.name} · {sub.plan.name} ({PERIOD_LABEL[sub.plan.billing_period]})
        </span>
      </div>

      <StatusStepper status={sub.status} />
      {actions}

      <Card className="p-5">
        <dl className="grid gap-4 sm:grid-cols-3">
          <Fact label="Start date">{formatDate(sub.start_date)}</Fact>
          <Fact label="Expiry date">{formatDate(sub.expiry_date)}</Fact>
          <Fact label="Payment terms">{sub.payment_term_days} days</Fact>
          <Fact label="Next invoice">{sub.status === 'ACTIVE' ? formatDate(sub.next_invoice_date) : '—'}</Fact>
          <Fact label="Quote valid until">{quoteLine}</Fact>
          {staff && <Fact label="Created by">{detail.created_by ?? '—'}</Fact>}
        </dl>
        {staff && detail.notes && <p className="mt-4 whitespace-pre-line border-t border-line pt-3 text-sm text-muted">{detail.notes}</p>}
      </Card>

      <Card className="overflow-x-auto">
        <table className="w-full text-left text-[13px] tabular-nums">
          <thead className="border-b border-ink bg-surface text-[10px] uppercase tracking-[0.1em] text-muted">
            <tr>
              <th className="px-4 py-2.5 font-medium">Product</th>
              <th className="px-4 py-2.5 text-right font-medium">Qty</th>
              <th className="px-4 py-2.5 text-right font-medium">Unit price</th>
              <th className="px-4 py-2.5 font-medium">Taxes</th>
              <th className="px-4 py-2.5 text-right font-medium">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {sub.lines.map((line) => (
              <tr key={line.id}>
                <td className="px-4 py-3">
                  <span className="font-medium">{line.product_name}</span>
                  {line.is_addon && <span className="ml-2 text-[10px] font-medium uppercase tracking-[0.08em] text-brand">Add-on</span>}
                  {line.variant_label && <span className="block text-xs text-muted">{line.variant_label}</span>}
                </td>
                <td className="px-4 py-3 text-right">{line.quantity}</td>
                <td className="px-4 py-3 text-right">{money(line.unit_price)}</td>
                <td className="px-4 py-3 text-muted">{line.taxes.length ? line.taxes.map((t) => t.name).join(', ') : '—'}</td>
                <td className="px-4 py-3 text-right font-medium">{money(line.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot className="border-t border-line text-sm">
            <tr>
              <td colSpan={4} className="px-4 pt-3 text-right text-muted">
                Subtotal
              </td>
              <td className="px-4 pt-3 text-right">{money(sub.subtotal)}</td>
            </tr>
            <tr>
              <td colSpan={4} className="px-4 py-1 text-right text-muted">
                Taxes
              </td>
              <td className="px-4 py-1 text-right">{money(sub.tax_total)}</td>
            </tr>
            <tr>
              <td colSpan={4} className="px-4 pb-3 pt-1 text-right font-medium">
                Total per {PERIOD_UNIT[sub.plan.billing_period]}
              </td>
              <td className="px-4 pb-3 pt-1 text-right font-semibold">{money(sub.total)}</td>
            </tr>
          </tfoot>
        </table>
      </Card>

      {afterLines}

      <Card className="p-5">
        <h3 className="mb-3 font-medium">History</h3>
        <EventHistory events={sub.events} staff={staff} />
      </Card>
    </div>
  )
}
