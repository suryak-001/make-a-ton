import { navItem } from "@/lib/nav";
import { PageHeader } from "./page-header";
import { TodoCard } from "./todo-card";

/** Renders the PLAN.md checklist for a nav entry. Replace with the real page. */
export function PlaceholderPage({ href }: { href: string }) {
  const item = navItem(href);
  return (
    <>
      <PageHeader title={item.label} />
      <TodoCard title={item.label} owner={item.owner} step={item.step} todo={item.todo} />
    </>
  );
}
