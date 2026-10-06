/** Lectura de correos de Mailpit (perfil e2e) para seguir enlaces de invitación e ingreso. */
import { type APIRequestContext, expect, request } from "@playwright/test";

const MAILPIT_URL = process.env.E2E_MAILPIT_URL ?? "http://localhost:8025";

export interface MailpitMessage {
  ID: string;
  Subject: string;
  To: { Address: string }[];
  HTML: string;
  Text: string;
}

export class Mailpit {
  private constructor(private readonly api: APIRequestContext) {}

  static async connect(): Promise<Mailpit> {
    return new Mailpit(await request.newContext({ baseURL: MAILPIT_URL }));
  }

  async clear(): Promise<void> {
    await this.api.delete("/api/v1/messages");
  }

  /** Espera el correo más reciente para `to` (hasta `timeoutMs`). */
  async latestFor(to: string, timeoutMs = 15_000): Promise<MailpitMessage> {
    let found: MailpitMessage | undefined;
    await expect
      .poll(
        async () => {
          const response = await this.api.get(
            `/api/v1/search?query=${encodeURIComponent(`to:"${to}"`)}`,
          );
          const body = (await response.json()) as { messages: { ID: string }[] };
          const first = body.messages[0];
          if (!first) {
            return false;
          }
          found = (await (
            await this.api.get(`/api/v1/message/${first.ID}`)
          ).json()) as MailpitMessage;
          return true;
        },
        { timeout: timeoutMs, message: "no llegó el correo esperado" },
      )
      .toBe(true);
    return found as MailpitMessage;
  }

  /** Primer enlace absoluto del correo que apunta a `path` (por ejemplo `/acceso`). */
  static linkTo(message: MailpitMessage, path: string): string {
    const match = message.Text.match(new RegExp(`https?://[^\\s]+${path}[^\\s]*`));
    if (!match) {
      throw new Error(`el correo no contiene un enlace a ${path}`);
    }
    return match[0];
  }

  async dispose(): Promise<void> {
    await this.api.dispose();
  }
}
