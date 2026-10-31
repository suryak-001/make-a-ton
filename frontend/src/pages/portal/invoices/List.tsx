import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router'
import { DataTable, Pagination } from '@/components/DataTable'
import { StatusBadge } from '@/components/StatusBadge'
import { PageHeader } from '@/components/ui'
import { api, type Page, qs } from '@/lib/api'
import { formatDate, money } from '@/lib/format'
import { canPayOnline } from '@/lib/invoices'
import type { Invoice } from '@/lib/types'

export default function PortalInvoiceList() {
  const navigate = useNavigate(); const [page, setPage] = useState(1); const list = useQuery({ queryKey: ['/portal-invoices', page], queryFn: () => api.get<Page<Invoice>>(`/portal-invoices${qs({ page })}`), placeholderData: keepPreviousData })
  return <><PageHeader title="My invoices" description="Your confirmed invoices, balances, and printable copies. Pay any open invoice online by card, UPI or netbanking." /><DataTable loading={list.isPending} rows={list.data?.items} rowKey={(i) => i.id} onRowClick={(i) => navigate(String(i.id))} empty="You don’t have any invoices yet." columns={[{ header: 'Invoice', cell: (i) => <span className="font-medium">{i.number}</span> }, { header: 'Date', cell: (i) => formatDate(i.invoice_date) }, { header: 'Due', cell: (i) => formatDate(i.due_date) }, { header: 'Status', cell: (i) => <StatusBadge status={i.status} /> }, { header: 'Total', className: 'text-right', cell: (i) => money(i.total) }, { header: 'Outstanding', className: 'text-right', cell: (i) => money(i.outstanding) }, { header: 'Pay', cell: (i) => (canPayOnline(i) ? <span className="font-medium text-brand">Pay online →</span> : <span className="text-muted">—</span>) }]} />{list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}</>
}
