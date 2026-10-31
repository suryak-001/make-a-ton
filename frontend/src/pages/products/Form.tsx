import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useAuth } from '@/auth/context'
import { Alert, Checkbox, FormField, Input, Select, Textarea } from '@/components/forms'
import { TaxPicker } from '@/components/TaxPicker'
import { Button, Card, PageHeader } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import type { Product } from '@/lib/types'

type VariantDraft = { id?: number; attribute: string; value: string; extra_price: string }
type Draft = {
  name: string
  type: 'SERVICE' | 'GOODS'
  sales_price: string
  cost_price: string
  notes: string
  active: boolean
  variants: VariantDraft[]
  default_tax_ids: number[]
}

const EMPTY: Draft = { name: '', type: 'SERVICE', sales_price: '', cost_price: '0', notes: '', active: true, variants: [], default_tax_ids: [] }

function toDraft(p: Product): Draft {
  return {
    name: p.name,
    type: p.type,
    sales_price: p.sales_price,
    cost_price: p.cost_price,
    notes: p.notes ?? '',
    active: p.active,
    variants: p.variants.map((v) => ({ id: v.id, attribute: v.attribute, value: v.value, extra_price: v.extra_price })),
    default_tax_ids: p.default_taxes.map((t) => t.id),
  }
}

export default function ProductFormPage() {
  const { id } = useParams()
  const product = useQuery({
    queryKey: ['product', id],
    queryFn: () => api.get<Product>(`/products/${id}`),
    enabled: !!id,
  })
  if (id && product.isPending) return <p className="text-sm text-muted">Loading…</p>
  if (id && product.isError) return <Alert>{product.error instanceof ApiError ? product.error.message : 'Could not load the product.'}</Alert>
  return <ProductEditor key={id ?? 'new'} product={product.data} />
}

