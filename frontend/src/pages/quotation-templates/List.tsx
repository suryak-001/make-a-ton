import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { buttonClass } from '@/components/button-class'
import { CustomerPicker } from '@/components/CustomerPicker'
import { DataTable, Pagination } from '@/components/DataTable'
import { EntityRowMenu } from '@/components/EntityRow'
import { Alert, FormField, Input } from '@/components/forms'
import { Modal } from '@/components/Modal'
import { Button, PageHeader } from '@/components/ui'
import { api, ApiError, type Page, qs } from '@/lib/api'
import { todayISO } from '@/lib/format'
import { useDebounced } from '@/lib/hooks'
import { PERIOD_LABEL, type Brief, type Subscription, type Template } from '@/lib/types'

export default function TemplateList() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [using, setUsing] = useState<Template | null>(null)
  const debounced = useDebounced(q)

  const list = useQuery({
    queryKey: ['templates', debounced, page],
    queryFn: () => api.get<Page<Template>>(`/quotation-templates${qs({ q: debounced, page })}`),
    placeholderData: keepPreviousData,
  })

  return (
    <>
      <PageHeader
        title="Quotation templates"
        description="A plan with ready-made product lines. Start a quote from one instead of building it from scratch."
        actions={<Link to="new" className={buttonClass()}>New template</Link>}
      />
      <Input
        value={q}
        onChange={(e) => {
          setQ(e.target.value)
          setPage(1)
        }}
        placeholder="Search templates…"
        aria-label="Search templates"
        className="mb-4 max-w-sm"
      />
      <DataTable
        loading={list.isPending}
        rows={list.data?.items}
        rowKey={(t) => t.id}
        onRowClick={(t) => navigate(String(t.id))}
        actions={(t) => <EntityRowMenu path="/quotation-templates" id={t.id} name={t.name} label="this template" />}
        empty="No templates yet."
        columns={[
          { header: 'Name', cell: (t) => <span className="font-medium">{t.name}</span> },
          { header: 'Plan', cell: (t) => `${t.plan.name} (${PERIOD_LABEL[t.plan.billing_period]})` },
          { header: 'Lines', cell: (t) => t.lines.map((l) => `${l.quantity} × ${l.product_name}${l.variant_label ? ` (${l.variant_label})` : ''}`).join(', ') },
          { header: 'Valid for', className: 'whitespace-nowrap', cell: (t) => `${t.validity_days} days` },
          {
            header: '',
            className: 'text-right',
            cell: (t) => (
              <Button
                variant="outline"
                onClick={(e) => {
                  e.stopPropagation()
                  setUsing(t)
                }}
              >
                Use template
              </Button>
            ),
          },
        ]}
      />
      {list.data && <Pagination page={page} pageSize={list.data.page_size} total={list.data.total} onPage={setPage} />}

      <Modal open={using !== null} onClose={() => setUsing(null)} title={using ? `New quote from “${using.name}”` : ''}>
        {using && <UseTemplateForm template={using} onCancel={() => setUsing(null)} onCreated={(id) => navigate(`/subscriptions/${id}`)} />}
      </Modal>
    </>
  )
}

function UseTemplateForm({ template, onCancel, onCreated }: { template: Template; onCancel: () => void; onCreated: (id: number) => void }) {
  const [customer, setCustomer] = useState<Brief | null>(null)
  const [startDate, setStartDate] = useState(todayISO)
  const [expiry, setExpiry] = useState('')
  const [error, setError] = useState<ApiError>()

  const create = useMutation({
    mutationFn: () =>
      api.post<Subscription>(`/quotation-templates/${template.id}/create-subscription`, {
        customer_id: customer!.id,
        start_date: startDate || null,
        expiry_date: expiry || null,
      }),
    onSuccess: (sub) => onCreated(sub.id),
    onError: (e) => setError(e instanceof ApiError ? e : new ApiError(0, 'Could not create the quote. Try again.')),
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    if (!customer) return setError(new ApiError(422, 'Choose a customer.', { customer_id: 'Choose a customer.' }))
    create.mutate()
  }

  const f = error?.fields ?? {}
  const general = error && !['customer_id', 'start_date', 'expiry_date'].some((k) => f[k]) ? error.message : undefined
  return (
    <form onSubmit={onSubmit} className="grid gap-4" noValidate>
      <p className="text-sm text-muted">
        Starts a draft with {template.plan.name} and {template.lines.length} line{template.lines.length === 1 ? '' : 's'}. The quote stays valid for {template.validity_days} days once you send it.
      </p>
      <FormField label="Customer" htmlFor="customer" error={f.customer_id}>
        <CustomerPicker id="customer" value={customer} onChange={setCustomer} error={!!f.customer_id} />
      </FormField>
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Start date" htmlFor="start" error={f.start_date}>
          <Input id="start" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
        </FormField>
        <FormField label="Expiry date" htmlFor="expiry" error={f.expiry_date} hint="Optional.">
          <Input id="expiry" type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} />
        </FormField>
      </div>
      {general && <Alert>{general}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={create.isPending}>
          {create.isPending ? 'Creating…' : 'Create quote'}
        </Button>
      </div>
    </form>
  )
}
