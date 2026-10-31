import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { Download, FileSpreadsheet, Upload } from 'lucide-react'
import { type DragEvent, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
import { buttonClass } from '@/components/button-class'
import { DataTable } from '@/components/DataTable'
import { Alert, Input } from '@/components/forms'
import { Modal } from '@/components/Modal'
import { useToast } from '@/components/Toast'
import { Badge, Button, Card, PageHeader } from '@/components/ui'
import { api, ApiError, type Page, qs } from '@/lib/api'
import { formatDate, money } from '@/lib/format'
import { useDebounced } from '@/lib/hooks'
import { PAYMENT_METHODS } from '@/lib/invoices'
import type { Invoice, ReconcileResult, StatementPreview, StatementRow } from '@/lib/types'

type Hint = NonNullable<StatementRow['invoice']>
type Choice = { invoice: Hint | null; checked: boolean }

const CONFIDENCE: Record<string, { label: string; tone: string }> = {
  high: { label: 'Sure', tone: 'border-green/30 bg-green/10 text-green' },
  medium: { label: 'Likely', tone: 'border-brand/30 bg-brand/10 text-brand' },
  low: { label: 'Check', tone: 'border-yellow bg-yellow/20 text-ink' },
}

/** A suggestion starts ticked when it is sure or likely; an amount-only guess waits for a person to tick it. */
const initialChoice = (row: StatementRow): Choice => ({
  invoice: row.invoice,
  checked: row.status === 'matched' && row.confidence !== 'low',
})

/** Red when a person has to act: no match yet, or recording it failed. */
const needsAttention = (row: StatementRow, done?: ReconcileResult['results'][number]) => (done ? done.status === 'failed' : row.status === 'unmatched')

const fits = (row: StatementRow, invoice: Hint | null) => invoice !== null && Number(row.amount) <= Number(invoice.outstanding)

export default function ReconciliationPage() {
  const qc = useQueryClient()
  const { toast } = useToast()
  const fileInput = useRef<HTMLInputElement>(null)
  const [fileName, setFileName] = useState<string>()
  const [dragging, setDragging] = useState(false)
  const [choices, setChoices] = useState<Record<string, Choice>>({})
  const [picking, setPicking] = useState<StatementRow | null>(null)
  const [result, setResult] = useState<ReconcileResult>()

  const preview = useMutation({
    mutationFn: (csv: string) => api.post<StatementPreview>('/reconciliation/preview', { csv }),
    onSuccess: (data) => {
      setResult(undefined)
      setChoices(Object.fromEntries(data.rows.map((row) => [row.ref, initialChoice(row)])))
    },
  })

  const record = useMutation({
    mutationFn: (rows: StatementRow[]) =>
      api.post<ReconcileResult>('/reconciliation/apply', {
        items: rows.map((row) => ({
          ref: row.ref,
          invoice_id: choices[row.ref].invoice!.id,
          amount: row.amount,
          payment_date: row.date,
          method: row.method,
          description: row.description.slice(0, 480),
        })),
      }),
    onSuccess: (data) => {
      setResult(data)
      for (const key of ['/invoices', '/payments', '/reports', '/customers', 'customers']) qc.invalidateQueries({ queryKey: [key] })
      toast(`Recorded ${data.recorded} payment${data.recorded === 1 ? '' : 's'} (${money(data.amount_recorded)})`)
    },
  })

  const read = async (file: File | undefined) => {
    if (!file) return
    setFileName(file.name)
    preview.mutate(await file.text())
  }
  // Loads the sample straight into the preview, so nobody has to download and re-upload it.
  const trySample = async () => {
    const res = await fetch('/api/reconciliation/sample.csv', { credentials: 'same-origin' })
    if (!res.ok) return
    setFileName('sample-statement.csv')
    preview.mutate(await res.text())
  }
  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    void read(event.dataTransfer.files[0])
  }
  const reset = () => {
    preview.reset()
    record.reset()
    setResult(undefined)
    setFileName(undefined)
    if (fileInput.current) fileInput.current.value = ''
  }

  const rows = useMemo(() => preview.data?.rows ?? [], [preview.data])
  const outcome = useMemo(() => new Map(result?.results.map((r) => [r.ref, r]) ?? []), [result])
  const ready = rows.filter((row) => row.status !== 'already_recorded' && !outcome.has(row.ref) && choices[row.ref]?.checked && fits(row, choices[row.ref].invoice))
  const readyTotal = ready.reduce((sum, row) => sum + Number(row.amount), 0)
  const counts = {
    high: rows.filter((r) => r.confidence === 'high').length,
    medium: rows.filter((r) => r.confidence === 'medium').length,
    low: rows.filter((r) => r.confidence === 'low').length,
    unmatched: rows.filter((r) => r.status === 'unmatched').length,
    recorded: rows.filter((r) => r.status === 'already_recorded').length,
  }
  const choose = (ref: string, patch: Partial<Choice>) => setChoices((current) => ({ ...current, [ref]: { ...current[ref], ...patch } }))

  return (
    <>
      <PageHeader
        title="Bank reconciliation"
        description="Upload your bank’s statement export. Each credit is matched to an open invoice, with the reason shown. Nothing is recorded until you approve it, and a statement line can never be recorded twice."
        actions={
          <>
            <button type="button" className={buttonClass('primary', 'gap-1.5')} disabled={preview.isPending} onClick={() => void trySample()}>
              <FileSpreadsheet aria-hidden className="size-4" />
              Try with a sample statement
            </button>
            <a href="/api/reconciliation/sample.csv" download className={buttonClass('outline', 'gap-1.5')}>
              <Download aria-hidden className="size-4" />
              Download sample
            </a>
          </>
        }
      />

      {!preview.data ? (
        <Card
          onDragOver={(e) => (e.preventDefault(), setDragging(true))}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={clsx('grid place-items-center gap-3 border-dashed px-6 py-14 text-center transition-colors', dragging && 'border-brand bg-brand/5')}
        >
          <span className="grid size-11 place-items-center rounded-full bg-surface">
            <Upload aria-hidden className="size-5 text-muted" />
          </span>
          <div>
            <p className="font-medium">{preview.isPending ? `Reading ${fileName}…` : 'Drop a bank statement CSV here'}</p>
            <p className="mt-1 max-w-md text-[13px] text-muted">Works with the usual exports: Date, Narration or Description, and Deposit, Credit or Amount columns. Debits are skipped.</p>
          </div>
          <input ref={fileInput} type="file" accept=".csv,text/csv" className="sr-only" id="statement" onChange={(e) => void read(e.target.files?.[0])} />
          <label htmlFor="statement" className={buttonClass('primary', 'cursor-pointer')}>
            Choose file
          </label>
          {preview.isError && <Alert>{preview.error instanceof ApiError ? preview.error.message : 'Could not read the statement.'}</Alert>}
        </Card>
      ) : (
        <div className="grid gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-line bg-paper p-3">
            <div className="flex flex-wrap items-center gap-2 text-[13px]">
              <span className="font-medium">{fileName}</span>
              <span className="text-muted">· {rows.length} credit{rows.length === 1 ? '' : 's'}</span>
              {counts.high > 0 && <Badge className={CONFIDENCE.high.tone}>{counts.high} sure</Badge>}
              {counts.medium > 0 && <Badge className={CONFIDENCE.medium.tone}>{counts.medium} likely</Badge>}
              {counts.low > 0 && <Badge className={CONFIDENCE.low.tone}>{counts.low} to check</Badge>}
              {counts.unmatched > 0 && <Badge className="bg-surface text-muted">{counts.unmatched} to place by hand</Badge>}
              {counts.recorded > 0 && <Badge className="bg-ink/5 text-muted">{counts.recorded} recorded before</Badge>}
              {preview.data.debits_skipped > 0 && <span className="text-muted">· {preview.data.debits_skipped} debit{preview.data.debits_skipped === 1 ? '' : 's'} skipped</span>}
            </div>
            <Button variant="ghost" onClick={reset}>
              Upload another
            </Button>
          </div>

          {preview.data.problems.length > 0 && (
            <Alert>
              {preview.data.problems.length} row{preview.data.problems.length === 1 ? '' : 's'} couldn’t be read and {preview.data.problems.length === 1 ? 'was' : 'were'} left out:{' '}
              {preview.data.problems.slice(0, 5).map((p) => `row ${p.line} (${p.error})`).join('; ')}
              {preview.data.problems.length > 5 ? '…' : ''}
            </Alert>
          )}
          {result && (
            <Alert kind={result.failed ? 'error' : 'success'}>
              Recorded {result.recorded} payment{result.recorded === 1 ? '' : 's'} totalling {money(result.amount_recorded)}.
              {result.already_recorded > 0 && ` ${result.already_recorded} had been recorded before.`}
              {result.failed > 0 && ` ${result.failed} could not be recorded; the reason is on each row.`}{' '}
              <Link to="/payments" className="underline">
                See payments
              </Link>
            </Alert>
          )}

          <DataTable
            rows={rows}
            rowKey={(row) => row.ref}
            empty="This statement has no credits."
            columns={[
              {
                header: 'Credit',
                cell: (row) => <CreditCell row={row} choice={choices[row.ref]} done={outcome.get(row.ref)} onToggle={(checked) => choose(row.ref, { checked })} />,
              },
              {
                header: 'Narration',
                className: 'max-w-[340px]',
                cell: (row) => (
                  <div className="min-w-0 whitespace-normal">
                    <p className="break-words text-[12px]">{row.description}</p>
                    <p className={clsx('mt-1 text-[12px]', needsAttention(row, outcome.get(row.ref)) ? 'text-danger' : 'text-muted')}>{outcome.get(row.ref)?.message ?? row.reason}</p>
                  </div>
                ),
              },
              {
                header: 'Invoice',
                cell: (row) => <InvoiceCell row={row} choice={choices[row.ref]} locked={row.status === 'already_recorded' || outcome.has(row.ref)} onPick={() => setPicking(row)} />,
              },
              {
                header: 'Match',
                cell: (row) =>
                  row.status === 'already_recorded' ? (
                    <Badge className="bg-ink/5 text-muted">Recorded before</Badge>
                  ) : row.confidence ? (
                    <Badge className={CONFIDENCE[row.confidence].tone}>{CONFIDENCE[row.confidence].label}</Badge>
                  ) : choices[row.ref]?.invoice ? (
                    <Badge className="bg-surface text-ink">Picked</Badge>
                  ) : (
                    <Badge className="bg-surface text-muted">No match</Badge>
                  ),
              },
            ]}
          />

          <div className="sticky bottom-3 z-10 flex flex-wrap items-center justify-between gap-3 rounded-md border border-ink bg-ink px-4 py-3 text-paper shadow-[4px_4px_0_#1849d6]">
            <p className="text-[13px]">
              {ready.length ? (
                <>
                  <span className="font-medium">{ready.length}</span> payment{ready.length === 1 ? '' : 's'} ready · <span className="font-medium tabular-nums">{money(readyTotal)}</span>
                </>
              ) : result ? (
                'Done. Upload the next statement whenever it arrives; lines already recorded are recognised.'
              ) : (
                'Tick the lines to record, or pick an invoice for the ones without a match.'
              )}
            </p>
            <Button className="border-yellow bg-yellow text-ink hover:bg-yellow/90" disabled={!ready.length || record.isPending} onClick={() => record.mutate(ready)}>
              {record.isPending ? 'Recording…' : `Record ${ready.length || ''} payment${ready.length === 1 ? '' : 's'}`}
            </Button>
          </div>
          {record.isError && <Alert>{record.error instanceof ApiError ? record.error.message : 'Could not record the payments.'}</Alert>}
        </div>
      )}

      <Modal open={picking !== null} onClose={() => setPicking(null)} title="Pick the invoice" description={picking ? `${money(picking.amount)} on ${formatDate(picking.date)} · ${picking.description}` : undefined}>
        {picking && (
          <InvoiceSearch
            amount={picking.amount}
            onPick={(invoice) => {
              choose(picking.ref, { invoice, checked: Number(picking.amount) <= Number(invoice.outstanding) })
              setPicking(null)
            }}
          />
        )}
      </Modal>
    </>
  )
}

