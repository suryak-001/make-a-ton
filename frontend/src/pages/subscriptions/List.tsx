import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { useAuth } from '@/auth/context'
import { buttonClass } from '@/components/button-class'
import { DataTable, Pagination } from '@/components/DataTable'
import { Alert, Input, Select } from '@/components/forms'
import { StatusBadge } from '@/components/StatusBadge'
import { Button, PageHeader } from '@/components/ui'
import { Sheet } from '@/components/Sheet'
import { SubscriptionView } from '@/components/SubscriptionView'
import { ActionButtons } from '@/components/ActionButtons'
import { api, ApiError, type Page, qs } from '@/lib/api'
import { formatDate, money, planLabel } from '@/lib/format'
import { useDebounced } from '@/lib/hooks'
import { usePlans } from '@/lib/queries'
import { STATUS_LABEL } from '@/lib/subscriptions'
import type { SubListItem, Subscription } from '@/lib/types'

export default function SubscriptionList() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const plans = usePlans()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [planId, setPlanId] = useState('')
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<number>()
  const [notice, setNotice] = useState<{ kind: 'success' | 'error'; text: string }>()
  const debounced = useDebounced(q)
  const selected = useQuery({ queryKey: ['/subscriptions', selectedId], queryFn: () => api.get<Subscription>(`/subscriptions/${selectedId}`), enabled: Boolean(selectedId) })

  const list = useQuery({
    queryKey: ['/subscriptions', 'list', debounced, status, planId, page],
    queryFn: () => api.get<Page<SubListItem>>(`/subscriptions${qs({ q: debounced, status, plan_id: planId, page })}`),
    placeholderData: keepPreviousData,
  })

  const lifecycle = useMutation({
    mutationFn: () => api.post<{ closed: number; expired_quotations: number }>('/subscriptions/run-lifecycle'),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['/subscriptions'] })
      setNotice({
        kind: 'success',
        text:
          r.closed + r.expired_quotations === 0
            ? 'Nothing to do: no subscription has ended and no quotation has expired.'
            : `Closed ${r.closed} ended subscription${r.closed === 1 ? '' : 's'} and expired ${r.expired_quotations} quotation${r.expired_quotations === 1 ? '' : 's'}.`,
      })
    },
    onError: (e) => setNotice({ kind: 'error', text: e instanceof ApiError ? e.message : 'Could not run the job.' }),
  })

  const reset = (fn: () => void) => {
    fn()
    setPage(1)
  }

  return (
    <>
      <PageHeader
        title="Subscriptions"
        description="Every subscription and where it stands."
        actions={
          <>
            {user?.role === 'ADMIN' && (
              <Button variant="outline" disabled={lifecycle.isPending} onClick={() => (setNotice(undefined), lifecycle.mutate())} title="Closes ended auto-close subscriptions and expires stale quotations">
                {lifecycle.isPending ? 'Running…' : 'Run lifecycle job'}
              </Button>
            )}
            <Link to="new" className={buttonClass()}>
              New subscription
            </Link>
          </>
        }
      />
      {notice && (
        <div className="mb-4">
          <Alert kind={notice.kind}>{notice.text}</Alert>
        </div>
      )}
      <div className="mb-4 flex flex-wrap gap-3 rounded-md border border-line bg-paper p-3">
        <Input value={q} onChange={(e) => reset(() => setQ(e.target.value))} placeholder="Search by number or customer…" aria-label="Search subscriptions" className="max-w-sm" />
        <Select value={status} onChange={(e) => reset(() => setStatus(e.target.value))} aria-label="Filter by status" className="w-full sm:w-44">
          <option value="">All statuses</option>
          {Object.entries(STATUS_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Select value={planId} onChange={(e) => reset(() => setPlanId(e.target.value))} aria-label="Filter by plan" className="w-full sm:w-52">
          <option value="">All plans</option>
          {plans.data?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </Select>
      </div>
      <DataTable
        loading={list.isPending}
        rows={list.data?.items}
        rowKey={(s) => s.id}
        onRowClick={(s) => setSelectedId(s.id)}
        empty={debounced || status || planId ? 'No subscriptions match these filters.' : 'No subscriptions yet.'}
        columns={[
          { header: 'Number', cell: (s) => <span className="font-medium">{s.number}</span> },
          { header: 'Customer', cell: (s) => s.customer.name },
          { header: 'Plan', cell: (s) => planLabel(s.plan) },
          { header: 'Status', cell: (s) => <StatusBadge status={s.status} /> },
          { header: 'Start', className: 'whitespace-nowrap', cell: (s) => formatDate(s.start_date) },
          { header: 'Expiry', className: 'whitespace-nowrap', cell: (s) => formatDate(s.expiry_date) },
          { header: 'Total', className: 'text-right', cell: (s) => money(s.total) },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}
      <Sheet open={Boolean(selectedId)} onClose={() => setSelectedId(undefined)} title={selected.data?.number ?? 'Subscription detail'} subtitle="Review the agreement without leaving the list.">
        {selected.isPending ? <p className="text-[13px] text-muted">Loading subscription…</p> : selected.data ? <SubscriptionView staff sub={selected.data} actions={<div className="grid gap-3"><ActionButtons sub={selected.data} base="/subscriptions" /><Link to={`${selected.data.id}`} className={buttonClass('outline', 'w-full')}>Open full record →</Link></div>} /> : <Alert>Could not load this subscription.</Alert>}
      </Sheet>
    </>
  )
}
