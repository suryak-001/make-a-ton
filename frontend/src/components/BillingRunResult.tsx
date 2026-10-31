import { Link } from 'react-router'
import { formatDate } from '@/lib/format'
import type { BillingRun } from '@/lib/types'
import { DataTable } from './DataTable'
import { Alert } from './forms'
import { Card } from './ui'

function Count({ label, value, hint, tone = '' }: { label: string; value: number; hint: string; tone?: string }) {
  return (
    <Card className="p-4">
      <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-muted">{label}</p>
      <p className={`mt-2 text-[28px] font-medium leading-none tabular-nums ${tone}`}>{value}</p>
      <p className="mt-2 text-xs text-muted">{hint}</p>
    </Card>
  )
}

const accountedFor = (run: BillingRun) => run.created + run.already_billed + run.skipped + run.failed

/** The outcome of one run. The counts always add up to what was due. */
export function BillingRunResult({ run }: { run: BillingRun }) {
  if (run.due === 0) return <Alert kind="info">Nothing was due on {formatDate(run.as_of)}. Every subscription is already billed up to that date.</Alert>
  return (
    <div className="grid gap-4">
      <div className="grid gap-3 sm:grid-cols-5">
        <Count label="Due" value={run.due} hint="Billing periods up to the date" />
        <Count label="Created" value={run.created} hint="New draft invoices" tone="text-green" />
        <Count label="Already billed" value={run.already_billed} hint="Invoice existed, not duplicated" />
        <Count label="Skipped" value={run.skipped} hint="Waiting on an earlier failure" />
        <Count label="Failed" value={run.failed} hint="Recorded below, retried next run" tone={run.failed ? 'text-danger' : ''} />
      </div>
      <p className="text-sm text-muted">
        {run.due} due = {run.created} created + {run.already_billed} already billed + {run.skipped} skipped + {run.failed} failed
        {accountedFor(run) === run.due ? ' ✓' : ' — these do not add up, please report this'}
      </p>
      {run.errors.length > 0 && <FailureTable errors={run.errors} />}
    </div>
  )
}

function FailureTable({ errors }: { errors: BillingRun['errors'] }) {
  return (
    <DataTable
      rows={errors}
      rowKey={(e) => `${e.subscription_id}-${e.period_start}`}
      columns={[
        { header: 'Subscription', cell: (e) => <Link to={`/subscriptions/${e.subscription_id}`} className="text-brand hover:underline">#{e.subscription_id}</Link> },
        { header: 'Period', cell: (e) => formatDate(e.period_start) },
        { header: 'Reason', cell: (e) => e.error },
      ]}
    />
  )
}
