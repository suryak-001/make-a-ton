import { useMutation, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { CheckCircle2, CreditCard, Landmark, LockKeyhole, Smartphone, XCircle } from 'lucide-react'
import { type FormEvent, type ReactNode, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '@/lib/api'
import { money } from '@/lib/format'
import type { Invoice } from '@/lib/types'
import { Alert, FormField, Input } from './forms'
import { Button } from './ui'

type Checkout = { order_id: string; amount: string; currency: string; invoice_number: string; merchant: string; customer_name: string; customer_email: string; test_mode: boolean }
type Charged = { order_id: string; payment_id: string; signature: string; method: string; instrument: string }
type Method = 'card' | 'upi' | 'netbanking'
type Charge = { method: Method; card?: { number: string; expiry: string; cvv: string; name?: string }; otp?: string; vpa?: string; bank?: string; bank_outcome?: 'success' | 'failure' }
type Step = 'details' | 'otp' | 'upi-wait' | 'bank' | 'processing' | 'paid' | 'failed'

// The demo gateway only accepts these. Checked here too, so no other card number ever leaves the browser.
const TEST_CARDS = [
  { number: '4111 1111 1111 1111', result: 'Approved' },
  { number: '5555 5555 5555 4444', result: 'Approved (Mastercard)' },
  { number: '4000 0000 0000 0002', result: 'Declined by bank' },
  { number: '4000 0000 0000 9995', result: 'Insufficient funds' },
]
const TEST_OTP = '123456'
const BANKS = [
  { code: 'HDFC', name: 'HDFC Bank' },
  { code: 'ICICI', name: 'ICICI Bank' },
  { code: 'SBI', name: 'State Bank of India' },
  { code: 'AXIS', name: 'Axis Bank' },
  { code: 'KOTAK', name: 'Kotak Mahindra Bank' },
]
const digitsOf = (value: string) => value.replace(/\D/g, '')
const groupCard = (value: string) => digitsOf(value).slice(0, 16).replace(/(\d{4})(?=\d)/g, '$1 ')
const network = (value: string) => (value.startsWith('4') ? 'Visa' : value.startsWith('5') ? 'Mastercard' : '')

/**
 * The online checkout for one invoice, talking to the built-in demo gateway (services/gateway.py): the server
 * opens an order for the balance, the gateway charges a test card, UPI id or bank, and the app checks the
 * gateway's signature before recording the payment. Test mode only; no real money moves.
 */
export function DemoCheckout({ invoice, open, onClose }: { invoice: Invoice; open: boolean; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  const qc = useQueryClient()
  const [method, setMethod] = useState<Method>('card')
  const [step, setStep] = useState<Step>('details')
  const [pending, setPending] = useState<Charge>()
  const [failure, setFailure] = useState<string>()
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [result, setResult] = useState<Charged>()

  const order = useMutation({ mutationFn: () => api.post<Checkout>(`/portal-invoices/${invoice.id}/checkout`) })
  const pay = useMutation({
    mutationFn: async (body: Charge) => {
      const charged = await api.post<Charged>(`/demo-gateway/orders/${order.data!.order_id}/charge`, body)
      await api.post(`/portal-invoices/${invoice.id}/checkout/verify`, { order_id: charged.order_id, payment_id: charged.payment_id, signature: charged.signature })
      return charged
    },
    onSuccess: (charged) => {
      setResult(charged)
      setStep('paid')
      qc.invalidateQueries({ queryKey: ['/portal-invoices'] })
    },
    onError: (e) => {
      if (e instanceof ApiError && e.status === 422 && Object.keys(e.fields).length) {
        setFieldErrors(e.fields)
        setStep('details')
        return
      }
      setFailure(e instanceof ApiError ? e.message : 'The payment could not be completed.')
      setStep('failed')
    },
  })

  const { mutate: openOrder } = order
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (open && !el.open) {
      el.showModal()
      openOrder()
    }
    if (!open && el.open) el.close()
  }, [open, openOrder])

  const submit = (body: Charge) => {
    setFieldErrors({})
    setFailure(undefined)
    setPending(body)
    if (body.method === 'card') setStep('otp')
    else if (body.method === 'upi') setStep('upi-wait')
    else setStep('bank')
  }
  const charge = (body: Charge) => {
    setStep('processing')
    pay.mutate(body)
  }
  const close = () => {
    if (step === 'processing') return
    setStep('details')
    setFailure(undefined)
    setResult(undefined)
    order.reset()
    onClose()
  }

  return (
    <dialog ref={ref} onClose={close} onCancel={(e) => step === 'processing' && e.preventDefault()} aria-label="Pay invoice" className="m-auto w-[calc(100%-2rem)] max-w-[760px] overflow-hidden border border-ink bg-paper p-0 shadow-[7px_7px_0_#171713]">
      {open && (
        <div className="page-enter grid md:grid-cols-[260px_1fr]">
          <aside className="relative flex flex-col gap-5 bg-ink p-5 text-paper">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-yellow">Demo checkout · Test mode</p>
              <p className="mt-3 text-[13px] text-paper/70">Paying</p>
              <p className="text-[16px] font-medium">{order.data?.merchant ?? 'Brightloop Software'}</p>
            </div>
            <div>
              <p className="text-[13px] text-paper/70">Invoice {invoice.number}</p>
              <p className="mt-1 text-[30px] font-medium tabular-nums tracking-[-0.03em]">{money(order.data?.amount ?? invoice.outstanding)}</p>
              {order.data && <p className="mt-1 text-[12px] text-paper/60">{order.data.customer_email}</p>}
            </div>
            <p className="mt-auto flex items-center gap-2 text-[11px] text-paper/60">
              <LockKeyhole aria-hidden className="size-3.5" />
              No real money moves. Only the test details below are accepted.
            </p>
          </aside>

          <section className="relative min-h-[420px] p-5">
            <button type="button" onClick={close} disabled={step === 'processing'} aria-label="Close checkout" className="absolute right-4 top-4 grid size-8 place-items-center border border-ink bg-paper text-lg hover:bg-yellow disabled:opacity-30">
              ×
            </button>
            {order.isError ? (
              <Result tone="failed" title="Couldn’t open checkout" text={order.error instanceof ApiError ? order.error.message : 'Try again in a moment.'} action={<Button onClick={close}>Close</Button>} />
            ) : !order.data ? (
              <Waiting title="Opening checkout…" />
            ) : step === 'details' ? (
              <Details method={method} onMethod={(m) => (setMethod(m), setFieldErrors({}))} errors={fieldErrors} onSubmit={submit} amount={order.data!.amount} />
            ) : step === 'otp' ? (
              <Otp card={pending!.card!} amount={order.data!.amount} onBack={() => setStep('details')} onSubmit={(otp) => charge({ ...pending!, otp })} />
            ) : step === 'upi-wait' ? (
              <UpiWait vpa={pending!.vpa!} onDone={() => charge(pending!)} onBack={() => setStep('details')} />
            ) : step === 'bank' ? (
              <BankPage bank={BANKS.find((b) => b.code === pending!.bank)!.name} amount={order.data!.amount} onOutcome={(bank_outcome) => charge({ ...pending!, bank_outcome })} />
            ) : step === 'processing' ? (
              <Waiting title="Processing payment…" text="Don’t close this window." />
            ) : step === 'paid' ? (
              <Result
                tone="paid"
                title="Payment successful"
                text={`${money(order.data!.amount)} paid with ${result!.instrument}. Invoice ${invoice.number} is now paid.`}
                detail={`Payment id ${result!.payment_id}`}
                action={<Button onClick={close}>Done</Button>}
              />
            ) : (
              <Result tone="failed" title="Payment failed" text={failure ?? 'The payment did not go through.'} detail="Nothing was charged. You can try again." action={<Button onClick={() => setStep('details')}>Try again</Button>} />
            )}
          </section>
        </div>
      )}
    </dialog>
  )
}

const METHODS: { id: Method; label: string; Icon: typeof CreditCard }[] = [
  { id: 'card', label: 'Card', Icon: CreditCard },
  { id: 'upi', label: 'UPI', Icon: Smartphone },
  { id: 'netbanking', label: 'Netbanking', Icon: Landmark },
]

function Details({ method, onMethod, errors, onSubmit, amount }: { method: Method; onMethod: (m: Method) => void; errors: Record<string, string>; onSubmit: (c: Charge) => void; amount: string }) {
  return (
    <div className="grid gap-4 pr-8">
      <h2 className="text-[17px] font-medium tracking-[-0.02em]">How would you like to pay?</h2>
      <div role="tablist" aria-label="Payment method" className="grid grid-cols-3 gap-2">
        {METHODS.map(({ id, label, Icon }) => (
          <button key={id} type="button" role="tab" aria-selected={method === id} onClick={() => onMethod(id)} className={clsx('flex items-center justify-center gap-2 rounded-md border px-2 py-2.5 text-[13px] font-medium transition-colors', method === id ? 'border-brand bg-brand/10 text-brand' : 'border-line hover:bg-surface')}>
            <Icon aria-hidden className="size-4" />
            {label}
          </button>
        ))}
      </div>
      {method === 'card' ? <CardForm errors={errors} onSubmit={onSubmit} amount={amount} /> : method === 'upi' ? <UpiForm errors={errors} onSubmit={onSubmit} amount={amount} /> : <BankForm errors={errors} onSubmit={onSubmit} amount={amount} />}
    </div>
  )
}

function TestHint({ children }: { children: ReactNode }) {
  return <div className="rounded-md border border-dashed border-yellow bg-yellow/10 p-3 text-[12px]">{children}</div>
}

function CardForm({ errors, onSubmit, amount }: { errors: Record<string, string>; onSubmit: (c: Charge) => void; amount: string }) {
  const [number, setNumber] = useState('')
  const [expiry, setExpiry] = useState('')
  const [cvv, setCvv] = useState('')
  const [name, setName] = useState('')
  const [local, setLocal] = useState<string>()

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!TEST_CARDS.some((c) => digitsOf(c.number) === digitsOf(number))) {
      setLocal('This is a demo checkout. Use one of the test cards below.')
      return
    }
    setLocal(undefined)
    onSubmit({ method: 'card', card: { number: digitsOf(number), expiry, cvv, name: name || undefined } })
  }
  const fillCard = (card: string) => {
    setNumber(card)
    setExpiry('12/30')
    setCvv('123')
    setLocal(undefined)
  }

  return (
    <form onSubmit={submit} className="grid gap-3" noValidate>
      <FormField label="Card number" htmlFor="card-number" error={local ?? errors['card.number']}>
        <div className="relative">
          <Input id="card-number" inputMode="numeric" autoComplete="off" placeholder="1234 5678 9012 3456" value={number} onChange={(e) => setNumber(groupCard(e.target.value))} error={Boolean(local ?? errors['card.number'])} className="pr-24 tabular-nums" />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] font-medium uppercase tracking-[0.08em] text-muted">{network(digitsOf(number))}</span>
        </div>
      </FormField>
      <div className="grid grid-cols-2 gap-3">
        <FormField label="Expiry (MM/YY)" htmlFor="card-expiry" error={errors['card.expiry']}>
          <Input id="card-expiry" inputMode="numeric" autoComplete="off" placeholder="MM/YY" value={expiry} onChange={(e) => setExpiry(digitsOf(e.target.value).slice(0, 4).replace(/^(\d{2})(\d)/, '$1/$2'))} error={Boolean(errors['card.expiry'])} />
        </FormField>
        <FormField label="CVV" htmlFor="card-cvv" error={errors['card.cvv']}>
          <Input id="card-cvv" inputMode="numeric" autoComplete="off" type="password" placeholder="•••" value={cvv} onChange={(e) => setCvv(digitsOf(e.target.value).slice(0, 4))} error={Boolean(errors['card.cvv'])} />
        </FormField>
      </div>
      <FormField label="Name on card (optional)" htmlFor="card-name">
        <Input id="card-name" autoComplete="off" value={name} onChange={(e) => setName(e.target.value)} />
      </FormField>
      <TestHint>
        <p className="mb-2 font-medium">Test cards (any future expiry, any CVV, OTP {TEST_OTP})</p>
        <div className="grid gap-1">
          {TEST_CARDS.map((card) => (
            <button key={card.number} type="button" onClick={() => fillCard(card.number)} className="flex justify-between gap-3 text-left hover:underline">
              <span className="tabular-nums">{card.number}</span>
              <span className="text-muted">{card.result}</span>
            </button>
          ))}
        </div>
      </TestHint>
      <Button type="submit">Pay {money(amount)}</Button>
    </form>
  )
}

