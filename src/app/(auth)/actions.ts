"use server";
// Owner: A. login/logout are real; signup (A1) and password reset (A2) are next.
import { redirect } from "next/navigation";
import * as z from "zod";
import { db } from "@/lib/db";
import { verifyPassword } from "@/lib/auth/password";
import { createSession, destroySession, homeFor } from "@/lib/auth/session";

export type FormState = { error?: string } | undefined;

const loginSchema = z.object({
  email: z.email().trim().toLowerCase(),
  password: z.string().min(1),
});

export async function login(_prev: FormState, formData: FormData): Promise<FormState> {
  const parsed = loginSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { error: "Enter your email and password." };

  const user = await db.user.findUnique({
    where: { email: parsed.data.email },
    include: { customer: { select: { id: true } } },
  });
  if (!user || !(await verifyPassword(parsed.data.password, user.passwordHash))) {
    return { error: "Invalid email or password." };
  }

  await createSession({ userId: user.id, role: user.role, name: user.name, customerId: user.customer?.id });
  redirect(homeFor(user.role));
}

export async function logout() {
  await destroySession();
  redirect("/login");
}
