import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, ApiError } from '@/lib/api'
import { formatDate, money } from '@/lib/format'
import type { AddonOption, Addons, PortalSubscription } from '@/lib/types'
import { Alert, Input, Select } from './forms'
import { useToast } from './Toast'
import { Badge, Button, Card } from './ui'

type LineIn = { product_id: number; variant_id: number | null; quantity: number }

/**
 * Switch add-ons on and off on a live subscription. Shared by staff and the portal (`base` picks the endpoints);
 * the server decides what is allowed and says why when it isn't. A change counts from the next invoice.
 */
export function AddonsPanel({ sub, base }: { sub: PortalSubscription; base: '/subscriptions' | '/portal-subscriptions' }) {
  const qc = useQueryClient()
  const { toast } = useToast()
  const [error, setError] = useState<string>()
  const live = sub.status === 'ACTIVE' || sub.status === 'PAUSED'
  const addons = useQuery({
    queryKey: [base, sub.id, 'addons'],
    queryFn: () => api.get<Addons>(`${base}/${sub.id}/addons`),
    enabled: live,
  })

  const refresh = () => qc.invalidateQueries({ queryKey: [base] })
  const switchOn = useMutation({
    mutationFn: (line: LineIn) => api.post(`${base}/${sub.id}/addons`, line),
    onSuccess: () => refresh(),
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not switch it on. Try again.'),
  })
  const switchOff = useMutation({
    mutationFn: (lineId: number) => api.delete(`${base}/${sub.id}/addons/${lineId}`),
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not switch it off. Try again.'),
  })

  if (!live || !addons.data || addons.data.options.length === 0) return null
  const { editable, blocker, min_quantity, options } = addons.data
  const pending = switchOn.isPending || switchOff.isPending
  const from = sub.next_invoice_date ? `the invoice on ${formatDate(sub.next_invoice_date)}` : 'the next invoice'

  const on = (option: AddonOption, line: LineIn) => {
    setError(undefined)
    switchOn.mutate(line, { onSuccess: () => toast(`${option.name} switched on. It’s billed from ${from}.`) })
  }
  const off = (option: AddonOption) => {
    const current = sub.lines.find((l) => l.id === option.line_id)
    setError(undefined)
    switchOff.mutate(option.line_id!, {
      onSuccess: () => {
        refresh()
        toast({
          message: `${option.name} switched off`,
          actionLabel: current ? 'Undo' : undefined,
          onAction: current
            ? () =>
                void api
                  .post(`${base}/${sub.id}/addons`, { product_id: current.product_id, variant_id: current.variant_id, quantity: current.quantity })
                  .then(() => (refresh(), toast(`${option.name} is back on`)))
                  .catch((e) => toast(e instanceof ApiError ? e.message : 'Could not undo'))
            : undefined,
        })
      },
    })
  }

  return (
    <Card className="p-5">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-medium">Add-ons</h3>
        <p className="text-[12px] text-muted">Changes count from {from}. Nothing already invoiced changes.</p>
      </div>
      {!editable && blocker && (
        <div className="mb-3">
          <Alert kind="info">{blocker}</Alert>
        </div>
      )}
      <ul className="divide-y divide-line">
        {options.map((option) => (
          <AddonRow key={option.product_id} option={option} minQuantity={min_quantity} disabled={!editable || pending} onOn={(line) => on(option, line)} onOff={() => off(option)} />
        ))}
      </ul>
      {error && (
        <div className="mt-3">
          <Alert>{error}</Alert>
        </div>
      )}
    </Card>
  )
}

function AddonRow({ option, minQuantity, disabled, onOn, onOff }: { option: AddonOption; minQuantity: number; disabled: boolean; onOn: (line: LineIn) => void; onOff: () => void }) {
  const [variantId, setVariantId] = useState(option.variants[0]?.id ?? null)
  const [quantity, setQuantity] = useState(String(minQuantity))
  const isOn = option.line_id !== null
  const extra = option.variants.find((v) => v.id === variantId)?.extra_price ?? '0'
  const taxes = option.taxes.length ? ` + ${option.taxes.join(', ')}` : ''

  return (
    <li className="flex flex-wrap items-center gap-3 py-3">
      <div className="min-w-48 flex-1">
        <p className="flex items-center gap-2 text-[13px] font-medium">
          {option.name}
          {isOn && <Badge className="border-green/30 bg-green/10 text-green">On · {option.quantity}</Badge>}
        </p>
        <p className="text-[12px] text-muted">
          {money(Number(option.unit_price) + Number(extra))} each{taxes}
          {option.notes ? ` · ${option.notes}` : ''}
        </p>
      </div>
      {isOn ? (
        <Button variant="outline" disabled={disabled} onClick={onOff}>
          Switch off
        </Button>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {option.variants.length > 0 && (
            <Select aria-label={`${option.name} variant`} value={variantId ?? ''} onChange={(e) => setVariantId(Number(e.target.value))} className="w-40" disabled={disabled}>
              {option.variants.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                  {Number(v.extra_price) ? ` (+${money(v.extra_price)})` : ''}
                </option>
              ))}
            </Select>
          )}
          <Input aria-label={`${option.name} quantity`} type="number" min={minQuantity} value={quantity} onChange={(e) => setQuantity(e.target.value)} className="w-20" disabled={disabled} />
          <Button disabled={disabled || !(Number(quantity) >= 1)} onClick={() => onOn({ product_id: option.product_id, variant_id: variantId, quantity: Number(quantity) })}>
            Switch on
          </Button>
        </div>
      )}
    </li>
  )
}
