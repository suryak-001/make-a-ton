// Optimistic route guard: bounces signed-out users to /login and keeps customers in /portal.
// Real authorization happens in pages/actions via requireRole() — never rely on this alone.
import { unsealData } from "iron-session";
import { NextResponse, type NextRequest } from "next/server";
import { SESSION_COOKIE, type SessionData } from "@/lib/auth/session-config";

const PUBLIC_PATHS = ["/login", "/signup", "/forgot-password", "/reset-password"];

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));

  const cookie = request.cookies.get(SESSION_COOKIE)?.value;
  const session = cookie
    ? await unsealData<Partial<SessionData>>(cookie, { password: process.env.SESSION_SECRET! }).catch(() => ({}))
    : {};
  const role = (session as Partial<SessionData>).role;

  if (!role) {
    return isPublic || pathname === "/" ? NextResponse.next() : NextResponse.redirect(new URL("/login", request.url));
  }
  if (isPublic) return NextResponse.redirect(new URL("/", request.url));
  if (role === "CUSTOMER" && !pathname.startsWith("/portal")) {
    return NextResponse.redirect(new URL("/portal", request.url));
  }
  if (role !== "CUSTOMER" && pathname.startsWith("/portal")) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|ico)$).*)"],
};
