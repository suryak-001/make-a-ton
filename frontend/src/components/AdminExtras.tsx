import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { Link } from 'react-router'
import { Card } from './ui'
import { api } from '@/lib/api'
import { formatDateTime, money } from '@/lib/format'
import type { AgingBucket, Proof, SetupStep } from '@/lib/types'

/** Points at the first setup step not done yet. It follows real data, so it moves on by itself and goes away when all are done. */
export function SetupBanner() {
  const steps = useQuery({ queryKey: ['/dashboard', 'setup'], queryFn: () => api.get<SetupStep[]>('/dashboard/setup') })
  const next = steps.data?.find((step) => !step.done)
  if (!steps.data || !next) return null
  const done = steps.data.filter((step) => step.done).length
  return (
    <Card className="flex flex-wrap items-center justify-between gap-3 border-brand/40 bg-brand/5 p-4">
      <div>
        <p className="text-[10px] font-medium uppercase tracking-[0.15em] text-brand">Next step · {done} of {steps.data.length} done</p>
        <p className="mt-1 text-[14px] font-medium">{next.title}</p>
      </div>
      <Link to={next.href} className="bg-brand px-3 py-2 text-[12px] font-medium text-paper hover:opacity-90">{next.cta} →</Link>
    </Card>
  )
}

const BUCKET_TONE: Record<string, string> = { current: 'bg-green', '1-30': 'bg-yellow', '31-60': 'bg-yellow', '61-90': 'bg-danger', '90+': 'bg-danger' }

/** Money still owed, by how long past due. Each bucket opens the overdue list. */
export function AgingCard() {
  const aging = useQuery({ queryKey: ['/dashboard', 'aging'], queryFn: () => api.get<AgingBucket[]>('/dashboard/aging') })
  const max = Math.max(1, ...(aging.data ?? []).map((bucket) => Number(bucket.amount)))
  return (
    <Card className="p-5">
      <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-brand">Receivables</p>
      <h2 className="mt-1 text-[16px] font-medium">Aging of unpaid invoices</h2>
      <p className="mt-0.5 mb-4 text-[12px] text-muted">What is owed, by how many days it is past due.</p>
      <div className="grid gap-2.5">
        {(aging.data ?? []).map((bucket) => (
          <Link key={bucket.key} to={bucket.key === 'current' ? '/invoices' : '/invoices?overdue=1'} className="group grid grid-cols-[84px_1fr_auto] items-center gap-3 text-[12px]">
            <span className="text-muted">{bucket.label}</span>
            <span className="h-3 bg-surface"><span className={clsx('block h-full transition-[width] duration-500', BUCKET_TONE[bucket.key])} style={{ width: `${Number(bucket.amount) / max * 100}%` }} /></span>
            <span className="min-w-28 text-right tabular-nums group-hover:underline">{money(bucket.amount)} <span className="text-muted">· {bucket.count}</span></span>
          </Link>
        ))}
        {aging.isPending && <p className="text-[12px] text-muted">Loading…</p>}
      </div>
    </Card>
  )
}

/** The claims, measured: how much data, that nothing was billed twice, and how long these checks took. */
export function ProofPanel() {
  const proof = useQuery({ queryKey: ['/dashboard', 'proof'], queryFn: () => api.get<Proof>('/dashboard/proof') })
  const data = proof.data
  const clean = data?.duplicate_invoice_periods === 0
  const facts: [string, string][] = data ? [
    ['Subscriptions', data.subscriptions.toLocaleString('en-IN')],
    ['Invoices', data.invoices.toLocaleString('en-IN')],
    ['Payments', data.payments.toLocaleString('en-IN')],
    ['Customers', data.customers.toLocaleString('en-IN')],
  ] : []
  return (
    <Card className="p-5">
      <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-brand">Proof</p>
      <h2 className="mt-1 text-[16px] font-medium">Billing integrity and speed</h2>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {facts.map(([label, value]) => <div key={label}><p className="text-[10px] uppercase tracking-[0.1em] text-muted">{label}</p><p className="mt-1 text-[18px] font-medium tabular-nums">{value}</p></div>)}
      </div>
      {data && <div className="mt-4 grid gap-2 text-[12px]">
        <p className={clsx('border-l-4 px-3 py-2', clean ? 'border-green bg-green/5 text-green' : 'border-danger bg-danger/5 text-danger')}>
          {clean ? '0 subscriptions billed twice for the same period.' : `${data.duplicate_invoice_periods} subscription periods billed twice. Investigate now.`}
        </p>
        <p className="text-muted">Checked just now across all your invoices. {data.last_invoice_at ? `Last invoice created ${formatDateTime(data.last_invoice_at)}.` : 'No invoices yet.'}</p>
      </div>}
    </Card>
  )
}
