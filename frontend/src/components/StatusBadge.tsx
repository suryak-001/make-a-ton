import clsx from 'clsx'
import { Badge } from './ui'

const TONES: Record<string, string> = {
  // subscriptions
  DRAFT: 'bg-surface text-muted',
  QUOTATION: 'bg-yellow/20 text-ink border-yellow',
  CONFIRMED: 'bg-brand/10 text-brand border-brand/30',
  ACTIVE: 'bg-green/10 text-green border-green/30',
  PAUSED: 'bg-danger/10 text-danger border-danger/30',
  CLOSED: 'bg-ink/5 text-muted border-ink/15',
  // invoices (B)
  PAID: 'bg-green/10 text-green border-green/30',
  CANCELLED: 'bg-ink/5 text-muted border-ink/15',
}

const label = (s: string) => s.charAt(0) + s.slice(1).toLowerCase().replaceAll('_', ' ')

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  return <Badge className={clsx(TONES[status] ?? 'bg-surface text-muted', className)}>{label(status)}</Badge>
}
