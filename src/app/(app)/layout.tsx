import { AppShell } from "@/components/app-shell";
import { requireRole } from "@/lib/auth/session";
import { APP_NAV } from "@/lib/nav";

// Internal back office (admin + staff). Pages still call requireRole() themselves —
// layouts don't re-render on client navigation, so they are not an auth boundary.
export default async function AppLayout({ children }: LayoutProps<"/">) {
  const session = await requireRole("ADMIN", "STAFF");
  return (
    <AppShell session={session} nav={APP_NAV}>
      {children}
    </AppShell>
  );
}
