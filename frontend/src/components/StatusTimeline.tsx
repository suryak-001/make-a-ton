import clsx from 'clsx'
import { eventText, isAddonEvent, STATUS_FLOW, STATUS_LABEL } from '@/lib/subscriptions'
import { formatDateTime } from '@/lib/format'
import type { SubEvent, SubStatus } from '@/lib/types'
import { Badge } from './ui'

/** Where the subscription is on its road: Draft → Quotation → Confirmed → Active → Closed. */
export function StatusStepper({ status }: { status: SubStatus }) {
  const here = STATUS_FLOW.indexOf(status === 'PAUSED' ? 'ACTIVE' : status)
  return (
    <ol className="flex flex-wrap items-center gap-2 text-[12px]" aria-label="Subscription progress">
      {STATUS_FLOW.map((step, i) => (
        <li key={step} className="flex items-center gap-2" aria-current={i === here ? 'step' : undefined}>
          <span
            className={clsx(
              'border px-2.5 py-1',
              i < here && 'border-brand/30 bg-brand/5 text-brand',
              i === here && 'border-brand bg-brand text-brand-fg font-medium',
              i > here && 'border-line text-muted',
            )}
          >
            {STATUS_LABEL[step]}
          </span>
          {i === here && status === 'PAUSED' && <Badge className="border-danger/30 bg-danger/10 text-danger">Paused</Badge>}
          {i < STATUS_FLOW.length - 1 && <span className="text-muted" aria-hidden>→</span>}
        </li>
      ))}
    </ol>
  )
}

/** Every status change, oldest first, with who did it and why. */
export function EventHistory({ events, staff = false }: { events: SubEvent[]; staff?: boolean }) {
  return (
    <ol className="grid gap-3">
      {events.map((e) => (
        <li key={e.id} className="grid grid-cols-[auto_1fr] gap-3 text-[13px]">
          <span className="mt-1.5 size-2 rotate-45 bg-brand" aria-hidden />
          <div>
            <p className="font-medium">{eventText(e.from_status, e.to_status, e.reason)}</p>
            <p className="text-xs text-muted">
              {formatDateTime(e.created_at)}
              {e.actor_name ? ` · ${e.actor_name}` : staff && e.from_status !== null ? ' · System' : ''}
            </p>
            {e.reason && !isAddonEvent(e) && <p className="mt-0.5 text-muted">“{e.reason}”</p>}
          </div>
        </li>
      ))}
    </ol>
  )
}