function UpiForm({ errors, onSubmit, amount }: { errors: Record<string, string>; onSubmit: (c: Charge) => void; amount: string }) {
  const [vpa, setVpa] = useState('')
  return (
    <form onSubmit={(e) => (e.preventDefault(), onSubmit({ method: 'upi', vpa: vpa.trim() }))} className="grid gap-3" noValidate>
      <FormField label="UPI id" htmlFor="upi-id" error={errors.vpa}>
        <Input id="upi-id" autoComplete="off" placeholder="name@bank" value={vpa} onChange={(e) => setVpa(e.target.value)} error={Boolean(errors.vpa)} />
      </FormField>
      <TestHint>
        <p className="mb-2 font-medium">Test UPI ids</p>
        <div className="flex flex-wrap gap-2">
          {[['success@demo', 'Approves'], ['failure@demo', 'Declines']].map(([id, what]) => (
            <button key={id} type="button" onClick={() => setVpa(id)} className="rounded-md border border-line bg-paper px-2 py-1 hover:border-ink/30">
              {id} <span className="text-muted">· {what}</span>
            </button>
          ))}
        </div>
      </TestHint>
      <Button type="submit">Pay {money(amount)}</Button>
    </form>
  )
}

function BankForm({ errors, onSubmit, amount }: { errors: Record<string, string>; onSubmit: (c: Charge) => void; amount: string }) {
  const [bank, setBank] = useState('')
  return (
    <form onSubmit={(e) => (e.preventDefault(), bank && onSubmit({ method: 'netbanking', bank }))} className="grid gap-3">
      <fieldset className="grid gap-2">
        <legend className="mb-1 text-[12px] font-medium uppercase tracking-[0.08em] text-muted">Your bank</legend>
        {BANKS.map((b) => (
          <label key={b.code} className={clsx('flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 text-[13px]', bank === b.code ? 'border-brand bg-brand/5' : 'border-line hover:bg-surface')}>
            <input type="radio" name="bank" value={b.code} checked={bank === b.code} onChange={() => setBank(b.code)} className="accent-[var(--color-brand)]" />
            {b.name}
          </label>
        ))}
      </fieldset>
      {errors.bank && <Alert>{errors.bank}</Alert>}
      <Button type="submit" disabled={!bank}>
        Continue to bank · {money(amount)}
      </Button>
    </form>
  )
}

