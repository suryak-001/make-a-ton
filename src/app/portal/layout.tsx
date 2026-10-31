// Owner: A (shell). B owns /portal/invoices.
import { AppShell } from "@/components/app-shell";
import { requireRole } from "@/lib/auth/session";
import { PORTAL_NAV } from "@/lib/nav";

export default async function PortalLayout({ children }: LayoutProps<"/portal">) {
  const session = await requireRole("CUSTOMER");
  return (
    <AppShell session={session} nav={PORTAL_NAV}>
      {children}
    </AppShell>
  );
}
