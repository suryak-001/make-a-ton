// Owner: A — replace this placeholder with the real page.
import { PlaceholderPage } from "@/components/placeholder-page";
import { requireRole } from "@/lib/auth/session";

export default async function Page() {
  await requireRole("ADMIN", "STAFF");
  return <PlaceholderPage href="/subscriptions" />;
}
