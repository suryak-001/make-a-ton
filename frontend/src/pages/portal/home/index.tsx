import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { Link, useNavigate } from 'react-router'
import { ActionButtons } from '@/components/ActionButtons'
import { DataTable } from '@/components/DataTable'
import { StatusBadge } from '@/components/StatusBadge'
import { Card, PageHeader } from '@/components/ui'
import { api } from '@/lib/api'
import { formatDate, money } from '@/lib/format'
import type { PortalHome, PortalSubscription } from '@/lib/types'

const ALERT_TONE = {
  danger: 'border-danger bg-danger/5 text-danger',
  warning: 'border-yellow bg-yellow/15 text-ink',
  success: 'border-green bg-green/5 text-green',
} as const

const PERIOD = { DAILY: 'day', WEEKLY: 'week', MONTHLY: 'month', YEARLY: 'year' } as Record<string, string>

/** The customer's first screen: what needs attention, what they owe and when, and their plans with the actions the plan allows. */
export default function PortalHomePage() {
  const navigate = useNavigate()
  // The key starts with the portal-subscriptions path so pausing or renewing here refreshes this screen too.
  const home = useQuery({ queryKey: ['/portal-subscriptions', 'home'], queryFn: () => api.get<PortalHome>('/dashboard/portal') })
  const data = home.data
  if (home.isPending) return <><PageHeader title="Home" /><Card className="h-40 animate-pulse bg-paper" /></>
  if (!data) return <><PageHeader title="Home" /><p className="text-sm text-danger">We couldn’t load your account. Try again in a moment.</p></>

  return <div className="grid gap-6">
    <PageHeader title={`Hello, ${data.name}`} description="Your plans, what you owe, and what is coming up." />

    <div className="grid gap-2">
      {data.alerts.map((alert) => {
        const inner = <span className={clsx('block border-l-4 px-4 py-3 text-[13px] font-medium', ALERT_TONE[alert.kind])}>{alert.text}{alert.href && ' →'}</span>
        return alert.href ? <Link key={alert.text} to={alert.href}>{inner}</Link> : <div key={alert.text}>{inner}</div>
      })}
    </div>

    <div className="grid gap-3 sm:grid-cols-3">
      <Card className="p-4"><p className="text-[10px] font-medium uppercase tracking-[0.13em] text-muted">You owe</p><p className="mt-3 text-[24px] font-medium leading-none tabular-nums">{money(data.outstanding)}</p><p className="mt-2 text-[11px] text-muted">Across open invoices</p></Card>
      <Card className={clsx('p-4', data.overdue_count > 0 && 'border-danger')}><p className="text-[10px] font-medium uppercase tracking-[0.13em] text-muted">Overdue</p><p className={clsx('mt-3 text-[24px] font-medium leading-none tabular-nums', data.overdue_count > 0 && 'text-danger')}>{money(data.overdue_amount)}</p><p className="mt-2 text-[11px] text-muted">{data.overdue_count} invoice{data.overdue_count === 1 ? '' : 's'}</p></Card>
      <Card className="p-4"><p className="text-[10px] font-medium uppercase tracking-[0.13em] text-muted">Next payment due</p>
        {data.next_due ? <><p className="mt-3 text-[24px] font-medium leading-none tabular-nums">{money(data.next_due.outstanding)}</p><p className="mt-2 text-[11px] text-muted">{data.next_due.number} · due {formatDate(data.next_due.due_date)} · <Link className="text-brand underline" to={`/portal/invoices/${data.next_due.id}`}>Pay now</Link></p></>
          : <p className="mt-3 text-[15px] text-muted">Nothing due</p>}
      </Card>
    </div>

    <section>
      <h2 className="mb-3 text-[16px] font-medium">Your subscriptions</h2>
      {data.subscriptions.length === 0 ? <p className="text-[13px] text-muted">You don’t have an active subscription yet.</p> : <div className="grid gap-3">
        {data.subscriptions.map((sub) => <Card key={sub.id} className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div className="min-w-0">
            <Link to={`/portal/subscriptions/${sub.id}`} className="text-[14px] font-medium hover:underline">{sub.number} · {sub.plan}</Link>
            <p className="mt-1 text-[12px] text-muted">{money(sub.total)} per {PERIOD[sub.billing_period] ?? 'period'}{sub.next_invoice_date && ` · next bill ${formatDate(sub.next_invoice_date)}`}{sub.expiry_date && ` · ends ${formatDate(sub.expiry_date)}`}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2"><StatusBadge status={sub.status} /><ActionButtons sub={sub as unknown as PortalSubscription} base="/portal-subscriptions" /></div>
        </Card>)}
      </div>}
    </section>

    <section>
      <div className="mb-3 flex items-end justify-between"><h2 className="text-[16px] font-medium">Recent invoices</h2><Link to="/portal/invoices" className="text-[12px] text-muted hover:underline">View all →</Link></div>
      <DataTable
        rows={data.recent_invoices}
        rowKey={(i) => i.id}
        onRowClick={(i) => navigate(`/portal/invoices/${i.id}`)}
        empty="No invoices yet."
        columns={[
          { header: 'Invoice', cell: (i) => i.number ?? `#${i.id}` },
          { header: 'Due', cell: (i) => <span className={i.overdue ? 'font-medium text-danger' : ''}>{formatDate(i.due_date)}</span> },
          { header: 'Status', cell: (i) => <StatusBadge status={i.status} /> },
          { header: 'Total', className: 'text-right', cell: (i) => money(i.total) },
          { header: 'Outstanding', className: 'text-right', cell: (i) => money(i.outstanding) },
        ]}
      />
    </section>
  </div>
}
