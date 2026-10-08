import { useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { InvitationBatch } from "@/api/model";
import { getValidateInvitationBatchUrl, useConfirmInvitationBatch } from "@/api/invitations";
import { customInstance } from "@/shared/api/http";
import { Button } from "@/shared/ui/button";
import { Label } from "@/shared/ui/label";
import { ScrollRegion } from "@/shared/ui/ScrollRegion";

import { problemText } from "./InviteForm";

/**
 * Invitar por lote (FR-009; escenario 5.2): el CSV (`correo,nombre,vence`) se envía tal cual;
 * el servidor responde el reporte por fila y solo las válidas se envían al confirmar.
 */
export function BatchUpload({ onConfirmed }: { onConfirmed: () => void }) {
  const { t } = useTranslation();
  const ids = { title: useId(), file: useId() };
  const fileInput = useRef<HTMLInputElement>(null);
  const [batch, setBatch] = useState<InvitationBatch | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const confirm = useConfirmInvitationBatch();

  async function check() {
    const file = fileInput.current?.files?.[0];
    setError(null);
    setDone(null);
    setBatch(null);
    if (!file) {
      setError(t("invitations.batch.chooseFile"));
      return;
    }
    setChecking(true);
    try {
      // El cliente generado serializa el cuerpo como JSON: el CSV va tal cual.
      const report = await customInstance<InvitationBatch>(getValidateInvitationBatchUrl(), {
        method: "POST",
        headers: { "Content-Type": "text/csv" },
        body: await file.text(),
      });
      setBatch(report);
    } catch (problem) {
      setError(problemText(problem));
    } finally {
      setChecking(false);
    }
  }

  async function send() {
    if (!batch) return;
    setError(null);
    try {
      const confirmed = await confirm.mutateAsync({ batchId: batch.id });
      setBatch(confirmed);
      setDone(t("invitations.batch.sent", { count: confirmed.valid_count }));
      onConfirmed();
    } catch (problem) {
      setError(problemText(problem));
    }
  }

  return (
    <section aria-labelledby={ids.title} className="mb-8 space-y-4 rounded-md border p-4">
      <h2 id={ids.title} className="text-lg font-semibold">
        {t("invitations.batch.title")}
      </h2>
      <p className="text-sm">{t("invitations.batch.help")}</p>
      {error ? (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900">
          {error}
        </p>
      ) : null}
      {done ? (
        <p role="status" className="rounded-md border border-green-300 bg-green-50 p-3">
          {done}
        </p>
      ) : null}
      <div>
        <Label htmlFor={ids.file}>{t("invitations.batch.file")}</Label>
        <input
          ref={fileInput}
          id={ids.file}
          type="file"
          accept=".csv,text/csv"
          className="mt-1 block w-full text-sm"
        />
      </div>
      <Button
        type="button"
        variant="outline"
        className="h-11"
        disabled={checking}
        onClick={() => void check()}
      >
        {t("invitations.batch.check")}
      </Button>

      {batch ? (
        <>
          <p>
            {t("invitations.batch.summary", {
              count: batch.valid_count,
              invalid: batch.invalid_count,
            })}
          </p>
          <ScrollRegion label={t("invitations.batch.report")}>
            <table aria-label={t("invitations.batch.report")} className="w-full text-left text-sm">
              <thead>
                <tr className="border-b">
                  <th scope="col" className="py-2 pr-3">
                    {t("invitations.batch.line")}
                  </th>
                  <th scope="col" className="py-2 pr-3">
                    {t("invitations.table.email")}
                  </th>
                  <th scope="col" className="py-2 pr-3">
                    {t("invitations.batch.result")}
                  </th>
                  <th scope="col" className="py-2">
                    {t("invitations.batch.detail")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {batch.rows.map((row) => (
                  <tr key={row.line} className="border-b align-top">
                    <td className="py-2 pr-3">{row.line}</td>
                    <td className="break-all py-2 pr-3">{row.email}</td>
                    <td className="py-2 pr-3">{t(`invitations.batch.results.${row.result}`)}</td>
                    <td className="py-2">{row.message ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollRegion>
          {batch.status === "pending_confirmation" ? (
            <Button
              type="button"
              className="h-11"
              disabled={batch.valid_count === 0 || confirm.isPending}
              onClick={() => void send()}
            >
              {t("invitations.batch.confirm", { count: batch.valid_count })}
            </Button>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
