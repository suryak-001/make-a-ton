import clsx from 'clsx'
import { Badge } from './ui'

const TONES: Record<string, string> = {
  // subscriptions
  DRAFT: 'bg-surface text-muted',
  QUOTATION: 'bg-amber-50 text-amber-800 border-amber-200',
  CONFIRMED: 'bg-sky-50 text-sky-800 border-sky-200',
  ACTIVE: 'bg-green-50 text-green-800 border-green-200',
  PAUSED: 'bg-orange-50 text-orange-800 border-orange-200',
  CLOSED: 'bg-zinc-100 text-zinc-600',
  // invoices (B)
  PAID: 'bg-green-50 text-green-800 border-green-200',
  CANCELLED: 'bg-zinc-100 text-zinc-600',
}

const label = (s: string) => s.charAt(0) + s.slice(1).toLowerCase().replaceAll('_', ' ')

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  return <Badge className={clsx(TONES[status] ?? 'bg-surface text-muted', className)}>{label(status)}</Badge>
}
