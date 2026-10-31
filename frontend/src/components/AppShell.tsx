import clsx from 'clsx'
import { useEffect, useMemo, useState } from 'react'
import {
  ArrowLeft, BadgePercent, CalendarRange, ChartNoAxesCombined, ChevronRight, FileStack, House, Landmark,
  LayoutDashboard, LogOut, Menu, Package, Percent, ReceiptText, Repeat2, UserCog,
  Users, WalletCards, X, type LucideIcon,
} from 'lucide-react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router'
import { useAuth } from '@/auth/context'
import type { NavItem } from '@/nav'
import { BrandMark } from './BrandMark'
import { CommandPalette } from './CommandPalette'

const ROLE_LABEL = { ADMIN: 'Admin workspace', STAFF: 'Staff workspace', CUSTOMER: 'Customer portal' } as const

const groupFor = (href: string) => {
  if (href.includes('/dashboard') || href.includes('/reports') || href === '/portal/home') return 'Overview'
  if (href.includes('/subscriptions') || href.includes('/customers') || href.includes('/quotation')) return 'Sales'
  if (href.includes('/products') || href.includes('/plans')) return 'Catalog'
  if (href.includes('/invoices') || href.includes('/payments') || href.includes('/reconciliation')) return 'Billing'
  return 'Configuration'
}

const iconFor = (href: string): LucideIcon => {
  if (href.includes('/dashboard')) return LayoutDashboard
  if (href.includes('/subscriptions')) return Repeat2
  if (href.includes('/customers')) return Users
  if (href.includes('/invoices')) return ReceiptText
  if (href.includes('/payments')) return WalletCards
  if (href.includes('/reconciliation')) return Landmark
  if (href.includes('/quotation')) return FileStack
  if (href.includes('/products')) return Package
  if (href.includes('/plans')) return CalendarRange
  if (href.includes('/taxes')) return Percent
  if (href.includes('/discounts')) return BadgePercent
  if (href.includes('/reports')) return ChartNoAxesCombined
  return UserCog
}

function NavItemLink({ item, onChoose }: { item: NavItem; onChoose?: () => void }) {
  const Icon = iconFor(item.href)
  return <NavLink to={item.href} onClick={onChoose} className={({ isActive }) => clsx(
    'group relative flex h-10 items-center gap-3 rounded-md border px-3 text-[13px] font-medium transition-colors',
    isActive ? 'border-brand/20 bg-brand/8 text-brand' : 'border-transparent text-muted hover:bg-ink/5 hover:text-ink',
  )}>
    {({ isActive }) => <>
      {isActive && <span className="absolute -left-[1px] h-5 w-0.5 rounded-r bg-brand" />}
      <Icon className="size-4 shrink-0" strokeWidth={1.8} />
      <span className="truncate">{item.label}</span>
    </>}
  </NavLink>
}

function Navigation({ items, onChoose }: { items: NavItem[]; onChoose?: () => void }) {
  const groups = Array.from(new Set(items.map((item) => groupFor(item.href))))
  return <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-4" aria-label="Primary navigation">
    {groups.map((group) => <section key={group} className="mb-5">
      <p className="mb-1.5 px-3 text-[10px] font-medium uppercase tracking-[0.16em] text-muted">{group}</p>
      <div className="grid gap-0.5">{items.filter((item) => groupFor(item.href) === group).map((item) => <NavItemLink key={item.href} item={item} onChoose={onChoose} />)}</div>
    </section>)}
  </nav>
}

function AccountFooter({ name, email, role, profile, onSignOut, onChoose }: { name: string; email: string; role: keyof typeof ROLE_LABEL; profile: string; onSignOut: () => void; onChoose?: () => void }) {
  return <div className="flex items-center gap-3 border-t border-line p-3">
    <NavLink to={profile} onClick={onChoose} title="Your profile" className="flex min-w-0 flex-1 items-center gap-3 rounded-md p-1 hover:bg-surface">
      <span className="grid size-9 shrink-0 place-items-center rounded-full bg-brand text-[11px] font-medium text-white">{name.slice(0, 2).toUpperCase()}</span>
      <div className="min-w-0 flex-1"><p className="truncate text-[12px] font-medium">{name}</p><p className="truncate text-[10px] text-muted">{email || ROLE_LABEL[role]}</p></div>
    </NavLink>
    <button type="button" onClick={onSignOut} aria-label="Sign out" title="Sign out" className="grid size-9 shrink-0 place-items-center rounded-md border border-transparent text-muted transition hover:border-line hover:bg-surface hover:text-danger"><LogOut className="size-4" /></button>
  </div>
}

