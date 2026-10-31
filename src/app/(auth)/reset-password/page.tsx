// Owner: A (A2) — replace this placeholder.
import Link from "next/link";
import { TodoCard } from "@/components/todo-card";

export default function Page() {
  return (
    <div className="grid gap-4">
      <TodoCard title="Reset password" owner="A" step="A2" todo={["Validate token from ?token=", "Apply passwordSchema, mark token used"]} />
      <Link href="/login" className="text-center text-sm hover:underline">
        Back to sign in
      </Link>
    </div>
  );
}
