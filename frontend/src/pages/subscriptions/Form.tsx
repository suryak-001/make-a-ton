import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { CustomerPicker } from '@/components/CustomerPicker'
import { Alert, FormField, Input, Select, Textarea } from '@/components/forms'
import { LinesEditor } from '@/components/LinesEditor'
import { Button, Card, PageHeader } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { todayISO } from '@/lib/format'
import { EMPTY_LINE, type LineDraft } from '@/lib/lines'
import { usePlans, useProducts } from '@/lib/queries'
import { PERIOD_LABEL, type Brief, type Subscription } from '@/lib/types'

type Draft = {
  customer: Brief | null
  plan_id: string
  start_date: string
  expiry_date: string
  payment_term_days: string
  validity_days: string
  notes: string
  lines: LineDraft[]
}

export default function SubscriptionFormPage() {
  const { id } = useParams()
  const sub = useQuery({ queryKey: ['/subscriptions', Number(id)], queryFn: () => api.get<Subscription>(`/subscriptions/${id}`), enabled: !!id })
  if (id && sub.isPending) return <p className="text-sm text-muted">Loading…</p>
  if (id && sub.isError) return <Alert>{sub.error instanceof ApiError ? sub.error.message : 'Could not load the subscription.'}</Alert>
  if (sub.data && !sub.data.editable) return <Alert>Only draft and quotation subscriptions can be edited.</Alert>
  return <SubscriptionEditor key={id ?? 'new'} sub={sub.data} />
}

