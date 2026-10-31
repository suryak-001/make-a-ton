import { useQuery } from '@tanstack/react-query'
import { DataTable } from '@/components/DataTable'
import { PageHeader } from '@/components/ui'
import { api, type Page } from '@/lib/api'
import { formatDate, money } from '@/lib/format'
import type { Payment } from '@/lib/types'

export default function PaymentsPage() {
  const list = useQuery({ queryKey: ['/payments'], queryFn: () => api.get<Page<Payment>>('/payments?page_size=100') })
  return <><PageHeader title="Payments" description="Collected amounts and the invoices they settled." /><DataTable loading={list.isPending} rows={list.data?.items} rowKey={(p) => p.id} empty="No payments have been recorded." columns={[
    { header: 'Date', cell: (p) => formatDate(p.payment_date) }, { header: 'Invoice', cell: (p) => p.invoice_number ?? `Invoice #${p.invoice_id}` }, { header: 'Customer', cell: (p) => p.customer_name }, { header: 'Method', cell: (p) => p.method.replaceAll('_', ' ').toLowerCase() }, { header: 'Note', cell: (p) => p.note ?? '—' }, { header: 'Amount', className: 'text-right font-medium', cell: (p) => money(p.amount) },
  ]} /></>
}
