// Edge-safe (no "server-only", no Prisma) so src/proxy.ts can import it.
import type { Role } from "@/generated/prisma/enums";

export const SESSION_COOKIE = "brightloop_session";

export type SessionData = {
  userId: string;
  role: Role;
  name: string;
  customerId?: string; // set for CUSTOMER users — scope every portal query by this
};
