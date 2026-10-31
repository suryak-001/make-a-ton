import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { InvoiceActions } from '@/components/InvoiceActions'
import { InvoiceView } from '@/components/InvoiceView'
import { PaymentForm } from '@/components/PaymentForm'
import { Alert } from '@/components/forms'
import { PageHeader } from '@/components/ui'
import { api } from '@/lib/api'
import type { Invoice } from '@/lib/types'

export default function InvoiceDetail() {
  const { id } = useParams()
  const invoice = useQuery({ queryKey: ['/invoices', id], queryFn: () => api.get<Invoice>(`/invoices/${id}`) })
  const data = invoice.data

  return (
    <>
      <PageHeader title={data?.number ?? 'Invoice'} actions={<Link to="/invoices" className="text-sm text-muted hover:underline">← All invoices</Link>} />
      {invoice.isPending && <p className="text-sm text-muted">Loading…</p>}
      {invoice.isError && <Alert>Could not load this invoice.</Alert>}
      {data && (
        <div className="grid gap-5">
          <InvoiceActions invoice={data} />
          <InvoiceView invoice={data} />
          {data.allowed_actions.includes('pay') && <PaymentForm key={data.amount_paid} invoice={data} />}
        </div>
      )}
    </>
  )
}
