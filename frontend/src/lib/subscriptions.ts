import type { SubStatus } from './types'

/** The main road of a subscription. PAUSED sits on top of ACTIVE. */
export const STATUS_FLOW: SubStatus[] = ['DRAFT', 'QUOTATION', 'CONFIRMED', 'ACTIVE', 'CLOSED']

export const STATUS_LABEL: Record<SubStatus, string> = {
  DRAFT: 'Draft',
  QUOTATION: 'Quotation',
  CONFIRMED: 'Confirmed',
  ACTIVE: 'Active',
  PAUSED: 'Paused',
  CLOSED: 'Closed',
}

export type ActionInfo = {
  label: string
  /** Opens a dialog (with an optional reason) before doing it. */
  askReason?: boolean
  danger?: boolean
  help?: string
}

/** Button text for a server-provided action (a target status or "RENEW"), given where we are now. */
export function actionInfo(current: SubStatus, action: string): ActionInfo {
  switch (action) {
    case 'QUOTATION':
      return { label: 'Send quotation' }
    case 'DRAFT':
      return { label: 'Back to draft' }
    case 'CONFIRMED':
      return { label: 'Confirm' }
    case 'ACTIVE':
      return current === 'PAUSED' ? { label: 'Resume' } : { label: 'Activate' }
    case 'PAUSED':
      return { label: 'Pause', askReason: true, help: 'Billing stops while it is paused. You can resume it later.' }
    case 'CLOSED':
      return current === 'ACTIVE' || current === 'PAUSED'
        ? { label: 'Close', askReason: true, danger: true, help: 'This ends the subscription and stops billing. It can’t be undone.' }
        : { label: 'Cancel', askReason: true, danger: true, help: 'This cancels the subscription. It can’t be undone.' }
    case 'RENEW':
      return { label: 'Renew', help: 'Extends the expiry date by one billing period.' }
    default:
      return { label: action }
  }
}

export function eventText(from: SubStatus | null, to: SubStatus): string {
  if (from === null) return 'Created as a draft'
  if (from === to) return 'Renewed'
  return `${STATUS_LABEL[from]} → ${STATUS_LABEL[to]}`
}

/** Forward moves first (so the first button is the natural next step), destructive ones last. */
const ACTION_ORDER = ['QUOTATION', 'CONFIRMED', 'ACTIVE', 'PAUSED', 'RENEW', 'DRAFT', 'CLOSED']
export const sortActions = (actions: string[]) => [...actions].sort((a, b) => ACTION_ORDER.indexOf(a) - ACTION_ORDER.indexOf(b))
