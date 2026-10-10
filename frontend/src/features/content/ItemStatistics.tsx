import { useTranslation } from "react-i18next";

import type { VersionStatistics } from "@/api/content/model";
import { useGetItemStatistics } from "@/api/content/insights";
import { isReauth, problemText } from "@/features/admin/common";

const MIN_RESPONSES = 30;
const COUNT = new Intl.NumberFormat("es-CO");
const PERCENT = new Intl.NumberFormat("es-CO", { style: "percent", maximumFractionDigits: 1 });
const INDEX = new Intl.NumberFormat("es-CO", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function VersionEntry({ entry }: { entry: VersionStatistics }) {
  const { t } = useTranslation();
  const title = t("content.statistics.version", {
    number: entry.version,
    state: t(`content.states.${entry.state}`),
  });
  const headingId = `estadisticas-version-${entry.version}`;
  return (
    <section aria-labelledby={headingId} className="space-y-2 rounded-md border p-3">
      <h3 id={headingId} className="font-medium">
        {title}
      </h3>
      {!entry.sufficient_data ? (
        <p>
          {t("content.statistics.insufficient", {
            count: entry.first_responses,
            shown: COUNT.format(entry.first_responses),
            minimum: MIN_RESPONSES,
          })}
        </p>
      ) : (
        <>
          <p>{t("content.statistics.responses", { value: COUNT.format(entry.first_responses) })}</p>
          <p>
            {t("content.statistics.correct", { value: PERCENT.format(entry.correct_rate ?? 0) })}
          </p>
          <p>
            {t("content.statistics.discrimination", {
              value:
                entry.discrimination == null
                  ? t("content.statistics.notAvailable")
                  : INDEX.format(entry.discrimination),
            })}
          </p>
          <ul
            aria-label={t("content.statistics.options", { number: entry.version })}
            className="space-y-1"
          >
            {Object.entries(entry.option_rates ?? {}).map(([option, rate]) => (
              <li key={option} className="flex items-center gap-2">
                <span className="w-6 font-mono">{option}</span>
                <span aria-hidden="true" className="h-3 flex-1 rounded bg-muted">
                  <span
                    className="block h-3 rounded bg-primary"
                    style={{ width: `${Math.round(rate * 100)}%` }}
                  />
                </span>
                <span className="w-14 text-right">{PERCENT.format(rate)}</span>
              </li>
            ))}
          </ul>
          {entry.signals.length ? (
            <ul
              aria-label={t("content.statistics.signalsOf", { number: entry.version })}
              className="list-disc pl-5 text-amber-900"
            >
              {entry.signals.map((signal) => (
                <li key={signal}>{t(`content.statistics.signals.${signal}`)}</li>
              ))}
            </ul>
          ) : null}
        </>
      )}
    </section>
  );
}

/**
 * Estadísticas de un ítem por versión publicada o retirada (US8; FR-041 a FR-044), calculadas
 * con la primera respuesta de cada estudiante. Con menos de 30 respuestas no se muestran cifras.
 */
export function ItemStatistics({ code }: { code: string }) {
  const { t } = useTranslation();
  const query = useGetItemStatistics(code);

  if (query.isError) {
    return isReauth(query.error) ? null : <p role="alert">{problemText(query.error)}</p>;
  }
  const versions = query.data?.items;
  if (!versions) return null;
  return (
    <section aria-labelledby={`estadisticas-${code}`} className="space-y-3">
      <h2 id={`estadisticas-${code}`} className="text-lg font-semibold">
        {t("content.statistics.title")}
      </h2>
      {versions.length === 0 ? (
        <p>{t("content.statistics.none")}</p>
      ) : (
        versions.map((entry) => <VersionEntry key={entry.version} entry={entry} />)
      )}
    </section>
  );
}
