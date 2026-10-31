// Owner: B — replace this placeholder with the real page.
import { PlaceholderPage } from "@/components/placeholder-page";
import { requireRole } from "@/lib/auth/session";

export default async function Page() {
  await requireRole("CUSTOMER");
  return <PlaceholderPage href="/portal/invoices" />;
}
