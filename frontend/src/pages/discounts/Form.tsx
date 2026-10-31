import { type FormEvent, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ProductTargets, SubscriptionTargets } from '@/components/DiscountTargets'
import { Alert, Checkbox, FormField, Input, Select } from '@/components/forms'
import { FormActions } from '@/components/FormActions'
import { WithEntity } from '@/components/WithEntity'
import { Card, PageHeader } from '@/components/ui'
import { type DiscountDraft, discountToBody, discountToDraft } from '@/lib/discounts'
import { generalMessage, useEntityMutations } from '@/lib/entity'
import { todayISO } from '@/lib/format'
import type { Discount } from '@/lib/types'

const newDraft = (): DiscountDraft => ({
  name: '', kind: 'PERCENT', value: '', scope: 'PRODUCT', start_date: todayISO(), end_date: '',
  min_purchase: '', min_quantity: '', usage_limit: '', active: true, product_ids: [], subscription_ids: [],
})
const FIELDS = ['name', 'kind', 'value', 'scope', 'start_date', 'end_date', 'min_purchase', 'min_quantity', 'usage_limit', 'product_ids', 'subscription_ids']

export default function DiscountFormPage() {
  const { id } = useParams()
  return (
    <WithEntity<Discount> id={id} path="/discounts" label="discount">
      {(discount) => <DiscountEditor key={id ?? 'new'} discount={discount} />}
    </WithEntity>
  )
}

function DiscountEditor({ discount }: { discount?: Discount }) {
  const navigate = useNavigate()
  const [draft, setDraft] = useState<DiscountDraft>(discount ? discountToDraft(discount) : newDraft())
  const { save, remove, error, clearError } = useEntityMutations('/discounts', () => navigate('/discounts'))
  const set = <K extends keyof DiscountDraft>(key: K, value: DiscountDraft[K]) => setDraft((d) => ({ ...d, [key]: value }))

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    clearError()
    save.mutate({ id: discount?.id, body: discountToBody(draft) })
  }
  const askToDelete = () => remove.mutate(discount!.id)

  const f = error?.fields ?? {}
  const message = generalMessage(error, FIELDS)

  return (
    <>
      <PageHeader
        title={discount ? discount.name : 'New discount'}
        description={discount ? `Used ${discount.used_count} time${discount.used_count === 1 ? '' : 's'} so far.` : undefined}
        actions={<Link to="/discounts" className="text-sm text-muted hover:underline">← All discounts</Link>}
      />
      <form onSubmit={onSubmit} noValidate className="grid max-w-3xl gap-6">
        <Card className="grid gap-4 p-5 sm:grid-cols-2">
          <FormField label="Name" htmlFor="name" error={f.name} className="sm:col-span-2">
            <Input id="name" value={draft.name} onChange={(e) => set('name', e.target.value)} required error={!!f.name} />
          </FormField>
          <FormField label="Type" htmlFor="kind" error={f.kind}>
            <Select id="kind" value={draft.kind} onChange={(e) => set('kind', e.target.value as DiscountDraft['kind'])}>
              <option value="PERCENT">Percentage</option>
              <option value="FIXED">Fixed amount</option>
            </Select>
          </FormField>
          <FormField label={draft.kind === 'PERCENT' ? 'Percent off' : 'Amount off'} htmlFor="value" error={f.value}>
            <Input id="value" inputMode="decimal" value={draft.value} onChange={(e) => set('value', e.target.value)} required error={!!f.value} />
          </FormField>
          <FormField label="Starts" htmlFor="start_date" error={f.start_date}>
            <Input id="start_date" type="date" value={draft.start_date} onChange={(e) => set('start_date', e.target.value)} required error={!!f.start_date} />
          </FormField>
          <FormField label="Ends" htmlFor="end_date" error={f.end_date} hint="Leave empty for no end date.">
            <Input id="end_date" type="date" value={draft.end_date} onChange={(e) => set('end_date', e.target.value)} error={!!f.end_date} />
          </FormField>
        </Card>

        <Card className="grid gap-4 p-5 sm:grid-cols-3">
          <h2 className="font-medium sm:col-span-3">When it applies</h2>
          <FormField label="Minimum purchase" htmlFor="min_purchase" error={f.min_purchase} hint="Subscription subtotal.">
            <Input id="min_purchase" inputMode="decimal" value={draft.min_purchase} onChange={(e) => set('min_purchase', e.target.value)} error={!!f.min_purchase} />
          </FormField>
          <FormField label="Minimum quantity" htmlFor="min_quantity" error={f.min_quantity} hint="Total units on the subscription.">
            <Input id="min_quantity" type="number" min={1} value={draft.min_quantity} onChange={(e) => set('min_quantity', e.target.value)} error={!!f.min_quantity} />
          </FormField>
          <FormField label="Usage limit" htmlFor="usage_limit" error={f.usage_limit} hint="Invoices it may appear on.">
            <Input id="usage_limit" type="number" min={1} value={draft.usage_limit} onChange={(e) => set('usage_limit', e.target.value)} error={!!f.usage_limit} />
          </FormField>
        </Card>

        <Card className="grid gap-3 p-5">
          <FormField label="Applies to" htmlFor="scope">
            <Select id="scope" value={draft.scope} onChange={(e) => set('scope', e.target.value as DiscountDraft['scope'])} className="max-w-xs">
              <option value="PRODUCT">Specific products</option>
              <option value="SUBSCRIPTION">Specific subscriptions</option>
            </Select>
          </FormField>
          {draft.scope === 'PRODUCT' ? (
            <ProductTargets selected={draft.product_ids} onChange={(ids) => set('product_ids', ids)} />
          ) : (
            <SubscriptionTargets selected={draft.subscription_ids} onChange={(ids) => set('subscription_ids', ids)} />
          )}
          {(f.product_ids || f.subscription_ids) && <p className="text-xs text-danger">{f.product_ids ?? f.subscription_ids}</p>}
          <Checkbox label="Active" hint="Inactive discounts are never applied." checked={draft.active} onChange={(e) => set('active', e.target.checked)} />
        </Card>

        {message && <Alert>{message}</Alert>}
        <FormActions cancelTo="/discounts" saving={save.isPending} saveLabel="Save discount" onDelete={discount && askToDelete} deleteLabel="Delete discount" deleteName={discount?.name} />
      </form>
    </>
  )
}
