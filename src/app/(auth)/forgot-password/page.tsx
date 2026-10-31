// Owner: A (A2) — replace this placeholder.
import Link from "next/link";
import { TodoCard } from "@/components/todo-card";

export default function Page() {
  return (
    <div className="grid gap-4">
      <TodoCard title="Forgot password" owner="A" step="A2" todo={["Create hashed single-use PasswordResetToken (1h expiry)", "Email the reset link with sendMail()"]} />
      <Link href="/login" className="text-center text-sm hover:underline">
        Back to sign in
      </Link>
    </div>
  );
}
