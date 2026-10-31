import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { InvoiceView } from '@/components/InvoiceView'
import { Alert } from '@/components/forms'
import { PageHeader } from '@/components/ui'
import { api } from '@/lib/api'
import type { Invoice } from '@/lib/types'

export default function PortalInvoiceDetail() {
  const { id } = useParams(); const invoice = useQuery({ queryKey: ['/portal-invoices', Number(id)], queryFn: () => api.get<Invoice>(`/portal-invoices/${id}`) })
  return <><PageHeader title={invoice.data?.number ?? 'Invoice'} actions={<div className="flex gap-3"><a href={`/api/portal-invoices/${id}/print`} target="_blank" rel="noreferrer" className="text-sm text-brand hover:underline">Print / PDF</a><Link to="/portal/invoices" className="text-sm text-muted hover:underline">← My invoices</Link></div>} />{invoice.isPending ? <p className="text-sm text-muted">Loading…</p> : invoice.data ? <InvoiceView invoice={invoice.data} /> : <Alert>Could not load this invoice.</Alert>}</>
}
