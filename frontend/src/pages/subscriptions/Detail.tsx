import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ActionButtons } from '@/components/ActionButtons'
import { AddonsPanel } from '@/components/AddonsPanel'
import { Alert } from '@/components/forms'
import { SubscriptionView } from '@/components/SubscriptionView'
import { buttonClass } from '@/components/button-class'
import { Button, PageHeader } from '@/components/ui'
import { ConfirmDialog } from '@/components/ConfirmDialog'
import { api, ApiError } from '@/lib/api'
import type { Subscription } from '@/lib/types'

export default function SubscriptionDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [error, setError] = useState<string>()
  const [confirmDelete, setConfirmDelete] = useState(false)

  const sub = useQuery({ queryKey: ['/subscriptions', Number(id)], queryFn: () => api.get<Subscription>(`/subscriptions/${id}`) })
  const remove = useMutation({
    mutationFn: () => api.delete(`/subscriptions/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['/subscriptions'] })
      navigate('/subscriptions')
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not delete.'),
  })

  return (
    <>
      <PageHeader
        title="Subscription"
        actions={
          <Link to="/subscriptions" className="text-sm text-muted hover:underline">
            ← All subscriptions
          </Link>
        }
      />
      {sub.isPending ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : sub.isError ? (
        <Alert>{sub.error instanceof ApiError ? sub.error.message : 'Could not load the subscription.'}</Alert>
      ) : (
        <div className="grid max-w-4xl gap-4">
          <SubscriptionView
            staff
            sub={sub.data}
            afterLines={<AddonsPanel sub={sub.data} base="/subscriptions" />}
            actions={
              <div className="flex flex-wrap items-start justify-between gap-3">
                <ActionButtons sub={sub.data} base="/subscriptions" />
                <div className="flex gap-2">
                  {sub.data.editable && (
                    <Link to="edit" className={buttonClass('outline')}>
                      Edit
                    </Link>
                  )}
                  {sub.data.status === 'DRAFT' && (
                    <Button variant="ghost" className="text-danger" disabled={remove.isPending} onClick={() => setConfirmDelete(true)}>
                      Delete draft
                    </Button>
                  )}
                </div>
              </div>
            }
          />
          {error && <Alert>{error}</Alert>}
        </div>
      )}
      <ConfirmDialog open={confirmDelete} onClose={() => setConfirmDelete(false)} onConfirm={() => remove.mutate()} pending={remove.isPending} title="Delete this draft?" confirmLabel="Delete draft">The draft and its unsent line items will be permanently removed.</ConfirmDialog>
    </>
  )
}
