import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router'
import { DataTable } from './DataTable'
import { useToast } from './Toast'
import { Button, Card } from './ui'
import { api, ApiError } from '@/lib/api'
import { formatDate, formatDateTime, money } from '@/lib/format'
import type { WorkQueue as Queue } from '@/lib/types'

function Count({ label, value, to, tone }: { label: string; value: number; to: string; tone?: string }) {
  return (
    <Link to={to}>
      <Card className="p-4 transition-colors hover:bg-surface">
        <p className="text-[10px] font-medium uppercase tracking-[0.13em] text-muted">{label}</p>
        <p className={`mt-3 text-[26px] font-medium leading-none tabular-nums ${value > 0 ? tone ?? '' : 'text-muted'}`}>{value}</p>
      </Card>
    </Link>
  )
}

const dayText = (days: number) => (days === 0 ? 'today' : days === 1 ? 'tomorrow' : `in ${days} days`)

/** Staff home: things to do today, not money totals. Everything here links to where the work is done. */
export function WorkQueue() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { toast } = useToast()
  const queue = useQuery({ queryKey: ['/dashboard', 'queue'], queryFn: () => api.get<Queue>('/dashboard/queue') })
  const remind = useMutation({
    mutationFn: (id: number) => api.post(`/dashboard/remind/${id}`),
    onSuccess: () => { toast('Reminder sent'); qc.invalidateQueries({ queryKey: ['/dashboard', 'queue'] }) },
    onError: (e) => toast(e instanceof ApiError ? e.message : 'Could not send the reminder'),
  })
  const data = queue.data
  if (queue.isPending) return <Card className="h-40 animate-pulse bg-paper" />
  if (!data) return <p className="text-sm text-danger">Could not load your work queue.</p>
  const allClear = !data.draft_invoices && !data.overdue_invoices && !data.renewals_due.length && !data.quotes_expiring.length

  return <div className="grid gap-6">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Count label="Draft invoices to confirm" value={data.draft_invoices} to="/invoices" tone="text-brand" />
      <Count label="Overdue invoices" value={data.overdue_invoices} to="/invoices?overdue=1" tone="text-danger" />
      <Count label={`Renewals due (14 days)`} value={data.renewals_due.length} to="/subscriptions" tone="text-brand" />
      <Count label="Quotes expiring (7 days)" value={data.quotes_expiring.length} to="/subscriptions" tone="text-brand" />
    </div>
    {allClear && <p className="border-l-4 border-green bg-green/5 px-3 py-2 text-[13px] text-green">Nothing needs doing right now.</p>}

    <section>
      <h2 className="mb-3 text-[16px] font-medium">Invoices to chase</h2>
      <DataTable
        rows={data.to_chase}
        rowKey={(i) => i.id}
        onRowClick={(i) => navigate(`/invoices/${i.id}`)}
        empty="Nothing is overdue."
        columns={[
          { header: 'Invoice', cell: (i) => i.number ?? `#${i.id}` },
          { header: 'Customer', cell: (i) => i.customer },
          { header: 'Overdue', cell: (i) => <span className="font-medium text-danger">{i.days_overdue} days</span> },
          { header: 'Outstanding', className: 'text-right', cell: (i) => money(i.outstanding) },
          { header: 'Reminder', className: 'text-right', cell: (i) => i.reminded
            ? <span className="text-[12px] text-muted" title={i.last_reminder_at ? formatDateTime(i.last_reminder_at) : undefined}>Sent for {i.stage}</span>
            : <Button variant="outline" disabled={remind.isPending} onClick={(event) => { event.stopPropagation(); remind.mutate(i.id) }}>Send reminder</Button> },
        ]}
      />
    </section>

    <section>
      <h2 className="mb-3 text-[16px] font-medium">Renewals due</h2>
      <DataTable
        rows={data.renewals_due}
        rowKey={(s) => s.id}
        onRowClick={(s) => navigate(`/subscriptions/${s.id}`)}
        empty="No subscription ends in the next 14 days."
        columns={[
          { header: 'Subscription', cell: (s) => s.number },
          { header: 'Customer', cell: (s) => s.customer },
          { header: 'Plan', cell: (s) => s.plan },
          { header: 'Ends', cell: (s) => <span>{formatDate(s.expiry_date)} · {dayText(s.days_left)}</span> },
          { header: 'On expiry', cell: (s) => (s.auto_close ? 'Closes by itself' : s.renewable ? 'Needs renewing' : 'Cannot be renewed') },
        ]}
      />
    </section>

    <section>
      <h2 className="mb-3 text-[16px] font-medium">Quotes about to expire</h2>
      <DataTable
        rows={data.quotes_expiring}
        rowKey={(s) => s.id}
        onRowClick={(s) => navigate(`/subscriptions/${s.id}`)}
        empty="No quote expires in the next 7 days."
        columns={[
          { header: 'Quote', cell: (s) => s.number },
          { header: 'Customer', cell: (s) => s.customer },
          { header: 'Valid until', cell: (s) => `${formatDate(s.valid_until)} · ${dayText(s.days_left)}` },
        ]}
      />
    </section>
  </div>
}
