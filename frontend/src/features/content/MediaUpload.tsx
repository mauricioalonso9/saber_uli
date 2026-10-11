import { useEffect, useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { getContentMedia, uploadContentMedia } from "@/api/content/contexts";
import type { Media } from "@/api/content/model";
import { problemText } from "@/features/admin/common";

/**
 * Subida de la imagen de un contexto (FR-009; research R-11). El servidor verifica el formato,
 * el tamaño y las dimensiones y la re-codifica sin metadatos; aquí se explica cada rechazo.
 *
 * La imagen se pide con el cliente de la API (lleva el token) y se muestra como URL de objeto:
 * un `<img src>` directo no enviaría la autorización.
 */
export function MediaUpload({
  mediaId,
  onUploaded,
  describedBy,
}: {
  mediaId: string | null | undefined;
  onUploaded: (media: Media) => void;
  describedBy?: string;
}) {
  const { t } = useTranslation();
  const inputId = useId();
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const preview = useObjectUrl(mediaId);

  async function upload(file: File) {
    setBusy(true);
    setError(null);
    setStatus(t("content.media.uploading"));
    try {
      const media = await uploadContentMedia({ file });
      setStatus(t("content.media.uploaded", { width: media.width, height: media.height }));
      onUploaded(media);
    } catch (failure) {
      setStatus(null);
      setError(problemText(failure));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2">
      <label htmlFor={inputId} className="font-medium">
        {t("content.media.label")}
      </label>
      <input
        id={inputId}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        disabled={busy}
        aria-describedby={describedBy}
        className="block"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void upload(file);
        }}
      />
      {status ? (
        <p role="status" aria-live="polite">
          {status}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="rounded-md border border-red-300 bg-red-50 p-3 text-red-900">
          {error}
        </p>
      ) : null}
      {preview ? (
        <img src={preview} alt={t("content.media.preview")} className="max-h-64 rounded-md" />
      ) : null}
    </div>
  );
}

/** URL de objeto de una imagen del banco; se libera al cambiar o al desmontar. */
export function useObjectUrl(mediaId: string | null | undefined): string | null {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!mediaId || typeof URL.createObjectURL !== "function") return;
    let created: string | null = null;
    let active = true;
    getContentMedia(mediaId)
      .then((blob) => {
        if (!active) return;
        created = URL.createObjectURL(blob);
        setUrl(created);
      })
      .catch(() => setUrl(null));
    return () => {
      active = false;
      if (created) URL.revokeObjectURL(created);
      setUrl(null);
    };
  }, [mediaId]);
  return url;
}
