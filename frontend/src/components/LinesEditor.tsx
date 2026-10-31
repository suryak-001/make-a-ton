import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { type LineDraft, EMPTY_LINE } from '@/lib/lines'
import { money } from '@/lib/format'
import type { PricePreview, Product } from '@/lib/types'
import { FormField, Input, Select } from './forms'
import { Button } from './ui'


/** Price of one line as the server will store it: the form never does price math itself. */
function LineAmount({ product, variantId, quantity }: { product?: Product; variantId: string; quantity: string }) {
  const variant = product?.variants.find((v) => String(v.id) === variantId)
  const qty = Number(quantity)
  const valid = !!product && Number.isInteger(qty) && qty >= 1
  const preview = useQuery({
    queryKey: ['preview', product?.id, variant?.id, qty],
    enabled: valid,
    queryFn: () =>
      api.post<PricePreview>('/pricing/preview', {
        unit_price: product!.sales_price,
        variant_extra: variant?.extra_price ?? '0',
        quantity: qty,
        taxes: product!.default_taxes.filter((t) => t).map((t) => ({ kind: t.kind, rate: t.rate })),
      }),
    staleTime: 60_000,
  })
  if (!valid) return <span className="text-muted">—</span>
  if (!preview.data) return <span className="text-muted">…</span>
  return (
    <span title={`${money(preview.data.unit_price)} each, tax ${money(preview.data.tax_amount)}`} className="font-medium">
      {money(preview.data.total)}
    </span>
  )
}

/**
 * Product / variant / quantity rows, shared by subscriptions and quotation templates.
 * `errors` is ApiError.fields (keys like `lines.0.quantity`).
 */
export function LinesEditor({
  lines,
  onChange,
  products,
  minQuantity = 1,
  errors = {},
  showAmounts = false,
  disabled = false,
}: {
  lines: LineDraft[]
  onChange: (lines: LineDraft[]) => void
  products: Product[] | undefined
  minQuantity?: number
  errors?: Record<string, string>
  showAmounts?: boolean
  disabled?: boolean
}) {
  const setLine = (i: number, patch: Partial<LineDraft>) => onChange(lines.map((l, j) => (j === i ? { ...l, ...patch } : l)))
  const byId = (id: string) => products?.find((p) => String(p.id) === id)

  return (
    <div className="grid gap-3">
      {lines.map((line, i) => {
        const product = byId(line.product_id)
        const selectable = (products ?? []).filter((p) => p.active || String(p.id) === line.product_id)
        return (
          <div key={i} className={`grid items-start gap-2 ${showAmounts ? 'grid-cols-[2fr_1.4fr_6rem_7rem_auto]' : 'grid-cols-[2fr_1.4fr_6rem_auto]'}`}>
            <FormField label="Product" htmlFor={`line-${i}-product`} error={errors[`lines.${i}.product_id`]}>
              <Select
                id={`line-${i}-product`}
                value={line.product_id}
                disabled={disabled}
                error={!!errors[`lines.${i}.product_id`]}
                onChange={(e) => setLine(i, { product_id: e.target.value, variant_id: '' })}
              >
                <option value="">Choose a product…</option>
                {selectable.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} — {money(p.sales_price)}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField label="Variant" htmlFor={`line-${i}-variant`} error={errors[`lines.${i}.variant_id`]}>
              <Select
                id={`line-${i}-variant`}
                value={line.variant_id}
                disabled={disabled || !product || product.variants.length === 0}
                onChange={(e) => setLine(i, { variant_id: e.target.value })}
              >
                <option value="">{product && product.variants.length === 0 ? 'No variants' : 'Base price'}</option>
                {product?.variants.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.attribute}: {v.value}
                    {Number(v.extra_price) ? ` (+${money(v.extra_price)})` : ''}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField label="Qty" htmlFor={`line-${i}-qty`} error={errors[`lines.${i}.quantity`]}>
              <Input
                id={`line-${i}-qty`}
                type="number"
                min={minQuantity}
                step={1}
                value={line.quantity}
                disabled={disabled}
                error={!!errors[`lines.${i}.quantity`]}
                onChange={(e) => setLine(i, { quantity: e.target.value })}
              />
            </FormField>
            {showAmounts && (
              <div className="grid gap-1.5">
                <span className="text-sm font-medium">Amount</span>
                <span className="flex h-9 items-center text-sm">
                  <LineAmount product={product} variantId={line.variant_id} quantity={line.quantity} />
                </span>
              </div>
            )}
            {!disabled && (
              <Button type="button" variant="ghost" className="mt-6 text-danger" disabled={lines.length === 1} onClick={() => onChange(lines.filter((_, j) => j !== i))} aria-label={`Remove line ${i + 1}`}>
                Remove
              </Button>
            )}
          </div>
        )
      })}
      {!disabled && (
        <div>
          <Button type="button" variant="outline" onClick={() => onChange([...lines, { ...EMPTY_LINE, quantity: String(minQuantity) }])}>
            Add line
          </Button>
        </div>
      )}
    </div>
  )
}
