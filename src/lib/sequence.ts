import "server-only";
import type { Prisma } from "@/generated/prisma/client";
import { db } from "./db";

type Tx = Prisma.TransactionClient | typeof db;

/**
 * Atomically reserves the next number in a named sequence.
 *   nextNumber("SUB", "SUB-")            -> "SUB-00001"
 *   nextNumber("INV-2026", "INV-2026-")  -> "INV-2026-00001"
 * Pass the transaction client when called inside $transaction.
 */
export async function nextNumber(name: string, prefix: string, tx: Tx = db, pad = 5): Promise<string> {
  const rows = await tx.$queryRaw<{ next: number }[]>`
    INSERT INTO "Sequence" ("name", "next") VALUES (${name}, 2)
    ON CONFLICT ("name") DO UPDATE SET "next" = "Sequence"."next" + 1
    RETURNING "next"`;
  return `${prefix}${String(rows[0].next - 1).padStart(pad, "0")}`;
}
