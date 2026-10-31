import { CalendarClock, CreditCard, FileText, PauseCircle, ShieldCheck, XCircle } from 'lucide-react'
import { Link } from 'react-router'
import { BrandMark } from '@/components/BrandMark'
import { buttonClass } from '@/components/button-class'

const FEATURES = [
  { icon: PauseCircle, title: 'Pause any time', text: 'Going away for a month? Pause a subscription in one click and billing stops. Resume when you are back.' },
  { icon: XCircle, title: 'Cancel without an email', text: 'End a subscription yourself, whenever your plan allows it. No forms, no waiting for a reply.' },
  { icon: CreditCard, title: 'Pay online in seconds', text: 'Pay any open invoice by card, UPI or netbanking. The invoice turns Paid straight away.' },
  { icon: FileText, title: 'Every invoice, one click', text: 'Download a clean PDF of any invoice, with your details, taxes and what you have paid.' },
  { icon: CalendarClock, title: 'Know what is coming', text: 'See your next bill, your renewal date and anything overdue the moment you sign in.' },
  { icon: ShieldCheck, title: 'Only your own data', text: 'You see your subscriptions and invoices, and nobody else’s. Your password never leaves a secure sign-in.' },
]

const STEPS = [
  { n: '01', title: 'Create your account', text: 'Use the email your company billed. Your subscriptions appear right away.' },
  { n: '02', title: 'Look after your plans', text: 'Pause, renew, switch add-ons on and off, or cancel. All from one page.' },
  { n: '03', title: 'Pay and keep records', text: 'Pay online and download every invoice whenever you need it.' },
]

const FAQ = [
  { q: 'Can I pause my subscription?', a: 'Yes, if your plan allows pausing. Open Home or My subscriptions and press Pause. Billing stops until you resume, and you can undo it straight away.' },
  { q: 'How do I cancel?', a: 'Open the subscription and press Cancel subscription. We ask for an optional reason and confirm before anything happens. Some contract plans can only be changed by our team, and the page tells you so.' },
  { q: 'How do I pay an invoice?', a: 'Open My invoices and press Pay on any open invoice. Cards, UPI and netbanking are supported.' },
  { q: 'I forgot my password.', a: 'Choose Forgot password on the sign-in page. We email a link that works for one hour.' },
  { q: 'I do not see my subscription.', a: 'Sign up with the same email address your company billed. If it still does not show, contact our team and we will link it for you.' },
]