function CreditCell({ row, choice, done, onToggle }: { row: StatementRow; choice?: Choice; done?: ReconcileResult['results'][number]; onToggle: (checked: boolean) => void }) {
  const canTick = row.status !== 'already_recorded' && !done && fits(row, choice?.invoice ?? null)
  return (
    <label className={clsx('flex items-start gap-3', canTick && 'cursor-pointer')}>
      {done ? (
        <span className={clsx('mt-0.5 grid size-4 shrink-0 place-items-center text-[11px] font-bold', done.status === 'failed' ? 'text-danger' : 'text-green')} aria-label={done.status}>
          {done.status === 'failed' ? '!' : '✓'}
        </span>
      ) : (
        <input type="checkbox" className="mt-0.5 size-4 shrink-0 accent-[var(--color-brand)]" checked={Boolean(choice?.checked) && canTick} disabled={!canTick} onChange={(e) => onToggle(e.target.checked)} aria-label={`Record ${money(row.amount)} from ${formatDate(row.date)}`} />
      )}
      <span>
        <span className="block font-medium tabular-nums">{money(row.amount)}</span>
        <span className="block text-[12px] text-muted">
          {formatDate(row.date)} · {PAYMENT_METHODS[row.method]}
        </span>
      </span>
    </label>
  )
}

