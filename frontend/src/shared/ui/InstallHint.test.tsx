/**
 * T068: guía de instalación en iPhone (Safari no muestra el aviso de instalación de la PWA).
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { InstallHint } from "@/shared/ui/InstallHint";

const IPHONE =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1";
const ANDROID =
  "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36";

function browser(userAgent: string, { standalone = false } = {}) {
  vi.spyOn(navigator, "userAgent", "get").mockReturnValue(userAgent);
  Object.defineProperty(navigator, "standalone", { value: standalone, configurable: true });
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: standalone && query.includes("standalone"),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
}

beforeEach(() => {
  localStorage.clear();
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("InstallHint", () => {
  it("en iPhone explica cómo agregar la app a la pantalla de inicio", () => {
    browser(IPHONE);
    render(<InstallHint />);

    const hint = screen.getByRole("region", { name: "Instala Saber Uli" });
    expect(hint).toHaveTextContent("Compartir");
    expect(hint).toHaveTextContent("Agregar a inicio");
  });

  it("se puede cerrar y no vuelve a aparecer", async () => {
    browser(IPHONE);
    const user = userEvent.setup();
    const { unmount } = render(<InstallHint />);

    await user.click(screen.getByRole("button", { name: "Cerrar la guía de instalación" }));
    expect(screen.queryByRole("region", { name: "Instala Saber Uli" })).not.toBeInTheDocument();

    unmount();
    render(<InstallHint />);
    expect(screen.queryByRole("region", { name: "Instala Saber Uli" })).not.toBeInTheDocument();
  });

  it("no aparece si la app ya está instalada", () => {
    browser(IPHONE, { standalone: true });
    render(<InstallHint />);

    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });

  it("no aparece en Android ni en escritorio (el navegador ofrece instalar)", () => {
    browser(ANDROID);
    render(<InstallHint />);

    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });

  it("funciona aunque el almacenamiento local no esté disponible", async () => {
    browser(IPHONE);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    const user = userEvent.setup();
    render(<InstallHint />);

    await user.click(screen.getByRole("button", { name: "Cerrar la guía de instalación" }));
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });
});
