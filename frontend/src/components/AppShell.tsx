import clsx from 'clsx'
import { NavLink, Outlet, useNavigate } from 'react-router'
import { useAuth } from '@/auth/context'
import type { NavItem } from '@/nav'
import { Button } from './ui'

const ROLE_LABEL = { ADMIN: 'Admin', STAFF: 'Staff', CUSTOMER: 'Customer' } as const

export function AppShell({ nav }: { nav: NavItem[] }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  if (!user) return null
  const items = nav.filter((i) => i.roles.includes(user.role))

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-r border-line bg-surface p-3">
        <p className="px-3 py-2 text-base font-semibold tracking-tight">Brightloop</p>
        <nav className="mt-2 grid flex-1 content-start gap-0.5">
          {items.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) =>
                clsx('rounded-md px-3 py-1.5 text-sm hover:bg-black/5', isActive && 'bg-black/5 font-medium')
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-line pt-3">
          <p className="px-3 text-sm font-medium">{user.name}</p>
          <p className="px-3 text-xs text-muted">{ROLE_LABEL[user.role]}</p>
          <Button
            variant="ghost"
            className="mt-2 w-full justify-start"
            onClick={async () => {
              await logout()
              navigate('/login', { replace: true })
            }}
          >
            Sign out
          </Button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-8">
        <Outlet />
      </main>
    </div>
  )
}
