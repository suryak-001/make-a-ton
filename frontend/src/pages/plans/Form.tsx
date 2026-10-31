import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useAuth } from '@/auth/context'
import { Alert, Checkbox, FormField, Input, Select } from '@/components/forms'
import { Button, Card, PageHeader } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { PERIOD_LABEL, type BillingPeriod, type Plan } from '@/lib/types'

type Draft = {
  name: string
  price: string
  billing_period: BillingPeriod
  min_quantity: string
  available_from: string
  available_to: string
  auto_close: boolean
  closable: boolean
  pausable: boolean
  renewable: boolean
  active: boolean
}

const EMPTY: Draft = {
  name: '',
  price: '0',
  billing_period: 'MONTHLY',
  min_quantity: '1',
  available_from: '',
  available_to: '',
  auto_close: false,
  closable: true,
  pausable: false,
  renewable: true,
  active: true,
}

const toDraft = (p: Plan): Draft => ({
  ...p,
  price: p.price,
  min_quantity: String(p.min_quantity),
  available_from: p.available_from ?? '',
  available_to: p.available_to ?? '',
})

export default function PlanFormPage() {
  const { id } = useParams()
  const plan = useQuery({ queryKey: ['plan', id], queryFn: () => api.get<Plan>(`/plans/${id}`), enabled: !!id })
  if (id && plan.isPending) return <p className="text-sm text-muted">Loading…</p>
  if (id && plan.isError) return <Alert>{plan.error instanceof ApiError ? plan.error.message : 'Could not load the plan.'}</Alert>
  return <PlanEditor key={id ?? 'new'} plan={plan.data} />
}

function PlanEditor({ plan }: { plan?: Plan }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const readOnly = user?.role !== 'ADMIN'
  const [draft, setDraft] = useState<Draft>(plan ? toDraft(plan) : EMPTY)
  const [error, setError] = useState<ApiError>()
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((d) => ({ ...d, [key]: value }))

  const done = () => {
    qc.invalidateQueries({ queryKey: ['plans'] })
    qc.invalidateQueries({ queryKey: ['plan'] })
    navigate('/plans')
  }
  const fail = (e: unknown) => setError(e instanceof ApiError ? e : new ApiError(0, 'Something went wrong. Try again.'))

  const save = useMutation({
    mutationFn: () => {
      const body = {
        name: draft.name,
        price: draft.price || '0',
        billing_period: draft.billing_period,
        min_quantity: Number(draft.min_quantity),
        available_from: draft.available_from || null,
        available_to: draft.available_to || null,
        auto_close: draft.auto_close,
        closable: draft.closable,
        pausable: draft.pausable,
        renewable: draft.renewable,
        active: draft.active,
      }
      return plan ? api.put<Plan>(`/plans/${plan.id}`, body) : api.post<Plan>('/plans', body)
    },
    onSuccess: done,
    onError: fail,
  })
  const remove = useMutation({ mutationFn: () => api.delete(`/plans/${plan!.id}`), onSuccess: done, onError: fail })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    save.mutate()
  }

  const f = error?.fields ?? {}
  const shownInline = Object.keys(f).some((k) => k in draft)
  const generalError = error && !shownInline ? error.message : undefined

  return (
    <>
      <PageHeader
        title={plan ? plan.name : 'New plan'}
        description={readOnly ? 'View only. Only an admin can change plans.' : undefined}
        actions={
          <Link to="/plans" className="text-sm text-muted hover:underline">
            ← All plans
          </Link>
        }
      />
      <form onSubmit={onSubmit} noValidate className="grid max-w-3xl gap-6">
        <fieldset disabled={readOnly} className="grid gap-6">
          <Card className="grid gap-4 p-5 sm:grid-cols-2">
            <FormField label="Name" htmlFor="name" error={f.name} className="sm:col-span-2">
              <Input id="name" value={draft.name} onChange={(e) => set('name', e.target.value)} required error={!!f.name} />
            </FormField>
            <FormField label="Billing period" htmlFor="billing_period" error={f.billing_period}>
              <Select id="billing_period" value={draft.billing_period} onChange={(e) => set('billing_period', e.target.value as BillingPeriod)}>
                {Object.entries(PERIOD_LABEL).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField label="Price" htmlFor="price" error={f.price}>
              <Input id="price" inputMode="decimal" value={draft.price} onChange={(e) => set('price', e.target.value)} error={!!f.price} />
            </FormField>
            <FormField label="Minimum quantity" htmlFor="min_quantity" error={f.min_quantity} hint="Total quantity a subscription on this plan must have.">
              <Input id="min_quantity" type="number" min={1} value={draft.min_quantity} onChange={(e) => set('min_quantity', e.target.value)} error={!!f.min_quantity} />
            </FormField>
            <div className="flex items-end pb-2">
              <Checkbox label="Active" hint="Inactive plans can't be picked for new subscriptions." checked={draft.active} onChange={(e) => set('active', e.target.checked)} />
            </div>
            <FormField label="Available from" htmlFor="available_from" error={f.available_from} hint="Leave empty for no start date.">
              <Input id="available_from" type="date" value={draft.available_from} onChange={(e) => set('available_from', e.target.value)} />
            </FormField>
            <FormField label="Available until" htmlFor="available_to" error={f.available_to} hint="Leave empty for no end date.">
              <Input id="available_to" type="date" value={draft.available_to} onChange={(e) => set('available_to', e.target.value)} />
            </FormField>
          </Card>

          <Card className="grid gap-3 p-5">
            <h2 className="font-medium">What can happen to subscriptions on this plan</h2>
            <Checkbox label="Close automatically when it ends" hint="Subscriptions close themselves once past their expiry date." checked={draft.auto_close} onChange={(e) => set('auto_close', e.target.checked)} />
            <Checkbox label="Can be closed early" hint="Staff can close an active subscription before it expires." checked={draft.closable} onChange={(e) => set('closable', e.target.checked)} />
            <Checkbox label="Can be paused" hint="Billing stops while paused and resumes later." checked={draft.pausable} onChange={(e) => set('pausable', e.target.checked)} />
            <Checkbox label="Can be renewed" hint="Staff can extend the expiry date by one billing period." checked={draft.renewable} onChange={(e) => set('renewable', e.target.checked)} />
          </Card>
        </fieldset>

        {generalError && <Alert>{generalError}</Alert>}
        {!readOnly && (
          <div className="flex items-center justify-between">
            <div>
              {plan && (
                <Button type="button" variant="ghost" className="text-danger" disabled={remove.isPending} onClick={() => confirm(`Delete ${plan.name}?`) && remove.mutate()}>
                  Delete plan
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Link to="/plans" className="inline-flex h-9 items-center rounded-md border border-line px-3 text-sm hover:bg-surface">
                Cancel
              </Link>
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? 'Saving…' : 'Save plan'}
              </Button>
            </div>
          </div>
        )}
      </form>
    </>
  )
}
