import { useState } from 'react'
import { FinanceOverview } from '@/components/FinanceOverview'
import { DateField } from '@/components/DateField'
import { PageHeader } from '@/components/ui'

export default function ReportsPage() {
  const [fromDate, setFromDate] = useState(''); const [toDate, setToDate] = useState('')
  return <><PageHeader title="Reports" description="Filter invoiced and collected totals by accounting period." /><div className="mb-5 flex flex-wrap gap-3 border border-line bg-paper p-3"><DateField id="report-from" label="From" value={fromDate} onChange={setFromDate} optional /><DateField id="report-to" label="To" value={toDate} onChange={setToDate} optional /></div><FinanceOverview fromDate={fromDate} toDate={toDate} /></>
}
