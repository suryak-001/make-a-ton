import type { Brief, Invoice, InvoiceAction, Payment } from './types'

export type InvoiceFilterValues = { status: string; overdue: boolean; customer: Brief | null; from: string; to: string }

export const NO_INVOICE_FILTERS: InvoiceFilterValues = { status: '', overdue: false, customer: null, from: '', to: '' }

/** The query-string parameters the invoices API understands (empty ones are dropped by `qs`). */
export const invoiceFilterParams = (f: InvoiceFilterValues) => ({
  status: f.status,
  overdue: f.overdue || undefined,
  customer_id: f.customer?.id,
  from_date: f.from,
  to_date: f.to,
})

export const ACTION_LABEL: Record<InvoiceAction, string> = {
  confirm: 'Confirm invoice',
  cancel: 'Cancel invoice',
  pay: 'Record payment',
  send: 'Send to customer',
  print: 'Print / PDF',
  rebill: 'Re-bill period',
}

export const ACTION_DONE: Partial<Record<InvoiceAction, string>> = {
  confirm: 'Invoice confirmed and numbered.',
  cancel: 'Invoice cancelled.',
  send: 'Invoice emailed to the customer.',
  rebill: 'A new draft invoice was created for this period.',
}

export const PAYMENT_METHODS: Record<Payment['method'], string> = {
  UPI: 'UPI',
  BANK_TRANSFER: 'Bank transfer',
  CARD: 'Card',
  CASH: 'Cash',
  CHEQUE: 'Cheque',
  OTHER: 'Other',
}

/** A customer can pay online while a confirmed invoice still has a balance. */
export const canPayOnline = (invoice: Invoice) => invoice.status === 'CONFIRMED' && Number(invoice.outstanding) > 0
