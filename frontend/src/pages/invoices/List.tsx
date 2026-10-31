import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { buttonClass } from '@/components/button-class'
import { DataTable, Pagination } from '@/components/DataTable'
import { ExportLink } from '@/components/ExportLink'
import { InvoiceFilters } from '@/components/InvoiceFilters'
import { StatusBadge } from '@/components/StatusBadge'
import { PageHeader } from '@/components/ui'
import { api, type Page, qs } from '@/lib/api'
import { formatDate, money } from '@/lib/format'
import { type InvoiceFilterValues, NO_INVOICE_FILTERS, invoiceFilterParams } from '@/lib/invoices'
import type { Invoice } from '@/lib/types'

export default function InvoiceList() {
  const navigate = useNavigate()
  const [params] = useSearchParams() // the dashboard links here with ?overdue=1
  const [filters, setFilters] = useState<InvoiceFilterValues>({ ...NO_INVOICE_FILTERS, overdue: params.get('overdue') === '1', status: params.get('status') ?? '' })
  const [page, setPage] = useState(1)

  const change = (patch: Partial<InvoiceFilterValues>) => {
    setFilters((current) => ({ ...current, ...patch }))
    setPage(1)
  }
  const clear = () => change({ ...NO_INVOICE_FILTERS })

  const list = useQuery({
    queryKey: ['/invoices', filters, page],
    queryFn: () => api.get<Page<Invoice>>(`/invoices${qs({ ...invoiceFilterParams(filters), page })}`),
    placeholderData: keepPreviousData,
  })

  return (
    <>
      <PageHeader
        title="Invoices"
        description="Confirm, send, collect payment and keep an eye on what is overdue."
        actions={
          <>
            <ExportLink path="/invoices" params={invoiceFilterParams(filters)} />
            <Link to="/billing-run" className={buttonClass()}>Billing run</Link>
          </>
        }
      />
      <InvoiceFilters values={filters} onChange={change} onClear={clear} />
      <DataTable
        loading={list.isPending}
        rows={list.data?.items}
        rowKey={(i) => i.id}
        onRowClick={(i) => navigate(String(i.id))}
        empty="No invoices match. Run billing when a subscription is due."
        columns={[
          { header: 'Invoice', cell: (i) => <span className="font-medium">{i.number ?? `Draft #${i.id}`}</span> },
          { header: 'Customer', cell: (i) => i.customer.name },
          { header: 'Period', cell: (i) => `${formatDate(i.period_start)} – ${formatDate(i.period_end)}` },
          { header: 'Due', cell: (i) => <span className={i.overdue ? 'font-medium text-danger' : ''}>{formatDate(i.due_date)}{i.overdue ? ' · overdue' : ''}</span> },
          { header: 'Status', cell: (i) => <StatusBadge status={i.status} /> },
          { header: 'Total', className: 'text-right', cell: (i) => money(i.total) },
          { header: 'Outstanding', className: 'text-right', cell: (i) => money(i.outstanding) },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}
    </>
  )
}