export function AppShell({ nav }: { nav: NavItem[] }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const items = useMemo(() => user ? nav.filter((item) => item.roles.includes(user.role)) : [], [nav, user])
  const current = [...items].sort((a, b) => b.href.length - a.href.length).find((item) => location.pathname === item.href || location.pathname.startsWith(`${item.href}/`)) ?? items[0]
  const group = current ? groupFor(current.href) : 'Workspace'

  useEffect(() => {
    if (!drawerOpen) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') setDrawerOpen(false) }
    window.addEventListener('keydown', close)
    return () => { document.body.style.overflow = previous; window.removeEventListener('keydown', close) }
  }, [drawerOpen])

  if (!user) return null
  const signOut = async () => { await logout(); navigate('/login', { replace: true }) }
  const email = 'email' in user && typeof user.email === 'string' ? user.email : ''
  const profile = user.role === 'CUSTOMER' ? '/portal/profile' : '/profile'
  const home = items.find((item) => item.href.includes('/dashboard'))?.href ?? items[0]?.href ?? '/'

  return <div className="min-h-screen">
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-line bg-paper/95 backdrop-blur-xl xl:flex">
      <div className="border-b border-line px-5 py-4"><BrandMark /></div>
      <Navigation items={items} />
      <AccountFooter name={user.name} email={email} role={user.role} profile={profile} onSignOut={signOut} />
    </aside>

    {drawerOpen && <button type="button" className="fixed inset-0 z-40 bg-ink/45 backdrop-blur-[2px] xl:hidden" onClick={() => setDrawerOpen(false)} aria-label="Close navigation" />}
    <aside className={clsx('fixed inset-y-0 left-0 z-50 flex w-[min(288px,88vw)] flex-col border-r border-line bg-paper shadow-[14px_0_40px_rgb(23_23_19_/_0.16)] transition-transform duration-200 xl:hidden', drawerOpen ? 'translate-x-0' : '-translate-x-full')} aria-hidden={!drawerOpen}>
      <div className="flex h-[60px] items-center justify-between border-b border-line px-4"><BrandMark /><button type="button" onClick={() => setDrawerOpen(false)} aria-label="Close navigation" className="grid size-9 place-items-center rounded-md border border-line text-muted hover:bg-surface hover:text-ink"><X className="size-4" /></button></div>
      <Navigation items={items} onChoose={() => setDrawerOpen(false)} />
      <AccountFooter name={user.name} email={email} role={user.role} profile={profile} onSignOut={signOut} onChoose={() => setDrawerOpen(false)} />
    </aside>

    <div className="min-w-0 xl:pl-64">
      <header className="sticky top-0 z-30 flex h-[60px] items-center gap-3 border-b border-line bg-paper/92 px-4 backdrop-blur-xl sm:px-6 xl:px-8">
        <button type="button" onClick={() => setDrawerOpen(true)} className="grid size-9 shrink-0 place-items-center rounded-md border border-line text-muted hover:bg-surface hover:text-ink xl:hidden" aria-label="Open navigation"><Menu className="size-[18px]" /></button>
        <div className="hidden sm:block xl:hidden"><BrandMark compact /></div>
        <div className="min-w-0 flex-1 sm:border-l sm:border-line sm:pl-3 xl:border-0 xl:pl-0"><p className="truncate text-[13px] font-medium">{current?.label ?? 'Workspace'}</p><p className="hidden truncate text-[10px] text-muted sm:block">{group} · {ROLE_LABEL[user.role]}</p></div>
        <CommandPalette items={items} />
        <NavLink to={profile} aria-label="Your profile" title="Your profile" className="grid size-8 shrink-0 place-items-center rounded-full bg-brand text-[10px] font-medium text-white xl:hidden">{user.name.slice(0, 2).toUpperCase()}</NavLink>
      </header>

      <main className="rand-grid min-h-[calc(100vh-60px)] px-4 py-4 sm:px-6 sm:py-5 xl:px-8 xl:py-6">
        <div className="relative mx-auto max-w-[1440px]">
          <nav aria-label="Breadcrumb" className="mb-4 flex min-w-0 items-center gap-1.5 overflow-x-auto whitespace-nowrap text-[11px] text-muted">
            {location.key !== 'default' && <button type="button" onClick={() => navigate(-1)} aria-label="Go back" title="Go back" className="mr-1 grid size-7 shrink-0 place-items-center rounded-md border border-line bg-paper text-ink transition hover:bg-surface"><ArrowLeft className="size-4" /></button>}
            <NavLink to={home} className="inline-flex items-center gap-1 hover:text-ink"><House className="size-3.5" /> Home</NavLink><ChevronRight className="size-3 shrink-0 opacity-50" /><span>{group}</span><ChevronRight className="size-3 shrink-0 opacity-50" /><span className="font-medium text-ink">{current?.label}</span>
          </nav>
          <div className="page-enter"><Outlet /></div>
        </div>
      </main>
    </div>
  </div>
}