function InvoiceCell({ row, choice, locked, onPick }: { row: StatementRow; choice?: Choice; locked: boolean; onPick: () => void }) {
  const invoice = choice?.invoice
  if (locked && !invoice) return <span className="text-muted">—</span>
  return (
    <div className="grid gap-1">
      {invoice && (
        <div>
          <Link to={`/invoices/${invoice.id}`} className="font-medium text-brand hover:underline">
            {invoice.number}
          </Link>
          <p className="text-[12px] text-muted">
            {invoice.customer_name} · {money(invoice.outstanding)} owed
          </p>
          {!fits(row, invoice) && <p className="text-[12px] text-danger">More than this invoice’s balance.</p>}
        </div>
      )}
      {!locked && (
        <button type="button" onClick={onPick} className="w-fit text-[12px] font-medium text-brand hover:underline">
          {invoice ? 'Change' : 'Pick invoice'}
        </button>
      )}
    </div>
  )
}

/** Search the open (confirmed) invoices by number or customer name. Ones that can take the amount come first. */
function InvoiceSearch({ amount, onPick }: { amount: string; onPick: (invoice: Hint) => void }) {
  const [text, setText] = useState('')
  const q = useDebounced(text, 250)
  const results = useQuery({
    queryKey: ['/invoices', 'open', q],
    queryFn: () => api.get<Page<Invoice>>(`/invoices${qs({ status: 'CONFIRMED', q, page_size: 10 })}`),
  })
  const items = [...(results.data?.items ?? [])].sort((a, b) => Number(Number(b.outstanding) >= Number(amount)) - Number(Number(a.outstanding) >= Number(amount)))
  return (
    <div className="grid gap-3">
      <Input autoFocus placeholder="Invoice number or customer…" aria-label="Search open invoices" value={text} onChange={(e) => setText(e.target.value)} />
      <ul className="max-h-80 divide-y divide-line overflow-auto rounded-md border border-line">
        {results.isPending ? (
          <li className="px-3 py-3 text-[13px] text-muted">Searching…</li>
        ) : items.length ? (
          items.map((invoice) => {
            const enough = Number(invoice.outstanding) >= Number(amount)
            return (
              <li key={invoice.id}>
                <button
                  type="button"
                  disabled={!enough}
                  onClick={() => onPick({ id: invoice.id, number: invoice.number ?? `#${invoice.id}`, customer_name: invoice.customer.name, outstanding: invoice.outstanding, due_date: invoice.due_date })}
                  className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left text-[13px] hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <span>
                    <span className="font-medium">{invoice.number}</span>
                    <span className="block text-[12px] text-muted">
                      {invoice.customer.name} · due {formatDate(invoice.due_date)}
                    </span>
                  </span>
                  <span className="text-right tabular-nums">
                    {money(invoice.outstanding)}
                    {!enough && <span className="block text-[11px] text-danger">less than the payment</span>}
                  </span>
                </button>
              </li>
            )
          })
        ) : (
          <li className="px-3 py-3 text-[13px] text-muted">No open invoices match.</li>
        )}
      </ul>
    </div>
  )
}
