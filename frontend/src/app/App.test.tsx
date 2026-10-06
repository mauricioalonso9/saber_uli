/**
 * T060: shell de la aplicación (idioma es-CO, indicador de conexión y navegación por teclado;
 * WCAG 2.2 AA, constitución VII).
 */
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "@/app/App";
import { createAppRouter } from "@/app/router";

function renderAt(path: string) {
  const router = createAppRouter({ initialPath: path });
  render(<App router={router} />);
  return router;
}

function setOnline(online: boolean) {
  vi.spyOn(navigator, "onLine", "get").mockReturnValue(online);
  act(() => {
    window.dispatchEvent(new Event(online ? "online" : "offline"));
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("shell de la aplicación", () => {
  it("usa el idioma es-CO en el documento y en los textos", async () => {
    renderAt("/inicio");

    expect(await screen.findByRole("heading", { name: "Inicio" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("es-CO");
    expect(screen.getByRole("banner")).toHaveTextContent("Saber Uli");
  });

  it("muestra el estado de conexión y reacciona a los cambios", async () => {
    renderAt("/inicio");
    const status = await screen.findByRole("status", { name: "Estado de conexión" });

    expect(status).toHaveTextContent("En línea");
    setOnline(false);
    expect(status).toHaveTextContent("Sin conexión");
    setOnline(true);
    expect(status).toHaveTextContent("En línea");
  });

  it("el primer elemento enfocable salta al contenido principal", async () => {
    const user = userEvent.setup();
    renderAt("/inicio");
    await screen.findByRole("heading", { name: "Inicio" });

    await user.tab();
    const skip = screen.getByRole("link", { name: "Saltar al contenido" });
    expect(skip).toHaveFocus();

    await user.keyboard("{Enter}");
    expect(screen.getByRole("main")).toHaveFocus();
  });

  it("la navegación principal tiene nombre y se recorre con el teclado", async () => {
    const user = userEvent.setup();
    renderAt("/inicio");
    await screen.findByRole("heading", { name: "Inicio" });

    const nav = screen.getByRole("navigation", { name: "Principal" });
    const links = within(nav).getAllByRole("link");
    expect(links.length).toBeGreaterThan(0);

    await user.tab(); // salto al contenido
    await user.tab();
    expect(links[0]).toHaveFocus();
  });

  it("la raíz lleva a /inicio", async () => {
    const router = renderAt("/");

    expect(await screen.findByRole("heading", { name: "Inicio" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/inicio");
  });

  it("una ruta desconocida muestra una página en español", async () => {
    renderAt("/no-existe");

    expect(
      await screen.findByRole("heading", { name: "Página no encontrada" }),
    ).toBeInTheDocument();
  });
});
