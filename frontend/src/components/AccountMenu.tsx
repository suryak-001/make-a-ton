import { LogOut, User as UserIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useAuth } from '@/auth/context'
import { useSignOut } from '@/auth/useSignOut'

const ROLE = { ADMIN: 'Admin', STAFF: 'Staff', CUSTOMER: 'Customer' } as const

/** The avatar in the top bar. Hover or click it for who you are, your Profile and Sign out. */
export function AccountMenu({ profile }: { profile: string }) {
  const { user } = useAuth()
  const signOut = useSignOut()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false) }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey) }
  }, [open])

  if (!user) return null
  return (
    <div ref={box} className="relative" onMouseEnter={() => window.matchMedia('(hover: hover)').matches && setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" aria-label="Account menu" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen((v) => (window.matchMedia('(hover: hover)').matches ? true : !v))} className="grid size-9 place-items-center rounded-full bg-brand text-[11px] font-medium text-white outline-none ring-offset-2 transition hover:opacity-90 focus-visible:ring-2 focus-visible:ring-brand">
        {user.name.slice(0, 2).toUpperCase()}
      </button>
      {open && (
        <div role="menu" className="sheet-enter absolute right-0 top-full z-50 w-64 pt-2">
          <div className="overflow-hidden rounded-md border border-ink bg-paper shadow-[4px_4px_0_#171713]">
            <div className="border-b border-line px-4 py-3">
              <p className="truncate text-[13px] font-medium">{user.name}</p>
              <p className="truncate text-[11px] text-muted">{user.email}</p>
              <p className="mt-1 text-[10px] font-medium uppercase tracking-[0.12em] text-brand">{ROLE[user.role]}</p>
            </div>
            <Link to={profile} role="menuitem" onClick={() => setOpen(false)} className="flex items-center gap-2.5 px-4 py-2.5 text-[13px] hover:bg-surface"><UserIcon className="size-4" strokeWidth={1.8} /> Profile</Link>
            <button type="button" role="menuitem" onClick={signOut} className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-[13px] text-danger hover:bg-surface"><LogOut className="size-4" strokeWidth={1.8} /> Sign out</button>
          </div>
        </div>
      )}
    </div>
  )
}