function SubscriptionEditor({ sub }: { sub?: Subscription }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const products = useProducts()
  const available = usePlans(true) // what can be picked for a new subscription today
  const [error, setError] = useState<ApiError>()
  const [draft, setDraft] = useState<Draft>(() =>
    sub
      ? {
          customer: { id: sub.customer.id, name: sub.customer.name },
          plan_id: String(sub.plan.id),
          start_date: sub.start_date,
          expiry_date: sub.expiry_date ?? '',
          payment_term_days: String(sub.payment_term_days),
          validity_days: String(sub.validity_days),
          notes: sub.notes ?? '',
          lines: sub.lines.map((l) => ({ product_id: String(l.product_id), variant_id: l.variant_id ? String(l.variant_id) : '', quantity: String(l.quantity) })),
        }
      : { customer: null, plan_id: '', start_date: todayISO(), expiry_date: '', payment_term_days: '15', validity_days: '30', notes: '', lines: [{ ...EMPTY_LINE }] },
  )
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((d) => ({ ...d, [key]: value }))

  // On edit the current plan stays selectable even if it has since left its availability window.
  const planOptions = [...(available.data ?? [])]
  if (sub && !planOptions.some((p) => p.id === sub.plan.id)) planOptions.push({ id: sub.plan.id, name: sub.plan.name, billing_period: sub.plan.billing_period, min_quantity: sub.plan.min_quantity } as (typeof planOptions)[number])
  const plan = planOptions.find((p) => String(p.id) === draft.plan_id)

  const save = useMutation({
    mutationFn: () => {
      const body = {
        customer_id: draft.customer!.id,
        plan_id: Number(draft.plan_id),
        start_date: draft.start_date,
        expiry_date: draft.expiry_date || null,
        payment_term_days: Number(draft.payment_term_days),
        validity_days: Number(draft.validity_days),
        notes: draft.notes,
        lines: draft.lines.map((l) => ({ product_id: Number(l.product_id), variant_id: l.variant_id ? Number(l.variant_id) : null, quantity: Number(l.quantity) })),
      }
      return sub ? api.put<Subscription>(`/subscriptions/${sub.id}`, body) : api.post<Subscription>('/subscriptions', body)
    },
    onSuccess: (saved) => {
      qc.invalidateQueries({ queryKey: ['/subscriptions'] })
      navigate(`/subscriptions/${saved.id}`)
    },
    onError: (e) => setError(e instanceof ApiError ? e : new ApiError(0, 'Could not save. Try again.')),
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    const missing: Record<string, string> = {}
    if (!draft.customer) missing.customer_id = 'Choose a customer.'
    if (!draft.plan_id) missing.plan_id = 'Choose a plan.'
    draft.lines.forEach((l, i) => {
      if (!l.product_id) missing[`lines.${i}.product_id`] = 'Choose a product.'
    })
    if (Object.keys(missing).length) return setError(new ApiError(422, 'Fill in the highlighted fields.', missing))
    save.mutate()
  }

  const f = error?.fields ?? {}
  const knownKeys = ['customer_id', 'plan_id', 'start_date', 'expiry_date', 'payment_term_days', 'validity_days', 'notes']
  const inline = Object.keys(f).some((k) => knownKeys.includes(k) || k.startsWith('lines.'))
  const general = error && !inline ? error.message : undefined
  const isDraft = !sub || sub.status === 'DRAFT'
  const back = sub ? `/subscriptions/${sub.id}` : '/subscriptions'

  return (
    <>
      <PageHeader
        title={sub ? `Edit ${sub.number}` : 'New subscription'}
        description="Prices, variants and taxes are worked out by the server from the catalogue."
        actions={
          <Link to={back} className="text-sm text-muted hover:underline">
            ← Back
          </Link>
        }
      />
      <form onSubmit={onSubmit} noValidate className="grid max-w-4xl gap-6">
        <Card className="grid gap-4 p-5 sm:grid-cols-2">
          <FormField label="Customer" htmlFor="customer" error={f.customer_id}>
            <CustomerPicker id="customer" value={draft.customer} onChange={(c) => set('customer', c)} error={!!f.customer_id} />
          </FormField>
          <FormField label="Plan" htmlFor="plan" error={f.plan_id} hint={plan ? `Each line needs a quantity of at least ${plan.min_quantity}.` : undefined}>
            <Select id="plan" value={draft.plan_id} onChange={(e) => set('plan_id', e.target.value)} error={!!f.plan_id}>
              <option value="">Choose a plan…</option>
              {planOptions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({PERIOD_LABEL[p.billing_period]})
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Start date" htmlFor="start" error={f.start_date}>
            <Input id="start" type="date" value={draft.start_date} onChange={(e) => set('start_date', e.target.value)} required error={!!f.start_date} />
          </FormField>
          <FormField label="Expiry date" htmlFor="expiry" error={f.expiry_date} hint="Leave empty for an open-ended subscription.">
            <Input id="expiry" type="date" value={draft.expiry_date} onChange={(e) => set('expiry_date', e.target.value)} error={!!f.expiry_date} />
          </FormField>
          <FormField label="Payment terms (days)" htmlFor="terms" error={f.payment_term_days} hint="An invoice is due this many days after its date.">
            <Input id="terms" type="number" min={0} max={365} value={draft.payment_term_days} onChange={(e) => set('payment_term_days', e.target.value)} error={!!f.payment_term_days} />
          </FormField>
          {isDraft && (
            <FormField label="Quote valid for (days)" htmlFor="validity" error={f.validity_days} hint="Counted from the day the quote is sent.">
              <Input id="validity" type="number" min={1} max={365} value={draft.validity_days} onChange={(e) => set('validity_days', e.target.value)} error={!!f.validity_days} />
            </FormField>
          )}
          <FormField label="Notes" htmlFor="notes" error={f.notes} className="sm:col-span-2">
            <Textarea id="notes" value={draft.notes} onChange={(e) => set('notes', e.target.value)} />
          </FormField>
        </Card>

        <Card className="p-5">
          <h2 className="mb-4 font-medium">Lines</h2>
          <LinesEditor lines={draft.lines} onChange={(lines) => set('lines', lines)} products={products.data} minQuantity={plan?.min_quantity ?? 1} errors={f} showAmounts />
        </Card>

        {general && <Alert>{general}</Alert>}
        <div className="flex justify-end gap-2">
          <Link to={back} className="inline-flex h-9 items-center rounded-md border border-line px-3 text-sm hover:bg-surface">
            Cancel
          </Link>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? 'Saving…' : sub ? 'Save changes' : 'Create subscription'}
          </Button>
        </div>
      </form>
    </>
  )
}
