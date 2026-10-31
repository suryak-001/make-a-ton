import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router'
import { DataTable, Pagination } from '@/components/DataTable'
import { StatusBadge } from '@/components/StatusBadge'
import { PageHeader } from '@/components/ui'
import { api, type Page, qs } from '@/lib/api'
import { formatDate, money, planLabel } from '@/lib/format'
import type { SubListItem } from '@/lib/types'

export default function PortalSubscriptionList() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const list = useQuery({
    queryKey: ['/portal-subscriptions', 'list', page],
    queryFn: () => api.get<Page<SubListItem>>(`/portal-subscriptions${qs({ page })}`),
    placeholderData: keepPreviousData,
  })

  return (
    <>
      <PageHeader title="My subscriptions" description="Everything you subscribe to. Open one to pause, renew or cancel it." />
      <DataTable
        loading={list.isPending}
        rows={list.data?.items}
        rowKey={(s) => s.id}
        onRowClick={(s) => navigate(`/portal/subscriptions/${s.id}`)}
        empty="You don’t have any subscriptions yet."
        columns={[
          { header: 'Number', cell: (s) => <span className="font-medium">{s.number}</span> },
          { header: 'Plan', cell: (s) => planLabel(s.plan) },
          { header: 'Status', cell: (s) => <StatusBadge status={s.status} /> },
          { header: 'Started', className: 'whitespace-nowrap', cell: (s) => formatDate(s.start_date) },
          { header: 'Expires', className: 'whitespace-nowrap', cell: (s) => formatDate(s.expiry_date) },
          { header: 'Total', className: 'text-right', cell: (s) => money(s.total) },
          { header: 'Manage', cell: (s) => (s.status === 'ACTIVE' || s.status === 'PAUSED') ? <span className="font-medium text-brand">Pause or cancel →</span> : <span className="text-muted">View →</span> },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}
    </>
  )
}
