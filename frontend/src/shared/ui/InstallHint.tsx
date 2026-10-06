import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/shared/ui/button";

const DISMISSED_KEY = "saber-uli:install-hint-dismissed";

function isIos(): boolean {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

function isStandalone(): boolean {
  const iosStandalone = (navigator as Navigator & { standalone?: boolean }).standalone === true;
  return iosStandalone || window.matchMedia("(display-mode: standalone)").matches;
}

function wasDismissed(): boolean {
  try {
    return localStorage.getItem(DISMISSED_KEY) === "1";
  } catch {
    return false;
  }
}

function rememberDismissal(): void {
  try {
    localStorage.setItem(DISMISSED_KEY, "1");
  } catch {
    // Sin almacenamiento (modo privado): solo se oculta en esta visita.
  }
}

/**
 * Guía para instalar la PWA en iPhone y iPad: Safari no ofrece un aviso de instalación, así que
 * se explica el paso "Compartir → Agregar a inicio". No aparece si la app ya está instalada ni
 * en navegadores que sí ofrecen instalar (Android, escritorio).
 */
export function InstallHint() {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(() => isIos() && !isStandalone() && !wasDismissed());

  if (!visible) {
    return null;
  }

  return (
    <section
      aria-label={t("install.title")}
      className="mx-4 my-3 rounded-lg border border-primary/30 bg-primary/5 p-4 text-sm"
    >
      <h2 className="mb-1 font-semibold">{t("install.title")}</h2>
      <p className="mb-3">{t("install.ios")}</p>
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label={t("install.dismiss")}
        onClick={() => {
          rememberDismissal();
          setVisible(false);
        }}
      >
        {t("install.dismissShort")}
      </Button>
    </section>
  );
}
