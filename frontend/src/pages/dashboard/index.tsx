import { useAuth } from '@/auth/context'
import { AgingCard, ProofPanel, SetupBanner } from '@/components/AdminExtras'
import { FinanceOverview } from '@/components/FinanceOverview'
import { PageHeader } from '@/components/ui'
import { WorkQueue } from '@/components/WorkQueue'

/** One route, a different first screen per role: the admin sees the money and the proof, staff see today's work. */
export default function DashboardPage() {
  const { user } = useAuth()
  if (user?.role !== 'ADMIN') {
    return <><PageHeader title="Today’s work" description="What needs doing now: invoices to confirm and chase, renewals and quotes that are running out." /><WorkQueue /></>
  }
  return <div className="grid gap-5">
    <PageHeader title="Finance overview" description="Subscriptions, billing, collections, and overdue exposure in one view." />
    <SetupBanner />
    <FinanceOverview />
    <div className="grid gap-4 xl:grid-cols-2"><AgingCard /><ProofPanel /></div>
  </div>
}
