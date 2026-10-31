import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { ActionButtons } from '@/components/ActionButtons'
import { Alert } from '@/components/forms'
import { SubscriptionView } from '@/components/SubscriptionView'
import { PageHeader } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import type { PortalSubscription } from '@/lib/types'

export default function PortalSubscriptionDetail() {
  const { id } = useParams()
  const sub = useQuery({ queryKey: ['/portal-subscriptions', Number(id)], queryFn: () => api.get<PortalSubscription>(`/portal-subscriptions/${id}`) })

  return (
    <>
      <PageHeader
        title="Subscription"
        actions={
          <Link to="/portal/subscriptions" className="text-sm text-muted hover:underline">
            ← My subscriptions
          </Link>
        }
      />
      {sub.isPending ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : sub.isError ? (
        <Alert>{sub.error instanceof ApiError && sub.error.status === 404 ? 'We couldn’t find that subscription.' : 'Could not load the subscription.'}</Alert>
      ) : (
        <div className="max-w-4xl">
          <SubscriptionView
            sub={sub.data}
            actions={
              <>
                <ActionButtons sub={sub.data} base="/portal-subscriptions" />
                {(sub.data.status === 'ACTIVE' || sub.data.status === 'PAUSED') && sub.data.allowed_actions.length === 0 && (
                  <Alert kind="info">Changes to this plan can’t be made online. Get in touch with us if you need to change it.</Alert>
                )}
              </>
            }
          />
        </div>
      )}
    </>
  )
}