function ProductEditor({ product }: { product?: Product }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const readOnly = user?.role !== 'ADMIN'
  const [draft, setDraft] = useState<Draft>(product ? toDraft(product) : EMPTY)
  const [error, setError] = useState<ApiError>()

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setDraft((d) => ({ ...d, [key]: value }))
  const setVariant = (i: number, patch: Partial<VariantDraft>) =>
    set('variants', draft.variants.map((v, j) => (j === i ? { ...v, ...patch } : v)))

  const save = useMutation({
    mutationFn: () => {
      const body = {
        ...draft,
        sales_price: draft.sales_price || '0',
        cost_price: draft.cost_price || '0',
        variants: draft.variants.map((v) => ({ ...v, extra_price: v.extra_price || '0' })),
      }
      return product ? api.put<Product>(`/products/${product.id}`, body) : api.post<Product>('/products', body)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      qc.invalidateQueries({ queryKey: ['product'] })
      navigate('/products')
    },
    onError: (e) => setError(e instanceof ApiError ? e : new ApiError(0, 'Could not save. Try again.')),
  })

  const remove = useMutation({
    mutationFn: () => api.delete(`/products/${product!.id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      navigate('/products')
    },
    onError: (e) => setError(e instanceof ApiError ? e : new ApiError(0, 'Could not delete. Try again.')),
  })

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    save.mutate()
  }

  const f = error?.fields ?? {}
  // Field errors render under their input; anything else (conflicts, whole-form errors) goes in the alert.
  const shownInline = Object.keys(f).some((k) => ['name', 'type', 'sales_price', 'cost_price', 'notes'].includes(k) || /^variants\.\d/.test(k))
  const generalError = error && !shownInline ? error.message : undefined

  return (
    <>
      <PageHeader
        title={product ? product.name : 'New product'}
        description={readOnly ? 'View only. Only an admin can change products.' : undefined}
        actions={
          <Link to="/products" className="text-sm text-muted hover:underline">
            ← All products
          </Link>
        }
      />
      <form onSubmit={onSubmit} noValidate className="grid max-w-3xl gap-6">
        <fieldset disabled={readOnly} className="grid gap-6">
          <Card className="grid gap-4 p-5 sm:grid-cols-2">
            <FormField label="Name" htmlFor="name" error={f.name} className="sm:col-span-2">
              <Input id="name" value={draft.name} onChange={(e) => set('name', e.target.value)} required error={!!f.name} />
            </FormField>
            <FormField label="Type" htmlFor="type" error={f.type}>
              <Select id="type" value={draft.type} onChange={(e) => set('type', e.target.value as Draft['type'])}>
                <option value="SERVICE">Service</option>
                <option value="GOODS">Goods</option>
              </Select>
            </FormField>
            <div className="flex items-end pb-2">
              <Checkbox label="Active" hint="Inactive products can't be added to new subscriptions." checked={draft.active} onChange={(e) => set('active', e.target.checked)} />
            </div>
            <FormField label="Sales price" htmlFor="sales_price" error={f.sales_price}>
              <Input id="sales_price" inputMode="decimal" value={draft.sales_price} onChange={(e) => set('sales_price', e.target.value)} required error={!!f.sales_price} />
            </FormField>
            <FormField label="Cost price" htmlFor="cost_price" error={f.cost_price}>
              <Input id="cost_price" inputMode="decimal" value={draft.cost_price} onChange={(e) => set('cost_price', e.target.value)} error={!!f.cost_price} />
            </FormField>
            <FormField label="Notes" htmlFor="notes" error={f.notes} className="sm:col-span-2">
              <Textarea id="notes" value={draft.notes} onChange={(e) => set('notes', e.target.value)} />
            </FormField>
            <div className="grid gap-1.5 sm:col-span-2">
              <span className="text-sm font-medium">Taxes</span>
              <TaxPicker selected={draft.default_tax_ids} onChange={(ids) => set('default_tax_ids', ids)} />
              <p className="text-xs text-muted">Added to every quote and invoice line for this product. Manage the rules on the Taxes page.</p>
            </div>
          </Card>

          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="font-medium">Variants</h2>
                <p className="text-xs text-muted">e.g. Brand → Odoo adds 560 to the price when chosen.</p>
              </div>
              {!readOnly && (
                <Button type="button" variant="outline" onClick={() => set('variants', [...draft.variants, { attribute: '', value: '', extra_price: '0' }])}>
                  Add variant
                </Button>
              )}
            </div>
            {draft.variants.length === 0 ? (
              <p className="text-sm text-muted">No variants.</p>
            ) : (
              <div className="grid gap-3">
                {draft.variants.map((v, i) => (
                  <div key={v.id ?? `new-${i}`} className="grid grid-cols-[1fr_1fr_8rem_auto] items-start gap-2">
                    <FormField label="Attribute" htmlFor={`attr-${i}`} error={f[`variants.${i}.attribute`]}>
                      <Input id={`attr-${i}`} value={v.attribute} onChange={(e) => setVariant(i, { attribute: e.target.value })} placeholder="Brand" />
                    </FormField>
                    <FormField label="Value" htmlFor={`val-${i}`} error={f[`variants.${i}.value`]}>
                      <Input id={`val-${i}`} value={v.value} onChange={(e) => setVariant(i, { value: e.target.value })} placeholder="Odoo" />
                    </FormField>
                    <FormField label="Extra price" htmlFor={`extra-${i}`} error={f[`variants.${i}.extra_price`]}>
                      <Input id={`extra-${i}`} inputMode="decimal" value={v.extra_price} onChange={(e) => setVariant(i, { extra_price: e.target.value })} />
                    </FormField>
                    {!readOnly && (
                      <Button type="button" variant="ghost" className="mt-6 text-danger" onClick={() => set('variants', draft.variants.filter((_, j) => j !== i))} aria-label={`Remove variant ${i + 1}`}>
                        Remove
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </fieldset>

        {generalError && <Alert>{generalError}</Alert>}
        {!readOnly && (
          <div className="flex items-center justify-between">
            <div>
              {product && (
                <Button type="button" variant="ghost" className="text-danger" disabled={remove.isPending} onClick={() => confirm(`Delete ${product.name}?`) && remove.mutate()}>
                  Delete product
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Link to="/products" className="inline-flex h-9 items-center rounded-md border border-line px-3 text-sm hover:bg-surface">
                Cancel
              </Link>
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? 'Saving…' : 'Save product'}
              </Button>
            </div>
          </div>
        )}
      </form>
    </>
  )
}
