import { useState } from 'react'
import { FinanceOverview } from '@/components/FinanceOverview'
import { ReportFilters } from '@/components/ReportFilters'
import { PageHeader } from '@/components/ui'
import type { ReportFilters as Filters } from '@/lib/types'

export default function ReportsPage() {
  const [filters, setFilters] = useState<Filters>({})
  return (
    <>
      <PageHeader title="Reports" description="Filter the finance numbers by period, plan or customer." />
      <ReportFilters values={filters} onChange={setFilters} />
      <FinanceOverview filters={filters} />
    </>
  )
}
