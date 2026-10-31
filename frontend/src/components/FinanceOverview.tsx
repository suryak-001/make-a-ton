import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { DataTable } from './DataTable'
import { StatusBadge } from './StatusBadge'
import { Button, Card } from './ui'
import { LIVE_MS } from '@/lib/queries'
import { api, qs } from '@/lib/api'
import { formatDate, money } from '@/lib/format'
import { METRIC_DEFINITIONS, type MetricKey } from '@/lib/metrics'
import type { Invoice, ReportFilters, RevenuePoint, Summary } from '@/lib/types'

const ACCENTS = ['bg-brand', 'bg-danger', 'bg-yellow', 'bg-green']

function monthKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

function revenueTimeline(data: RevenuePoint[], count: number) {
  const byMonth = new Map(data.map((point) => [point.month, point]))
  const now = new Date()
  return Array.from({ length: count }, (_, index) => {
    const date = new Date(now.getFullYear(), now.getMonth() - (count - index - 1), 1)
    const key = monthKey(date)
    return byMonth.get(key) ?? { month: key, invoiced: '0', collected: '0' }
  })
}

function monthLabel(value: string) {
  const [year, month] = value.split('-').map(Number)
  return new Intl.DateTimeFormat('en-IN', { month: 'short', year: '2-digit' }).format(new Date(year, month - 1, 1))
}

/** Collected as a share of invoiced, so a weak month shows up without doing the sum. */
function collectionRate(summary: Summary) {
  const invoiced = Number(summary.invoiced)
  return invoiced > 0 ? `${Math.round(Number(summary.collected) / invoiced * 100)}% of invoiced` : 'Cash received'
}

function compactMoney(value: number) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

