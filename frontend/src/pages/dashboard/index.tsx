import { FinanceOverview } from '@/components/FinanceOverview'
import { PageHeader } from '@/components/ui'

export default function DashboardPage() {
  return <><PageHeader title="Finance overview" description="Subscriptions, billing, collections, and overdue exposure in one view." /><FinanceOverview /></>
}
