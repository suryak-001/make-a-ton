// Owner: A (A1) — replace this placeholder.
import Link from "next/link";
import { TodoCard } from "@/components/todo-card";

export default function Page() {
  return (
    <div className="grid gap-4">
      <TodoCard title="Create account" owner="A" step="A1" todo={["Email unique, password policy from lib/auth/password.ts", "Creates User(CUSTOMER) + linked Customer, then signs in"]} />
      <Link href="/login" className="text-center text-sm hover:underline">
        Back to sign in
      </Link>
    </div>
  );
}
