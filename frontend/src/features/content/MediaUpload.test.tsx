/**
 * T055: subida de la imagen de un contexto (FR-009, R-11). Los errores 413 y 415 se explican en
 * lenguaje claro.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { useSessionStore } from "@/features/auth/session-store";
import { MediaUpload } from "@/features/content/MediaUpload";

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledFrame: "error" }));
beforeEach(() => useSessionStore.getState().setSession("token", 600));
afterEach(() => {
  server.resetHandlers();
  useSessionStore.getState().clear();
});
afterAll(() => server.close());

const MEDIA = {
  id: "0b6a0366-9b56-451a-9a19-49cbcbe21c1c",
  content_type: "image/png",
  width: 40,
  height: 30,
  size_bytes: 120,
  url: "/api/v1/content/media/0b6a0366-9b56-451a-9a19-49cbcbe21c1c",
};
const LABEL = "Imagen (PNG, JPEG o WebP, hasta 1 MB)";

function renderUpload() {
  const onUploaded = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MediaUpload mediaId={null} onUploaded={onUploaded} />
    </QueryClientProvider>,
  );
  return onUploaded;
}

const png = () =>
  new File([new Uint8Array([137, 80, 78, 71])], "infografia.png", { type: "image/png" });

describe("subida de imágenes", () => {
  it("sube la imagen y entrega su id", async () => {
    server.use(http.post("/api/v1/content/media", () => HttpResponse.json(MEDIA, { status: 201 })));
    const onUploaded = renderUpload();
    const user = userEvent.setup();

    await user.upload(screen.getByLabelText(LABEL), png());

    expect(await screen.findByRole("status")).toHaveTextContent("Imagen cargada: 40 × 30 px.");
    expect(onUploaded).toHaveBeenCalledWith(MEDIA);
  });

  it.each([
    [413, "file-too-large", "La imagen pesa más de 1 MB. Redúcela e intenta de nuevo."],
    [
      415,
      "unsupported-media-type",
      "La imagen debe ser PNG, JPEG o WebP y medir como máximo 4 000 px por lado.",
    ],
  ])("explica el error %i", async (status, slug, message) => {
    server.use(
      http.post("/api/v1/content/media", () =>
        HttpResponse.json(
          { type: `urn:saber-uli:problem:${slug}`, title: "x", status },
          { status, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    const onUploaded = renderUpload();
    const user = userEvent.setup();

    await user.upload(screen.getByLabelText(LABEL), png());

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(onUploaded).not.toHaveBeenCalled();
  });
});