function Otp({ card, amount, onBack, onSubmit }: { card: NonNullable<Charge['card']>; amount: string; onBack: () => void; onSubmit: (otp: string) => void }) {
  const [otp, setOtp] = useState('')
  return (
    <form onSubmit={(e) => (e.preventDefault(), onSubmit(otp))} className="grid gap-4 pr-8">
      <div>
        <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-muted">Secure verification · Demo bank</p>
        <h2 className="mt-1 text-[17px] font-medium tracking-[-0.02em]">Enter the OTP</h2>
        <p className="mt-1 text-[13px] text-muted">
          Authorise {money(amount)} on {network(card.number) || 'card'} •••• {card.number.slice(-4)}. The OTP was sent to the phone registered with the card.
        </p>
      </div>
      <Input autoFocus inputMode="numeric" autoComplete="one-time-code" aria-label="One-time password" placeholder="6-digit OTP" value={otp} onChange={(e) => setOtp(digitsOf(e.target.value).slice(0, 6))} className="text-center text-[18px] tracking-[0.4em]" />
      <TestHint>
        Test OTP: <button type="button" className="font-medium underline" onClick={() => setOtp(TEST_OTP)}>{TEST_OTP}</button>. Any other OTP is declined.
      </TestHint>
      <div className="grid grid-cols-2 gap-2">
        <Button type="button" variant="outline" onClick={onBack}>Back</Button>
        <Button type="submit" disabled={otp.length < 6}>Authorise</Button>
      </div>
    </form>
  )
}

