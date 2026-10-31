// Owner: A
import bcrypt from "bcryptjs";
import * as z from "zod";

// Brief: "more than eight characters, with an uppercase letter, a lowercase letter and a special character".
export const passwordSchema = z
  .string()
  .min(9, { error: "Must be more than 8 characters." })
  .regex(/[a-z]/, { error: "Must contain a lowercase letter." })
  .regex(/[A-Z]/, { error: "Must contain an uppercase letter." })
  .regex(/[^A-Za-z0-9]/, { error: "Must contain a special character." });

export function hashPassword(password: string) {
  return bcrypt.hash(password, 10);
}

export function verifyPassword(password: string, hash: string) {
  return bcrypt.compare(password, hash);
}