/** What a visitor sees at "/": what the customer portal does, with Pause and Cancel front and centre. */
export default function Landing() {
  return (
    <div className="min-h-screen bg-surface text-ink">
      <header className="sticky top-0 z-30 border-b border-line bg-paper/90 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5">
          <BrandMark />
          <nav className="flex items-center gap-2" aria-label="Account">
            <a href="#faq" className="hidden px-3 text-[13px] text-muted hover:text-ink sm:inline">Questions</a>
            <Link to="/login" className={buttonClass('outline')}>Sign in</Link>
            <Link to="/signup" className={buttonClass('primary', 'hidden sm:inline-flex')}>Create account</Link>
          </nav>
        </div>
      </header>

      <section className="relative overflow-hidden border-b border-ink bg-brand text-paper">
        <div className="absolute -right-16 -top-20 size-44 rounded-full border-[28px] border-yellow md:-right-24 md:-top-24 md:size-80 md:border-[48px]" aria-hidden />
        <div className="absolute bottom-10 right-1/3 hidden size-24 rotate-12 bg-danger md:block" aria-hidden />
        <div className="relative z-10 mx-auto grid max-w-6xl gap-10 px-5 py-16 md:grid-cols-[1.1fr_.9fr] md:py-24">
          <div>
            <p className="text-[10px] font-medium uppercase tracking-[0.25em] text-paper/70">Customer portal</p>
            <h1 className="mt-4 text-[clamp(40px,6vw,76px)] font-medium leading-[0.92] tracking-[-0.06em]">Your subscriptions,<br /><span className="text-yellow">in your hands.</span></h1>
            <p className="mt-6 max-w-lg text-[16px] leading-7 text-paper/80">See what you pay, pay invoices online, and pause or cancel a subscription yourself, any time your plan allows. No emails, no waiting.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/signup" className={buttonClass('primary', '!h-11 !border-yellow !bg-yellow px-5 !text-ink hover:!bg-yellow/90')}>Create your account</Link>
              <Link to="/login" className={buttonClass('outline', '!h-11 !border-paper/40 !bg-transparent px-5 !text-paper hover:!bg-paper/10')}>Sign in</Link>
            </div>
            <p className="mt-4 text-[12px] text-paper/60">Already a customer? Sign in with the email we billed.</p>
          </div>

          <div className="self-center" aria-label="A preview of the portal">
            <div className="border border-ink bg-paper p-5 text-ink shadow-[8px_8px_0_#171713]">
              <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted">Your subscriptions</p>
              <div className="mt-3 grid gap-3">
                <div className="flex flex-wrap items-center justify-between gap-3 border border-line p-3">
                  <div><p className="text-[13px] font-medium">SUB-00003 · Monthly</p><p className="text-[11px] text-muted">₹3,304.00 per month · next bill 5 Nov</p></div>
                  <div className="flex items-center gap-2"><span className="border border-green/30 bg-green/10 px-2 py-0.5 text-[10px] font-medium uppercase text-green">Active</span><span className={buttonClass('primary', '!h-8 pointer-events-none')}>Pause</span><span className={buttonClass('outline', '!h-8 pointer-events-none')}>Cancel subscription</span></div>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-3 border border-line p-3">
                  <div><p className="text-[13px] font-medium">INV-2026-00001</p><p className="text-[11px] text-danger">₹4,720.00 overdue</p></div>
                  <span className={buttonClass('primary', '!h-8 pointer-events-none')}>Pay now</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-16" aria-labelledby="what">
        <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-brand">What you can do</p>
        <h2 id="what" className="mt-2 max-w-xl text-[30px] font-medium leading-tight tracking-[-0.04em]">Everything about your plans, without asking anyone.</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="border border-line bg-paper p-5">
              <span className="grid size-10 place-items-center rounded-md bg-brand/10 text-brand"><Icon className="size-5" strokeWidth={1.8} /></span>
              <h3 className="mt-4 text-[15px] font-medium">{title}</h3>
              <p className="mt-1.5 text-[13px] leading-6 text-muted">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-y border-line bg-paper">
        <div className="mx-auto max-w-6xl px-5 py-16">
          <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-brand">How it works</p>
          <div className="mt-6 grid gap-8 md:grid-cols-3">
            {STEPS.map((step) => (
              <div key={step.n}>
                <p className="text-[34px] font-medium leading-none tracking-[-0.05em] text-yellow">{step.n}</p>
                <h3 className="mt-3 text-[16px] font-medium">{step.title}</h3>
                <p className="mt-1.5 text-[13px] leading-6 text-muted">{step.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="faq" className="mx-auto max-w-3xl px-5 py-16" aria-labelledby="faq-title">
        <p className="text-[10px] font-medium uppercase tracking-[0.22em] text-brand">Questions</p>
        <h2 id="faq-title" className="mt-2 text-[30px] font-medium tracking-[-0.04em]">Good to know</h2>
        <div className="mt-6 divide-y divide-line border-y border-line">
          {FAQ.map((item) => (
            <details key={item.q} className="group py-4">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-[14px] font-medium">{item.q}<span className="text-muted transition-transform group-open:rotate-45" aria-hidden>+</span></summary>
              <p className="mt-2 max-w-2xl text-[13px] leading-6 text-muted">{item.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="border-t border-ink bg-ink text-paper">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-5 px-5 py-12">
          <div><h2 className="text-[24px] font-medium tracking-[-0.04em]">Ready to take a look?</h2><p className="mt-1 text-[13px] text-paper/70">Create your account in under a minute.</p></div>
          <div className="flex gap-3"><Link to="/signup" className={buttonClass('primary', '!border-yellow !bg-yellow !text-ink hover:!bg-yellow/90')}>Create account</Link><Link to="/login" className={buttonClass('outline', '!border-paper/40 !bg-transparent !text-paper hover:!bg-paper/10')}>Sign in</Link></div>
        </div>
      </section>

      <footer className="bg-ink px-5 pb-8 text-center text-[10px] uppercase tracking-[0.18em] text-paper/50">Brightloop Software Pvt Ltd · Kochi</footer>
    </div>
  )
}
