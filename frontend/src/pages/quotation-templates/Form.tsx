import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { Alert, FormField, Input, Select, Textarea } from '@/components/forms'
import { LinesEditor } from '@/components/LinesEditor'
import { Button, Card, PageHeader } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { EMPTY_LINE, type LineDraft } from '@/lib/lines'
import { usePlans, useProducts } from '@/lib/queries'
import { PERIOD_LABEL, type Template } from '@/lib/types'

type Draft = { name: string; plan_id: string; validity_days: string; notes: string; lines: LineDraft[] }

export default function TemplateFormPage() {
  const { id } = useParams()
  const template = useQuery({ queryKey: ['template', id], queryFn: () => api.get<Template>(`/quotation-templates/${id}`), enabled: !!id })
  if (id && template.isPending) return <p className="text-sm text-muted">Loading…</p>
  if (id && template.isError) return <Alert>{template.error instanceof ApiError ? template.error.message : 'Could not load the template.'}</Alert>
  return <TemplateEditor key={id ?? 'new'} template={template.data} />
}

function TemplateEditor({ template }: { template?: Template }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const products = useProducts()
  const plans = usePlans()
  const [error, setError] = useState<ApiError>()
  const [draft, setDraft] = useState<Draft>(
    template
      ? {
          name: template.name,
          plan_id: String(template.plan.id),
          validity_days: String(template.validity_days),
          notes: template.notes ?? '',
          lines: template.lines.map((l) => ({ product_id: String(l.product_id), variant_id: l.variant_id ? String(l.variant_id) : '', quantity: String(l.quantity) })),
        }
      : { name: '', plan_id: '', validity_days: '30', notes: '', lines: [{ ...EMPTY_LINE }] },
  )
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((d) => ({ ...d, [key]: value }))
  const plan = plans.data?.find((p) => String(p.id) === draft.plan_id)

  const done = () => {
    qc.invalidateQueries({ queryKey: ['templates'] })
    qc.invalidateQueries({ queryKey: ['template'] })
    navigate('/quotation-templates')
  }
  const fail = (e: unknown) => setError(e instanceof ApiError ? e : new ApiError(0, 'Something went wrong. Try again.'))

  const save = useMutation({
    mutationFn: () => {
      const body = {
        name: draft.name,
        plan_id: Number(draft.plan_id),
        validity_days: Number(draft.validity_days),
        notes: draft.notes,
        lines: draft.lines.map((l) => ({ product_id: Number(l.product_id), variant_id: l.variant_id ? Number(l.variant_id) : null, quantity: Number(l.quantity) })),
      }
      return template ? api.put(`/quotation-templates/${template.id}`, body) : api.post('/quotation-templates', body)
    },
    onSuccess: done,
    onError: fail,
  })
  const remove = useMutation({ mutationFn: () => api.delete(`/quotation-templates/${template!.id}`), onSuccess: done, onError: fail })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    if (!draft.plan_id) return setError(new ApiError(422, 'Choose a plan.', { plan_id: 'Choose a plan.' }))
    if (draft.lines.some((l) => !l.product_id)) return setError(new ApiError(422, 'Every line needs a product.'))
    save.mutate()
  }

  const f = error?.fields ?? {}
  const inline = Object.keys(f).some((k) => ['name', 'plan_id', 'validity_days', 'notes'].includes(k) || k.startsWith('lines.'))
  const general = error && !inline ? error.message : undefined

  return (
    <>
      <PageHeader
        title={template ? template.name : 'New template'}
        actions={
          <Link to="/quotation-templates" className="text-sm text-muted hover:underline">
            ← All templates
          </Link>
        }
      />
      <form onSubmit={onSubmit} noValidate className="grid max-w-4xl gap-6">
        <Card className="grid gap-4 p-5 sm:grid-cols-2">
          <FormField label="Name" htmlFor="name" error={f.name} className="sm:col-span-2">
            <Input id="name" value={draft.name} onChange={(e) => set('name', e.target.value)} required error={!!f.name} />
          </FormField>
          <FormField label="Plan" htmlFor="plan" error={f.plan_id}>
            <Select id="plan" value={draft.plan_id} onChange={(e) => set('plan_id', e.target.value)} error={!!f.plan_id}>
              <option value="">Choose a plan…</option>
              {plans.data
                ?.filter((p) => p.active || String(p.id) === draft.plan_id)
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({PERIOD_LABEL[p.billing_period]})
                  </option>
                ))}
            </Select>
          </FormField>
          <FormField label="Quote valid for (days)" htmlFor="validity" error={f.validity_days} hint="Counted from the day the quote is sent.">
            <Input id="validity" type="number" min={1} max={365} value={draft.validity_days} onChange={(e) => set('validity_days', e.target.value)} error={!!f.validity_days} />
          </FormField>
          <FormField label="Notes" htmlFor="notes" error={f.notes} className="sm:col-span-2">
            <Textarea id="notes" value={draft.notes} onChange={(e) => set('notes', e.target.value)} />
          </FormField>
        </Card>

        <Card className="p-5">
          <h2 className="mb-1 font-medium">Lines</h2>
          <p className="mb-4 text-xs text-muted">
            {plan ? `Each line needs a quantity of at least ${plan.min_quantity} on ${plan.name}.` : 'Choose a plan to see its minimum quantity.'}
          </p>
          <LinesEditor lines={draft.lines} onChange={(lines) => set('lines', lines)} products={products.data} minQuantity={plan?.min_quantity ?? 1} errors={f} />
        </Card>

        {general && <Alert>{general}</Alert>}
        <div className="flex items-center justify-between">
          <div>
            {template && (
              <Button type="button" variant="ghost" className="text-danger" disabled={remove.isPending} onClick={() => confirm(`Delete ${template.name}?`) && remove.mutate()}>
                Delete template
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Link to="/quotation-templates" className="inline-flex h-9 items-center rounded-md border border-line px-3 text-sm hover:bg-surface">
              Cancel
            </Link>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? 'Saving…' : 'Save template'}
            </Button>
          </div>
        </div>
      </form>
    </>
  )
}
