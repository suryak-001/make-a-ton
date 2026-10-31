import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { BillingRunResult } from '@/components/BillingRunResult'
import { DateField } from '@/components/DateField'
import { Alert } from '@/components/forms'
import { Button, Card, PageHeader } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { todayISO } from '@/lib/format'
import type { BillingRun } from '@/lib/types'

export default function BillingRunPage() {
  const queryClient = useQueryClient()
  const [asOf, setAsOf] = useState(todayISO())
  const run = useMutation({
    mutationFn: () => api.post<BillingRun>('/invoices/run-billing', { as_of: asOf }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/invoices'] })
      queryClient.invalidateQueries({ queryKey: ['/reports'] })
    },
  })

  return (
    <>
      <PageHeader
        title="Billing run"
        description="Creates a draft invoice for every billing period that is due. Nothing is billed twice and a missed day is caught up, so running it again is always safe."
        actions={<Link to="/invoices" className="text-sm text-muted hover:underline">View invoices →</Link>}
      />
      <Card className="mb-5 flex flex-wrap items-end gap-3 p-4">
        <DateField id="as-of" label="Bill through" value={asOf} onChange={setAsOf} />
        <Button disabled={run.isPending || !asOf} onClick={() => run.mutate()}>
          {run.isPending ? 'Running…' : run.data ? 'Run again' : 'Run billing'}
        </Button>
      </Card>
      {run.error && <Alert>{run.error instanceof ApiError ? run.error.message : 'The billing run failed. Try again.'}</Alert>}
      {run.data && <BillingRunResult run={run.data} />}
    </>
  )
}
