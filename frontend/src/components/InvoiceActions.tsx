import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useAuth } from '@/auth/context'
import { api, ApiError } from '@/lib/api'
import { ACTION_DONE, ACTION_LABEL } from '@/lib/invoices'
import type { Invoice, InvoiceAction } from '@/lib/types'
import { ConfirmDialog } from './ConfirmDialog'
import { useToast } from './Toast'
import { buttonClass } from './button-class'
import { Button } from './ui'

/** Buttons for what the server says may be done to this invoice right now (`allowed_actions`). */
export function InvoiceActions({ invoice }: { invoice: Invoice }) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { user } = useAuth()
  const [askingToCancel, setAskingToCancel] = useState(false)

  const act = useMutation({
    mutationFn: (action: InvoiceAction) => api.post<Invoice>(`/invoices/${invoice.id}/${action}`),
    onSuccess: (_, action) => {
      queryClient.invalidateQueries({ queryKey: ['/invoices'] })
      queryClient.invalidateQueries({ queryKey: ['/reports'] })
      setAskingToCancel(false)
      toast(ACTION_DONE[action] ?? 'Done.')
    },
    onError: (e) => toast(e instanceof ApiError ? e.message : 'That did not work. Try again.'),
  })

  // Re-billing is admin only on the server; staff don't see the button.
  const buttons = invoice.allowed_actions.filter(
    (action) => action !== 'pay' && (action !== 'rebill' || user?.role === 'ADMIN'),
  )
  return (
    <>
      <div className="flex flex-wrap gap-2">
        {buttons.map((action, index) =>
          action === 'print' ? (
            <a key={action} href={`/api/invoices/${invoice.id}/print`} target="_blank" rel="noreferrer" className={buttonClass('outline')}>
              {ACTION_LABEL.print}
            </a>
          ) : (
            <Button
              key={action}
              variant={index === 0 ? 'primary' : 'outline'}
              className={action === 'cancel' ? 'text-danger' : undefined}
              disabled={act.isPending}
              onClick={() => (action === 'cancel' ? setAskingToCancel(true) : act.mutate(action))}
            >
              {ACTION_LABEL[action]}
            </Button>
          ),
        )}
      </div>
      <ConfirmDialog open={askingToCancel} onClose={() => setAskingToCancel(false)} onConfirm={() => act.mutate('cancel')} pending={act.isPending} title="Cancel this invoice?" confirmLabel="Cancel invoice">
        This can’t be undone. The invoice stays in the ledger as cancelled, and its billing period is not billed again automatically.
      </ConfirmDialog>
    </>
  )
}