function UpiWait({ vpa, onDone, onBack }: { vpa: string; onDone: () => void; onBack: () => void }) {
  const [seconds, setSeconds] = useState(3)
  const done = useRef(onDone) // the latest callback, called once: a re-render must never charge twice
  useEffect(() => {
    done.current = onDone
  }, [onDone])
  useEffect(() => {
    if (seconds === 0) {
      done.current()
      return
    }
    const t = setTimeout(() => setSeconds((s) => s - 1), 1000)
    return () => clearTimeout(t)
  }, [seconds])
  return (
    <div className="grid h-full place-content-center gap-3 pr-8 text-center">
      <Smartphone aria-hidden className="mx-auto size-10 animate-pulse text-brand" />
      <h2 className="text-[17px] font-medium">Approve the request in your UPI app</h2>
      <p className="text-[13px] text-muted">A collect request was sent to <span className="font-medium text-ink">{vpa}</span>. In this demo it answers by itself in {seconds}s.</p>
      <Button variant="ghost" onClick={onBack}>Cancel</Button>
    </div>
  )
}

function BankPage({ bank, amount, onOutcome }: { bank: string; amount: string; onOutcome: (o: 'success' | 'failure') => void }) {
  return (
    <div className="grid gap-4 pr-8">
      <div className="border-b border-line pb-3">
        <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-muted">Simulated bank page</p>
        <h2 className="mt-1 text-[17px] font-medium">{bank} · Netbanking</h2>
      </div>
      <p className="text-[13px]">Confirm the transfer of <span className="font-medium tabular-nums">{money(amount)}</span> to Brightloop Software.</p>
      <TestHint>This stands in for the bank’s own login page. Choose what the bank reports back.</TestHint>
      <div className="grid grid-cols-2 gap-2">
        <Button variant="outline" className="border-danger/40 text-danger" onClick={() => onOutcome('failure')}>Simulate failure</Button>
        <Button onClick={() => onOutcome('success')}>Simulate success</Button>
      </div>
    </div>
  )
}

function Waiting({ title, text }: { title: string; text?: string }) {
  return (
    <div className="grid h-full min-h-[380px] place-content-center gap-3 text-center" role="status">
      <span className="mx-auto size-9 animate-spin rounded-full border-2 border-line border-t-brand" aria-hidden />
      <p className="font-medium">{title}</p>
      {text && <p className="text-[13px] text-muted">{text}</p>}
    </div>
  )
}

function Result({ tone, title, text, detail, action }: { tone: 'paid' | 'failed'; title: string; text: string; detail?: string; action: ReactNode }) {
  const Icon = tone === 'paid' ? CheckCircle2 : XCircle
  return (
    <div className="grid h-full min-h-[380px] place-content-center gap-3 px-4 text-center" role={tone === 'failed' ? 'alert' : 'status'}>
      <Icon aria-hidden className={clsx('mx-auto size-12', tone === 'paid' ? 'text-green' : 'text-danger')} />
      <h2 className="text-[18px] font-medium tracking-[-0.02em]">{title}</h2>
      <p className="mx-auto max-w-sm text-[13px] text-muted">{text}</p>
      {detail && <p className="text-[11px] text-muted">{detail}</p>}
      <div className="mt-2">{action}</div>
    </div>
  )
}
