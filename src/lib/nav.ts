import type { Role } from "@/generated/prisma/enums";

export type NavItem = {
  href: string;
  label: string;
  roles: Role[]; // who sees it in the sidebar; pages must still call requireRole()
  owner: "A" | "B";
  step: string; // PLAN.md step id
  todo: string[];
};

const STAFF: Role[] = ["ADMIN", "STAFF"];
const ADMIN: Role[] = ["ADMIN"];

export const APP_NAV: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    roles: STAFF,
    owner: "B",
    step: "B8",
    todo: ["KPI cards: active subs, MRR, revenue, payments, outstanding, overdue", "Revenue-by-month chart", "Overdue invoices table"],
  },
  {
    href: "/subscriptions",
    label: "Subscriptions",
    roles: STAFF,
    owner: "A",
    step: "A7",
    todo: ["Server-paginated list with status/customer/plan filters", "Form with lines (computeLine)", "State machine action buttons"],
  },
  {
    href: "/customers",
    label: "Customers",
    roles: STAFF,
    owner: "A",
    step: "A3",
    todo: ["Customer CRUD", "Link to portal user when one exists"],
  },
  {
    href: "/invoices",
    label: "Invoices",
    roles: STAFF,
    owner: "B",
    step: "B6",
    todo: ["List with status/customer/date/overdue filters", "Confirm / Cancel / Send / Print", '"Run billing now" button (B5)'],
  },
  {
    href: "/payments",
    label: "Payments",
    roles: STAFF,
    owner: "B",
    step: "B7",
    todo: ["Record payment against invoice", "Auto-mark invoice Paid", "Block overpayment"],
  },
  {
    href: "/quotation-templates",
    label: "Quotation templates",
    roles: STAFF,
    owner: "A",
    step: "A6",
    todo: ["Template CRUD with lines + validity days", '"New subscription from template"'],
  },
  {
    href: "/products",
    label: "Products",
    roles: STAFF,
    owner: "A",
    step: "A4",
    todo: ["Product CRUD (admin), read-only for staff", "Variant editor: attribute, value, extra price"],
  },
  {
    href: "/plans",
    label: "Plans",
    roles: STAFF,
    owner: "A",
    step: "A5",
    todo: ["Plan CRUD (admin), read-only for staff", "Period, min qty, availability, 4 behaviour flags"],
  },
  {
    href: "/taxes",
    label: "Taxes",
    roles: ADMIN,
    owner: "B",
    step: "B2",
    todo: ["Tax CRUD (percent / fixed)", "Default taxes per product"],
  },
  {
    href: "/discounts",
    label: "Discounts",
    roles: ADMIN,
    owner: "B",
    step: "B3",
    todo: ["Discount CRUD with all rules", "Product vs subscription scope", "Usage limit tracking"],
  },
  {
    href: "/reports",
    label: "Reports",
    roles: STAFF,
    owner: "B",
    step: "B8",
    todo: ["Filters: date range, plan, customer, status", "Summary view", "< 2 s with 5k subscriptions"],
  },
  {
    href: "/users",
    label: "Users",
    roles: ADMIN,
    owner: "A",
    step: "A3",
    todo: ["Admin-only: add staff member", "List users with role"],
  },
];

export const PORTAL_NAV: NavItem[] = [
  {
    href: "/portal/subscriptions",
    label: "My subscriptions",
    roles: ["CUSTOMER"],
    owner: "A",
    step: "A9",
    todo: ["List + read-only detail of the customer's own subscriptions"],
  },
  {
    href: "/portal/invoices",
    label: "My invoices",
    roles: ["CUSTOMER"],
    owner: "B",
    step: "B9",
    todo: ["List of the customer's own invoices, print/download"],
  },
];

export function navItem(href: string): NavItem {
  const item = [...APP_NAV, ...PORTAL_NAV].find((i) => i.href === href);
  if (!item) throw new Error(`No nav item for ${href}`);
  return item;
}
