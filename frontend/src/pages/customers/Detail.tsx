import { useQuery } from '@tanstack/react-query'
import { ReceiptText, Repeat2, WalletCards } from 'lucide-react'
import { type ReactNode, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { DataTable } from '@/components/DataTable'
import { ExportLink } from '@/components/ExportLink'
import { Alert } from '@/components/forms'
import { Modal } from '@/components/Modal'
import { StatusBadge } from '@/components/StatusBadge'
import { Badge, Button, Card, PageHeader } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { formatDate, formatDateTime, money, planLabel } from '@/lib/format'
import { PAYMENT_METHODS } from '@/lib/invoices'
import { METRIC_DEFINITIONS } from '@/lib/metrics'
import type { CustomerOverview, TimelineItem } from '@/lib/types'
import { CustomerForm } from './Form'

/** One customer on one page: their numbers, what they subscribe to, what they were billed and paid, and when. */
export default function CustomerDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [editing, setEditing] = useState(false)
  const overview = useQuery({ queryKey: ['/customers', Number(id), 'overview'], queryFn: () => api.get<CustomerOverview>(`/customers/${id}/overview`) })

  const back = (
    <Link to="/customers" className="text-sm text-muted hover:underline">
      ← All customers
    </Link>
  )
  if (overview.isPending) return <><PageHeader title="Customer" actions={back} /><p className="text-sm text-muted">Loading…</p></>
  if (overview.isError) {
    const missing = overview.error instanceof ApiError && overview.error.status === 404
    return <><PageHeader title="Customer" actions={back} /><Alert>{missing ? 'We couldn’t find that customer.' : 'Could not load the customer.'}</Alert></>
  }

  const { customer, summary, average_days_late, subscriptions, invoices, payments, timeline } = overview.data
  const contact = [customer.email, customer.phone].filter(Boolean).join(' · ')
  const tiles: [string, string, string, string | undefined][] = [
    ['Active subscriptions', String(summary.active_subscriptions), `${subscriptions.length} in total`, METRIC_DEFINITIONS.active],
    ['Monthly revenue', money(summary.mrr), 'Net of discounts, before tax', METRIC_DEFINITIONS.mrr],
    ['Outstanding', money(summary.outstanding), summary.overdue_count ? `${money(summary.overdue_amount)} overdue on ${summary.overdue_count} invoice${summary.overdue_count === 1 ? '' : 's'}` : 'Nothing overdue', METRIC_DEFINITIONS.outstanding],
    ['Collected', money(summary.collected), `of ${money(summary.invoiced)} invoiced · ${paymentHabit(average_days_late)}`, METRIC_DEFINITIONS.collected],
  ]

  return (
    <>
      <PageHeader
        title={customer.name}
        description={contact}
        actions={
          <>
            {back}
            <Button variant="outline" onClick={() => setEditing(true)}>
              Edit
            </Button>
          </>
        }
      />
      <div className="mb-5 flex flex-wrap items-center gap-2 text-[12px] text-muted">
        {customer.has_login ? <Badge className="border-green/30 bg-green/10 text-green">Portal login</Badge> : <Badge className="bg-surface text-muted">No portal login</Badge>}
        <span>Customer since {formatDate(customer.created_at)}</span>
        {customer.address && <span>· {customer.address}</span>}
      </div>

      <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {tiles.map(([label, value, hint, definition], index) => (
          <Card key={label} className={`p-4 ${index === 2 && summary.overdue_count ? 'border-danger/40' : ''}`} title={definition}>
            <p className="text-[10px] font-medium uppercase tracking-[0.13em] text-muted">{label}</p>
            <p className="mt-2 text-[22px] font-medium tabular-nums tracking-[-0.03em]">{value}</p>
            <p className={`mt-1 text-[12px] ${index === 2 && summary.overdue_count ? 'text-danger' : 'text-muted'}`}>{hint}</p>
          </Card>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="grid min-w-0 content-start gap-5">
          <Section title="Subscriptions">
            <DataTable
              rows={subscriptions}
              rowKey={(s) => s.id}
              onRowClick={(s) => navigate(`/subscriptions/${s.id}`)}
              empty="No subscriptions yet."
              columns={[
                { header: 'Number', cell: (s) => <span className="font-medium">{s.number}</span> },
                { header: 'Plan', cell: (s) => planLabel(s.plan) },
                { header: 'Status', cell: (s) => <StatusBadge status={s.status} /> },
                { header: 'Start', className: 'whitespace-nowrap', cell: (s) => formatDate(s.start_date) },
                { header: 'Expiry', className: 'whitespace-nowrap', cell: (s) => formatDate(s.expiry_date) },
                { header: 'Per period', className: 'text-right', cell: (s) => money(s.total) },
              ]}
            />
          </Section>
          <Section title="Recent invoices" more={<ExportLink path="/invoices" params={{ customer_id: customer.id }} />}>
            <DataTable
              rows={invoices}
              rowKey={(i) => i.id}
              onRowClick={(i) => navigate(`/invoices/${i.id}`)}
              empty="No invoices yet."
              columns={[
                { header: 'Invoice', cell: (i) => <span className="font-medium">{i.number ?? `Draft #${i.id}`}</span> },
                { header: 'Period', cell: (i) => `${formatDate(i.period_start)} – ${formatDate(i.period_end)}` },
                { header: 'Due', cell: (i) => <span className={i.overdue ? 'font-medium text-danger' : ''}>{formatDate(i.due_date)}{i.overdue ? ' · overdue' : ''}</span> },
                { header: 'Status', cell: (i) => <StatusBadge status={i.status} /> },
                { header: 'Total', className: 'text-right', cell: (i) => money(i.total) },
                { header: 'Outstanding', className: 'text-right', cell: (i) => money(i.outstanding) },
              ]}
            />
          </Section>
          <Section title="Recent payments">
            <DataTable
              rows={payments}
              rowKey={(p) => p.id}
              onRowClick={(p) => navigate(`/invoices/${p.invoice_id}`)}
              empty="No payments yet."
              columns={[
                { header: 'Date', cell: (p) => formatDate(p.payment_date) },
                { header: 'Invoice', cell: (p) => p.invoice_number ?? `Draft #${p.invoice_id}` },
                { header: 'Method', cell: (p) => PAYMENT_METHODS[p.method] },
                { header: 'Note', cell: (p) => p.note ?? '—' },
                { header: 'Amount', className: 'text-right font-medium', cell: (p) => money(p.amount) },
              ]}
            />
          </Section>
        </div>

        <Card className="content-start self-start p-5">
          <h2 className="mb-4 font-medium">Activity</h2>
          {timeline.length === 0 ? <p className="text-[13px] text-muted">Nothing has happened yet.</p> : <div className="max-h-[520px] overflow-y-auto pr-2"><Timeline items={timeline} /></div>}
        </Card>
      </div>

      <Modal open={editing} onClose={() => setEditing(false)} title="Edit customer">
        {editing && <CustomerForm customer={customer} onDone={() => setEditing(false)} onDeleted={() => navigate('/customers')} />}
      </Modal>
    </>
  )
}

/** "Pays 4 days early on average" from the average of payment date minus due date. */
function paymentHabit(daysLate: string | null) {
  if (daysLate === null) return 'no payments yet'
  const days = Math.round(Number(daysLate))
  if (days === 0) return 'pays on time'
  return `pays ${Math.abs(days)} day${Math.abs(days) === 1 ? '' : 's'} ${days > 0 ? 'late' : 'early'} on average`
}

function Section({ title, more, children }: { title: string; more?: ReactNode; children: ReactNode }) {
  return (
    <section className="min-w-0">
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h2 className="font-medium">{title}</h2>
        {more}
      </div>
      {children}
    </section>
  )
}

const KIND = {
  subscription: { Icon: Repeat2, tone: 'bg-brand/10 text-brand' },
  invoice: { Icon: ReceiptText, tone: 'bg-yellow/25 text-ink' },
  payment: { Icon: WalletCards, tone: 'bg-green/10 text-green' },
}

function Timeline({ items }: { items: TimelineItem[] }) {
  return (
    <ol className="grid gap-4">
      {items.map((item, index) => {
        const { Icon, tone } = KIND[item.kind]
        return (
          <li key={`${item.kind}-${item.at}-${index}`} className="flex gap-3">
            <span className={`mt-0.5 grid size-7 shrink-0 place-items-center rounded-full ${tone}`}>
              <Icon aria-hidden className="size-3.5" />
            </span>
            <div className="min-w-0 flex-1">
              <Link to={item.link} className="block text-[13px] font-medium hover:underline">
                {item.title}
              </Link>
              {item.detail && <p className="truncate text-[12px] text-muted">{item.detail}</p>}
              <p className="text-[11px] text-muted">
                {formatDateTime(item.at)}
                {item.amount && <span className="ml-2 font-medium tabular-nums text-ink">{money(item.amount)}</span>}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
