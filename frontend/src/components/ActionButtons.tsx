import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, ApiError } from '@/lib/api'
import { actionInfo, sortActions } from '@/lib/subscriptions'
import type { PortalSubscription } from '@/lib/types'
import { Alert, FormField, Textarea } from './forms'
import { Modal } from './Modal'
import { Button } from './ui'

/**
 * One button per action the SERVER says is allowed right now (plan flags and status already applied).
 * `base` picks the staff or the portal endpoints; the buttons are the same, the server rules are too.
 */
export function ActionButtons({ sub, base }: { sub: PortalSubscription; base: '/subscriptions' | '/portal-subscriptions' }) {
  const qc = useQueryClient()
  const [asking, setAsking] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string>()

  const run = useMutation({
    mutationFn: ({ action, reason }: { action: string; reason?: string }) =>
      action === 'RENEW'
        ? api.post(`${base}/${sub.id}/renew`, { reason })
        : api.post(`${base}/${sub.id}/transition`, { to: action, reason }),
    onSuccess: () => {
      setAsking(null)
      setReason('')
      qc.invalidateQueries({ queryKey: [base] })
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'That didn’t work. Try again.'),
  })

  if (sub.allowed_actions.length === 0) return null

  const submit = (action: string, reasonText?: string) => {
    setError(undefined)
    run.mutate({ action, reason: reasonText?.trim() || undefined })
  }
  const dialog = asking ? actionInfo(sub.status, asking) : null

  return (
    <>
      <div className="flex flex-wrap gap-2">
        {sortActions(sub.allowed_actions).map((action, i) => {
          const info = actionInfo(sub.status, action)
          return (
            <Button
              key={action}
              variant={info.danger ? 'outline' : i === 0 ? 'primary' : 'outline'}
              className={info.danger ? 'border-danger/40 text-danger' : undefined}
              disabled={run.isPending}
              onClick={() => (info.askReason ? (setError(undefined), setAsking(action)) : submit(action))}
            >
              {info.label}
            </Button>
          )
        })}
      </div>
      {error && !asking && (
        <div className="mt-3">
          <Alert>{error}</Alert>
        </div>
      )}

      <Modal open={asking !== null} onClose={() => setAsking(null)} title={dialog ? `${dialog.label} ${sub.number}?` : ''}>
        {asking && dialog && (
          <div className="grid gap-4">
            {dialog.help && <p className="text-sm text-muted">{dialog.help}</p>}
            <FormField label="Reason (optional)" htmlFor="reason">
              <Textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} />
            </FormField>
            {error && <Alert>{error}</Alert>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setAsking(null)}>
                Not now
              </Button>
              <Button
                className={dialog.danger ? 'bg-danger text-white hover:opacity-90' : undefined}
                disabled={run.isPending}
                onClick={() => submit(asking, reason)}
              >
                {run.isPending ? 'Working…' : dialog.label}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </>
  )
}
