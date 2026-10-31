import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { DataTable } from '@/components/DataTable'
import { StatusBadge } from '@/components/StatusBadge'
import { PageHeader } from '@/components/ui'
import { api, type Page } from '@/lib/api'
import { formatDate, money } from '@/lib/format'
import type { Invoice } from '@/lib/types'

export default function PortalInvoiceList() {
  const navigate = useNavigate(); const list = useQuery({ queryKey: ['/portal-invoices'], queryFn: () => api.get<Page<Invoice>>('/portal-invoices') })
  return <><PageHeader title="My invoices" description="Your confirmed invoices, balances, and printable copies." /><DataTable loading={list.isPending} rows={list.data?.items} rowKey={(i) => i.id} onRowClick={(i) => navigate(String(i.id))} empty="You don’t have any invoices yet." columns={[{ header: 'Invoice', cell: (i) => <span className="font-medium">{i.number}</span> }, { header: 'Date', cell: (i) => formatDate(i.invoice_date) }, { header: 'Due', cell: (i) => formatDate(i.due_date) }, { header: 'Status', cell: (i) => <StatusBadge status={i.status} /> }, { header: 'Total', className: 'text-right', cell: (i) => money(i.total) }, { header: 'Outstanding', className: 'text-right', cell: (i) => money(i.outstanding) }]} /></>
}
