import { useTranslation } from "react-i18next";

import type { ItemHistoryVersionsItem } from "@/api/content/model";
import { useGetItemHistory } from "@/api/content/items";
import { isReauth, problemText } from "@/features/admin/common";
import { fieldLabel } from "@/features/content/fields";
import { formatDateTime } from "@/shared/lib/dates";

function VersionEntry({ version }: { version: ItemHistoryVersionsItem }) {
  const { t } = useTranslation();
  const changed = version.changed_fields ?? [];
  return (
    <li className="space-y-1 rounded-md border p-3">
      <p className="font-medium">
        {t("content.history.version", {
          number: version.number,
          state: t(`content.states.${version.state}`),
        })}
      </p>
      <div className="text-sm">
        {version.author ? (
          <p>{t("content.history.author", { name: version.author.display_name })}</p>
        ) : null}
        {version.reviewer ? (
          <p>{t("content.history.reviewer", { name: version.reviewer.display_name })}</p>
        ) : null}
        <p>{t("content.history.created", { date: formatDateTime(version.created_at) })}</p>
        {version.published_at ? (
          <p>{t("content.history.published", { date: formatDateTime(version.published_at) })}</p>
        ) : null}
        {version.retired_at ? (
          <p>{t("content.history.retired", { date: formatDateTime(version.retired_at) })}</p>
        ) : null}
        <p>
          {changed.length
            ? t("content.history.changed", { fields: changed.map(fieldLabel).join(", ") })
            : version.number === 1
              ? t("content.history.firstVersion")
              : t("content.history.noChanges")}
        </p>
      </div>
    </li>
  );
}

/**
 * Historia de un ítem (FR-018): cada versión con su estado, autor, revisor, fechas y campos
 * cambiados frente a la anterior, y los eventos con quién, cuándo y el comentario o motivo.
 */
export function ItemHistory({ code }: { code: string }) {
  const { t } = useTranslation();
  const query = useGetItemHistory(code);

  if (query.isError) {
    return isReauth(query.error) ? null : <p role="alert">{problemText(query.error)}</p>;
  }
  const history = query.data;
  if (!history) return null;
  return (
    <section aria-labelledby={`historia-${code}`} className="space-y-4">
      <h2 id={`historia-${code}`} className="text-lg font-semibold">
        {t("content.history.title")}
      </h2>
      <h3 className="font-medium">{t("content.history.versions")}</h3>
      <ul aria-label={t("content.history.versions")} className="space-y-2">
        {[...history.versions]
          .sort((a, b) => b.number - a.number)
          .map((version) => (
            <VersionEntry key={version.number} version={version} />
          ))}
      </ul>
      <h3 className="font-medium">{t("content.history.events")}</h3>
      <ol aria-label={t("content.history.events")} className="space-y-1 text-sm">
        {history.events.map((event) => (
          <li key={event.id}>
            <p>
              {[
                t(`content.history.types.${event.type}`),
                event.version ? t("content.history.eventVersion", { number: event.version }) : null,
                event.actor?.display_name ?? t("content.history.system"),
                formatDateTime(event.occurred_at),
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
            {event.comment ? <p className="text-muted-foreground">{event.comment}</p> : null}
            {event.reason ? <p className="text-muted-foreground">{event.reason}</p> : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
