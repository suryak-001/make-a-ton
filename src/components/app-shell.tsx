import { logout } from "@/app/(auth)/actions";
import { Button } from "@/components/ui/button";
import type { Session } from "@/lib/auth/session";
import type { NavItem } from "@/lib/nav";
import { SidebarNav } from "./sidebar-nav";

const ROLE_LABEL = { ADMIN: "Admin", STAFF: "Staff", CUSTOMER: "Customer" } as const;

export function AppShell({ session, nav, children }: { session: Session; nav: NavItem[]; children: React.ReactNode }) {
  const items = nav.filter((i) => i.roles.includes(session.role)).map(({ href, label }) => ({ href, label }));

  return (
    <div className="flex min-h-screen flex-1">
      <aside className="flex w-60 shrink-0 flex-col border-r bg-sidebar p-3">
        <p className="px-3 py-2 text-base font-semibold tracking-tight">Brightloop</p>
        <div className="mt-2 flex-1">
          <SidebarNav items={items} />
        </div>
        <div className="border-t pt-3">
          <p className="px-3 text-sm font-medium">{session.name}</p>
          <p className="px-3 text-xs text-muted-foreground">{ROLE_LABEL[session.role]}</p>
          <form action={logout} className="mt-2 px-1">
            <Button type="submit" variant="ghost" size="sm" className="w-full justify-start">
              Sign out
            </Button>
          </form>
        </div>
      </aside>
      <main className="flex-1 overflow-x-auto p-8">{children}</main>
    </div>
  );
}
