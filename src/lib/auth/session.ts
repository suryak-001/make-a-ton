// Owner: A. Contract used by everyone: getSession / requireUser / requireRole.
import "server-only";
import { getIronSession, type SessionOptions } from "iron-session";
import { cookies } from "next/headers";
import { forbidden, redirect } from "next/navigation";
import type { Role } from "@/generated/prisma/enums";
import { SESSION_COOKIE, type SessionData } from "./session-config";

export type Session = SessionData;

const sessionOptions: SessionOptions = {
  cookieName: SESSION_COOKIE,
  password: process.env.SESSION_SECRET!,
  ttl: 60 * 60 * 24 * 7,
  cookieOptions: {
    secure: process.env.NODE_ENV === "production",
    httpOnly: true,
    sameSite: "lax",
  },
};

async function ironSession() {
  return getIronSession<Partial<SessionData>>(await cookies(), sessionOptions);
}

export async function getSession(): Promise<Session | null> {
  const s = await ironSession();
  if (!s.userId || !s.role) return null;
  return { userId: s.userId, role: s.role, name: s.name ?? "", customerId: s.customerId };
}

export async function createSession(data: Session) {
  const s = await ironSession();
  Object.assign(s, data);
  await s.save();
}

export async function destroySession() {
  const s = await ironSession();
  s.destroy();
}

/** Redirects to /login when signed out. */
export async function requireUser(): Promise<Session> {
  const session = await getSession();
  if (!session) redirect("/login");
  return session;
}

/** Use at the top of every page, server action and route handler that touches data. */
export async function requireRole(...roles: Role[]): Promise<Session> {
  const session = await requireUser();
  if (!roles.includes(session.role)) forbidden();
  return session;
}

export function homeFor(role: Role) {
  return role === "CUSTOMER" ? "/portal" : "/dashboard";
}
