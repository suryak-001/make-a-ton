import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { DataTable } from './DataTable'
import { StatusBadge } from './StatusBadge'
import { Button, Card } from './ui'
import { api, qs } from '@/lib/api'
import { formatDate, money } from '@/lib/format'
import type { Invoice, RevenuePoint, Summary } from '@/lib/types'

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

function compactMoney(value: number) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

export function FinanceOverview({ fromDate, toDate }: { fromDate?: string; toDate?: string }) {
  const navigate = useNavigate()
  const [months, setMonths] = useState(6)
  const suffix = qs({ from_date: fromDate, to_date: toDate })
  const summary = useQuery({ queryKey: ['/reports/summary', fromDate, toDate], queryFn: () => api.get<Summary>(`/reports/summary${suffix}`) })
  const revenue = useQuery({ queryKey: ['/reports/revenue'], queryFn: () => api.get<RevenuePoint[]>('/reports/revenue-by-month') })
  const overdue = useQuery({ queryKey: ['/reports/overdue'], queryFn: () => api.get<Invoice[]>('/reports/overdue') })
  const primary = summary.data ? [
    ['Active subscriptions', String(summary.data.active_subscriptions), 'Live agreements'],
    ['Monthly revenue', money(summary.data.mrr), 'Before tax'],
    ['Invoiced', money(summary.data.invoiced), 'Confirmed + paid'],
    ['Collected', money(summary.data.collected), 'Cash received'],
  ] : []
  const points = revenueTimeline(revenue.data ?? [], months)
  const max = Math.max(1, ...(points.flatMap((point) => [Number(point.invoiced), Number(point.collected)])))
  const hasRevenue = (revenue.data ?? []).some((point) => Number(point.invoiced) > 0 || Number(point.collected) > 0)

  return <div className="grid gap-5">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {summary.isPending ? Array.from({ length: 4 }, (_, index) => <Card key={index} className="h-28 animate-pulse bg-paper" />) : primary.map(([label, value, hint], index) => (
        <Card key={label} className="relative overflow-hidden p-4">
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
        <Card className="relative overflow-hidden !border-ink !bg-ink p-5 !text-paper">
          <span className="absolute -right-7 -top-7 size-24 rounded-full border-[14px] border-yellow" />
          <p className="text-[10px] font-medium uppercase tracking-[0.15em] text-paper/60">Outstanding</p>
          <p className="mt-8 text-[25px] font-medium tracking-[-0.04em]">{summary.data ? money(summary.data.outstanding) : '—'}</p>
          <p className="mt-2 text-[11px] text-paper/60">Still to collect</p>
        </Card>
        <Card className="relative overflow-hidden !border-danger !bg-danger p-5 !text-paper">
          <span className="absolute right-5 top-5 size-5 rotate-45 bg-yellow" />
          <p className="text-[10px] font-medium uppercase tracking-[0.15em] text-paper/70">Overdue</p>
          <p className="mt-8 text-[25px] font-medium tracking-[-0.04em]">{summary.data ? money(summary.data.overdue_amount) : '—'}</p>
          <p className="mt-2 text-[11px] text-paper/70">{summary.data?.overdue_count ?? 0} invoices need attention</p>
        </Card>
      </div>
    </div>

    <section>
      <div className="mb-3 flex items-end justify-between gap-4"><div><p className="text-[10px] font-medium uppercase tracking-[0.15em] text-danger">Needs action</p><h2 className="mt-1 text-[16px] font-medium">Overdue invoices</h2></div><Button variant="ghost" onClick={() => navigate('/invoices')}>View all →</Button></div>
      <DataTable loading={overdue.isPending} rows={overdue.data} rowKey={(invoice) => invoice.id} onRowClick={(invoice) => navigate(`/invoices/${invoice.id}`)} empty="Nothing is overdue." columns={[{ header: 'Invoice', cell: (invoice) => invoice.number ?? `Draft #${invoice.id}` }, { header: 'Customer', cell: (invoice) => invoice.customer.name }, { header: 'Due', cell: (invoice) => formatDate(invoice.due_date) }, { header: 'Status', cell: (invoice) => <StatusBadge status={invoice.status} /> }, { header: 'Outstanding', className: 'text-right font-medium text-danger', cell: (invoice) => money(invoice.outstanding) }]} />
    </section>
  </div>
}
