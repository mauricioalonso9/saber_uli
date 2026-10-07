import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Invitation } from "@/api/model";
import {
  useResendInvitation,
  useRevokeInvitation,
  useUpdateInvitationExpiry,
} from "@/api/invitations";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

import { endOfDayInBogota, problemText, todayInBogota } from "./InviteForm";

interface Props {
  invitation: Invitation;
  /** Mensaje para la página (éxito) y recarga del listado. */
  onDone: (message: string) => void;
  onError: (message: string) => void;
}

/**
 * Acciones de una invitación (FR-010; escenarios 5.4 y 5.5): reenviar si no se aceptó, cambiar
 * el vencimiento (también renueva un acceso vencido o revocado hace menos de 90 días) y revocar
 * con confirmación.
 */
export function InvitationActions({ invitation, onDone, onError }: Props) {
  const { t } = useTranslation();
  const resend = useResendInvitation();
  const revoke = useRevokeInvitation();
  const update = useUpdateInvitationExpiry();
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [until, setUntil] = useState("");
  const confirmButton = useRef<HTMLButtonElement>(null);
  const ids = { until: useId(), confirmTitle: useId() };
  const who = invitation.email ?? t("invitations.table.noEmail");

  const accepted = Boolean(invitation.accepted_at);
  const canResend = invitation.status === "sent" || (invitation.status === "expired" && !accepted);
  const canRevoke = invitation.status === "sent" || invitation.status === "accepted";
  const canChange = invitation.status !== "revoked" || accepted;

  useEffect(() => {
    if (confirming) confirmButton.current?.focus();
  }, [confirming]);

  async function run(action: () => Promise<unknown>, success: string) {
    try {
      await action();
      onDone(success);
    } catch (problem) {
      onError(problemText(problem));
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {canResend ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            aria-label={t("invitations.actions.resendFor", { who })}
            onClick={() =>
              void run(
                () => resend.mutateAsync({ invitationId: invitation.id }),
                t("invitations.actions.resent", { who }),
              )
            }
          >
            {t("invitations.actions.resend")}
          </Button>
        ) : null}
        {canChange ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            aria-expanded={editing}
            aria-label={t("invitations.actions.changeFor", { who })}
            onClick={() => setEditing((value) => !value)}
          >
            {t("invitations.actions.change")}
          </Button>
        ) : null}
        {canRevoke ? (
          <Button
            type="button"
            size="sm"
            variant="destructive"
            aria-label={t("invitations.actions.revokeFor", { who })}
            onClick={() => setConfirming(true)}
          >
            {t("invitations.actions.revoke")}
          </Button>
        ) : null}
      </div>

      {editing ? (
        <form
          className="flex flex-wrap items-end gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (!until || until <= todayInBogota()) {
              onError(t("invitations.form.errors.date"));
              return;
            }
            void run(
              () =>
                update.mutateAsync({
                  invitationId: invitation.id,
                  data: { access_expires_at: endOfDayInBogota(until) },
                }),
              t("invitations.actions.changed", { who }),
            ).then(() => setEditing(false));
          }}
        >
          <div>
            <Label htmlFor={ids.until}>{t("invitations.actions.newDate")}</Label>
            <Input
              id={ids.until}
              type="date"
              value={until}
              onChange={(event) => setUntil(event.target.value)}
            />
          </div>
          <Button type="submit" size="sm">
            {t("invitations.actions.save")}
          </Button>
        </form>
      ) : null}

      {confirming ? (
        <div
          role="alertdialog"
          aria-labelledby={ids.confirmTitle}
          className="rounded-md border border-destructive p-3"
        >
          <p id={ids.confirmTitle} className="mb-2 font-semibold">
            {t("invitations.actions.confirmTitle", { who })}
          </p>
          <p className="mb-3 text-sm">{t("invitations.actions.confirmBody")}</p>
          <div className="flex gap-2">
            <Button
              ref={confirmButton}
              type="button"
              size="sm"
              variant="destructive"
              onClick={() =>
                void run(
                  () => revoke.mutateAsync({ invitationId: invitation.id }),
                  t("invitations.actions.revoked", { who }),
                ).then(() => setConfirming(false))
              }
            >
              {t("invitations.actions.confirmYes")}
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={() => setConfirming(false)}>
              {t("invitations.actions.cancel")}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