export function FinanceOverview({ filters = {} }: { filters?: ReportFilters }) {
  const navigate = useNavigate()
  const [months, setMonths] = useState(6)
  const suffix = qs(filters)
  const summary = useQuery({ refetchInterval: LIVE_MS, refetchOnWindowFocus: true, queryKey: ['/reports', 'summary', filters], queryFn: () => api.get<Summary>(`/reports/summary${suffix}`) })
  const revenue = useQuery({ refetchInterval: LIVE_MS, refetchOnWindowFocus: true, queryKey: ['/reports', 'revenue', filters], queryFn: () => api.get<RevenuePoint[]>(`/reports/revenue-by-month${suffix}`) })
  const overdue = useQuery({ refetchInterval: LIVE_MS, refetchOnWindowFocus: true, queryKey: ['/reports', 'overdue', filters], queryFn: () => api.get<Invoice[]>(`/reports/overdue${qs({ plan_id: filters.plan_id, customer_id: filters.customer_id })}`) })
  const GO: Record<string, string> = { active: '/subscriptions?status=ACTIVE', mrr: '/subscriptions?status=ACTIVE', invoiced: '/invoices', collected: '/payments' }
  const primary: [string, string, string, MetricKey][] = summary.data ? [
    ['Active subscriptions', String(summary.data.active_subscriptions), 'Live agreements', 'active'],
    ['Monthly revenue', money(summary.data.mrr), 'Net of discounts, before tax', 'mrr'],
    ['Invoiced', money(summary.data.invoiced), 'Confirmed + paid', 'invoiced'],
    ['Collected', money(summary.data.collected), collectionRate(summary.data), 'collected'],
  ] : []
  const points = revenueTimeline(revenue.data ?? [], months)
  const max = Math.max(1, ...(points.flatMap((point) => [Number(point.invoiced), Number(point.collected)])))
  const hasRevenue = (revenue.data ?? []).some((point) => Number(point.invoiced) > 0 || Number(point.collected) > 0)

  return <div className="grid gap-5">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {summary.isPending ? Array.from({ length: 4 }, (_, index) => <Card key={index} className="h-28 animate-pulse bg-paper" />) : primary.map(([label, value, hint, metric], index) => (
        <Card key={label} className="relative cursor-pointer overflow-hidden p-4 transition-shadow hover:shadow-[3px_3px_0_#171713]" title={`${METRIC_DEFINITIONS[metric]} Click to see the records.`} role="link" tabIndex={0} onClick={() => navigate(GO[metric])} onKeyDown={(e) => e.key === 'Enter' && navigate(GO[metric])}>
          <span className={`absolute inset-x-0 top-0 h-1 ${ACCENTS[index]}`} />
          <div className="flex items-start justify-between gap-4">
            <p className="text-[10px] font-medium uppercase tracking-[0.13em] text-muted">{label}</p>
            <span className="text-[10px] text-muted">0{index + 1}</span>
          </div>
          <p className="mt-4 text-[24px] font-medium leading-none tracking-[-0.045em] tabular-nums">{value}</p>
          <p className="mt-2 text-[11px] text-muted">{hint}</p>
        </Card>
      ))}
    </div>

    <div className="grid gap-4 xl:grid-cols-[1fr_240px]">
      <Card className="min-w-0 p-5">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div><p className="text-[10px] font-medium uppercase tracking-[0.16em] text-brand">Cash movement</p><h2 className="mt-1 text-[16px] font-medium">Revenue by month</h2><p className="mt-0.5 text-[12px] text-muted">Invoiced versus cash collected.</p></div>
          <div className="flex border border-line bg-surface p-0.5">
            {[6, 12].map((value) => <button key={value} type="button" onClick={() => setMonths(value)} className={`px-2.5 py-1 text-[11px] ${months === value ? 'bg-ink text-paper' : 'text-muted hover:text-ink'}`}>{value} months</button>)}
          </div>
        </div>
        {hasRevenue ? <div>
          <div className="overflow-x-auto pb-1">
            <div className="relative h-56" style={{ minWidth: months === 12 ? 680 : 0 }}>
              {[0, 0.5, 1].map((ratio) => <div key={ratio} className="absolute left-12 right-0 border-t border-line/80" style={{ top: `${ratio * 184}px` }} />)}
              <span className="absolute left-0 top-0 text-[9px] text-muted">{compactMoney(max)}</span>
              <span className="absolute left-0 top-[88px] text-[9px] text-muted">{compactMoney(max / 2)}</span>
              <span className="absolute bottom-[25px] left-0 text-[9px] text-muted">₹0</span>
              <div className="absolute bottom-7 left-12 right-0 top-0 flex items-end gap-1">
                {points.map((point) => <div key={point.month} className="flex h-full min-w-0 flex-1 items-end justify-center gap-1 px-1">
                  {[['invoiced', 'bg-brand'], ['collected', 'bg-green']].map(([key, color]) => {
                    const value = Number(point[key as 'invoiced' | 'collected'])
                    return <div key={key} className={`w-full max-w-5 rounded-t-[2px] ${color} transition-[height] duration-500 ${value === 0 ? 'opacity-25' : ''}`} style={{ height: value === 0 ? 2 : `${Math.max(3, value / max * 100)}%` }} title={`${key === 'invoiced' ? 'Invoiced' : 'Collected'} ${money(value)}`} />
                  })}
                </div>)}
              </div>
              <div className="absolute bottom-0 left-12 right-0 flex gap-1">{points.map((point) => <span key={point.month} className="min-w-0 flex-1 text-center text-[9px] text-muted">{monthLabel(point.month)}</span>)}</div>
            </div>
          </div>
          <div className="mt-3 flex gap-4 text-[10px] uppercase tracking-[0.08em] text-muted"><span className="flex items-center gap-1.5"><i className="size-2 bg-brand" /> Invoiced</span><span className="flex items-center gap-1.5"><i className="size-2 bg-green" /> Collected</span></div>
        </div> : <p className="py-16 text-center text-[13px] text-muted">Revenue appears after invoices are confirmed.</p>}
      </Card>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
        <Card className="relative cursor-pointer overflow-hidden !border-ink !bg-ink p-5 !text-paper transition-opacity hover:opacity-90" title={`${METRIC_DEFINITIONS.outstanding} Click to see the records.`} role="link" tabIndex={0} onClick={() => navigate('/invoices?status=CONFIRMED')} onKeyDown={(e) => e.key === 'Enter' && navigate('/invoices?status=CONFIRMED')}>
          <span className="absolute -right-7 -top-7 size-24 rounded-full border-[14px] border-yellow" />
          <p className="text-[10px] font-medium uppercase tracking-[0.15em] text-paper/60">Outstanding</p>
          <p className="mt-8 text-[25px] font-medium tracking-[-0.04em]">{summary.data ? money(summary.data.outstanding) : '—'}</p>
          <p className="mt-2 text-[11px] text-paper/60">Still to collect</p>
        </Card>
        <Card className="relative cursor-pointer overflow-hidden !border-danger !bg-danger p-5 !text-paper transition-opacity hover:opacity-90" title={METRIC_DEFINITIONS.overdue} onClick={() => navigate('/invoices?overdue=1')}>
          <span className="absolute right-5 top-5 size-5 rotate-45 bg-yellow" />
          <p className="text-[10px] font-medium uppercase tracking-[0.15em] text-paper/70">Overdue</p>
          <p className="mt-8 text-[25px] font-medium tracking-[-0.04em]">{summary.data ? money(summary.data.overdue_amount) : '—'}</p>
          <p className="mt-2 text-[11px] text-paper/70">{(() => { const n = summary.data?.overdue_count ?? 0; return `${n} invoice${n === 1 ? '' : 's'} need${n === 1 ? 's' : ''} attention` })()}</p>
        </Card>
      </div>
    </div>

    <section>
      <div className="mb-3 flex items-end justify-between gap-4"><div><p className="text-[10px] font-medium uppercase tracking-[0.15em] text-danger">Needs action</p><h2 className="mt-1 text-[16px] font-medium">Overdue invoices</h2></div><Button variant="ghost" onClick={() => navigate('/invoices')}>View all →</Button></div>
      <DataTable loading={overdue.isPending} rows={overdue.data} rowKey={(invoice) => invoice.id} onRowClick={(invoice) => navigate(`/invoices/${invoice.id}`)} empty="Nothing is overdue." columns={[{ header: 'Invoice', cell: (invoice) => invoice.number ?? `Draft #${invoice.id}` }, { header: 'Customer', cell: (invoice) => invoice.customer.name }, { header: 'Due', cell: (invoice) => formatDate(invoice.due_date) }, { header: 'Status', cell: (invoice) => <StatusBadge status={invoice.status} /> }, { header: 'Outstanding', className: 'text-right font-medium text-danger', cell: (invoice) => money(invoice.outstanding) }]} />
    </section>
    <MetricDefinitions />
  </div>
}

function MetricDefinitions() {
  return (
    <details className="rounded-md border border-line bg-paper p-4 text-sm">
      <summary className="cursor-pointer font-medium">How these numbers are calculated</summary>
      <dl className="mt-3 grid gap-3">
        {(Object.keys(METRIC_DEFINITIONS) as MetricKey[]).map((key) => (
          <div key={key}>
            <dt className="font-medium capitalize">{key === 'mrr' ? 'Monthly revenue (MRR)' : key}</dt>
            <dd className="text-muted">{METRIC_DEFINITIONS[key]}</dd>
          </div>
        ))}
      </dl>
    </details>
  )
}
