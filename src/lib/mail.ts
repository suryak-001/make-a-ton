import "server-only";
import nodemailer from "nodemailer";

type Mail = { to: string; subject: string; text: string; html?: string };

/** Sends via SMTP when SMTP_HOST is set; otherwise logs to the server console (dev). */
export async function sendMail(mail: Mail) {
  if (!process.env.SMTP_HOST) {
    console.log(`\n📧 [mail] to=${mail.to} subject="${mail.subject}"\n${mail.text}\n`);
    return;
  }
  const transport = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: Number(process.env.SMTP_PORT ?? 587),
    auth: process.env.SMTP_USER ? { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS } : undefined,
  });
  await transport.sendMail({ from: process.env.MAIL_FROM, ...mail });
}
