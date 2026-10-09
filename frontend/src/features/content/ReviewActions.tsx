import { useMutation } from "@tanstack/react-query";
import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { approveItem, commentItem, rejectItem, retireItem, returnItem } from "@/api/content/items";
import type { Item } from "@/api/content/model";
import { Feedback, problemText } from "@/features/admin/common";
import { Button } from "@/shared/ui/button";
import { Label } from "@/shared/ui/label";

type Mode = "approve" | "return" | "reject" | "retire" | "comment";

const TEXTAREA =
  "mt-1 block w-full rounded-md border border-input bg-background px-3 py-2 text-base";

/**
 * Acciones de revisión de un ítem (US2; FR-012 a FR-014). Se muestran según `item.can`, que la
 * API calcula con los permisos y la regla de autoaprobación. Aprobar exige las dos confirmaciones;
 * devolver, un comentario; rechazar y retirar, un motivo. Cada acción envía la revisión que la
 * persona está viendo (`If-Match`, research R-09).
 */
export function ReviewActions({ item, onChanged }: { item: Item; onChanged: () => void }) {
  const { t } = useTranslation();
  const textId = useId();
  const [mode, setMode] = useState<Mode | null>(null);
  const [text, setText] = useState("");
  const [alignment, setAlignment] = useState(false);
  const [originality, setOriginality] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const headers = { "If-Match": `"${item.revision}"` };

  const action = useMutation({
    mutationFn: async (current: Mode) => {
      const body = text.trim();
      switch (current) {
        case "approve":
          return approveItem(
            item.code,
            { confirms_alignment: true, confirms_originality: true },
            { headers },
          );
        case "return":
          return returnItem(item.code, { comment: body }, { headers });
        case "reject":
          return rejectItem(item.code, { reason: body }, { headers });
        case "retire":
          return retireItem(item.code, { reason: body }, { headers });
        case "comment":
          return commentItem(item.code, { comment: body });
      }
    },
    onSuccess: (_, current) => {
      setMessage(t(`content.review.done.${current}`));
      setError(null);
      setMode(null);
      setText("");
      setAlignment(false);
      setOriginality(false);
      onChanged();
    },
    onError: (failure) => {
      setMessage(null);
      setError(problemText(failure));
    },
  });

  function open(next: Mode) {
    setMode(next);
    setMessage(null);
    setError(null);
  }

  const buttons: { mode: Mode; allowed: boolean }[] = [
    { mode: "approve", allowed: item.can.approve },
    { mode: "return", allowed: item.can.return },
    { mode: "reject", allowed: item.can.reject },
    { mode: "retire", allowed: item.can.retire },
    { mode: "comment", allowed: item.can.edit },
  ];
  const needsText = mode !== null && mode !== "approve";
  const ready = mode === "approve" ? alignment && originality : needsText && text.trim().length > 0;

  return (
    <section aria-label={t("content.review.actions")} className="space-y-3">
      <Feedback message={message} error={error} />
      {item.can.approve_blocked_reason === "self_approval" ? (
        <p className="rounded-md border border-amber-300 bg-amber-50 p-3">
          {t("content.review.selfApproval")}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {buttons
          .filter((button) => button.allowed)
          .map((button) => (
            <Button
              key={button.mode}
              type="button"
              variant={button.mode === "approve" ? "default" : "outline"}
              aria-expanded={mode === button.mode}
              onClick={() => open(button.mode)}
            >
              {t(`content.review.open.${button.mode}`)}
            </Button>
          ))}
      </div>
      {mode !== null ? (
        <form
          className="space-y-3 rounded-md border border-border p-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (ready) action.mutate(mode);
          }}
        >
          {mode === "approve" ? (
            <fieldset className="space-y-2">
              <legend className="font-semibold">{t("content.review.confirmations")}</legend>
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-1 h-5 w-5"
                  checked={alignment}
                  onChange={(event) => setAlignment(event.target.checked)}
                />
                <span>{t("content.review.confirmsAlignment")}</span>
              </label>
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-1 h-5 w-5"
                  checked={originality}
                  onChange={(event) => setOriginality(event.target.checked)}
                />
                <span>{t("content.review.confirmsOriginality")}</span>
              </label>
            </fieldset>
          ) : (
            <div>
              <Label htmlFor={textId}>{t(`content.review.textLabel.${mode}`)}</Label>
              <textarea
                id={textId}
                className={TEXTAREA}
                rows={3}
                maxLength={mode === "reject" || mode === "retire" ? 1000 : 2000}
                value={text}
                onChange={(event) => setText(event.target.value)}
              />
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={!ready || action.isPending}>
              {t(`content.review.submit.${mode}`)}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setMode(null)}>
              {t("content.review.cancel")}
            </Button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
