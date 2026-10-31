import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { DemoCheckout } from '@/components/DemoCheckout'
import { InvoiceView } from '@/components/InvoiceView'
import { Alert } from '@/components/forms'
import { Button, PageHeader } from '@/components/ui'
import { api } from '@/lib/api'
import { money } from '@/lib/format'
import { canPayOnline } from '@/lib/invoices'
import type { Invoice } from '@/lib/types'

export default function PortalInvoiceDetail() {
  const { id } = useParams()
  const [paying, setPaying] = useState(false)
  const invoice = useQuery({ queryKey: ['/portal-invoices', Number(id)], queryFn: () => api.get<Invoice>(`/portal-invoices/${id}`) })
  return (
    <>
      <PageHeader
        title={invoice.data?.number ?? 'Invoice'}
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <a href={`/api/portal-invoices/${id}/print`} target="_blank" rel="noreferrer" className="text-sm text-brand hover:underline">Print / PDF</a>
            <Link to="/portal/invoices" className="text-sm text-muted hover:underline">← My invoices</Link>
            {invoice.data && canPayOnline(invoice.data) && <Button onClick={() => setPaying(true)}>Pay {money(invoice.data.outstanding)}</Button>}
          </div>
        }
      />
      {invoice.isPending ? <p className="text-sm text-muted">Loading…</p> : invoice.data ? <InvoiceView invoice={invoice.data} /> : <Alert>Could not load this invoice.</Alert>}
      {invoice.data && <DemoCheckout invoice={invoice.data} open={paying} onClose={() => setPaying(false)} />}
    </>
  )
}
