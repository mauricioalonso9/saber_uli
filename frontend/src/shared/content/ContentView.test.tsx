/**
 * T031: presentación del contenido de un ítem (research R-10, R-17; FR-006, FR-009, FR-025).
 *
 * `ContentView` es lo que verá el estudiante: la vista previa del docente (002) y la práctica
 * (003) usan el mismo componente. El Markdown admite tablas y fórmulas, nunca HTML crudo.
 */
import { render, screen, within } from "@testing-library/react";
import axe from "axe-core";
import { describe, expect, it } from "vitest";

import { ContentView, type ContentViewProps } from "@/shared/content/ContentView";

const SELECTION: ContentViewProps = {
  kind: "selection",
  context: {
    kind: "table",
    title: "Préstamo de equipos",
    body_md: "| Usuario | Plazo |\n|---|---|\n| Estudiante | 3 días |",
  },
  stem_md: "Si $x^2 = 9$, ¿cuál es el plazo?",
  options: [
    { key: "A", text: "3 días", correct: true, feedback: "Correcto: lo dice la tabla." },
    { key: "B", text: "5 días", correct: false, feedback: "Ese es el plazo de docentes." },
  ],
  explanation_md: "La tabla indica el plazo por tipo de usuario.",
};

async function violations(container: HTMLElement) {
  const result = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
  return result.violations.map((violation) => violation.id);
}

describe("ContentView", () => {
  it("muestra el contexto, la tabla con encabezados, el enunciado y las opciones", () => {
    render(<ContentView {...SELECTION} />);

    expect(screen.getByRole("heading", { name: "Préstamo de equipos" })).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((cell) => cell.textContent),
    ).toEqual(["Usuario", "Plazo"]);
    const options = screen.getByRole("list", { name: "Opciones" });
    expect(within(options).getAllByRole("listitem")).toHaveLength(2);
    expect(options).toHaveTextContent("A3 días");
  });

  it("las fórmulas llevan MathML para los lectores de pantalla", () => {
    const { container } = render(<ContentView {...SELECTION} />);

    expect(container.querySelector("math")).not.toBeNull();
    expect(container.querySelector("annotation")?.textContent).toBe("x^2 = 9");
  });

  it("no renderiza HTML crudo del contenido", () => {
    const { container } = render(
      <ContentView
        {...SELECTION}
        stem_md={'Hola <script>alert(1)</script><img src=x onerror="alert(1)"> mundo'}
      />,
    );

    // Las etiquetas se descartan; su texto queda como texto inerte.
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.innerHTML).not.toContain("onerror");
    expect(container).toHaveTextContent(/Hola .* mundo/);
  });

  it("sin retroalimentación no revela la respuesta", () => {
    render(<ContentView {...SELECTION} />);

    expect(screen.queryByText(/Correcto: lo dice la tabla/)).toBeNull();
    expect(screen.queryByText(/La tabla indica/)).toBeNull();
  });

  it("con retroalimentación muestra la de cada opción, cuál es correcta y la explicación", () => {
    render(<ContentView {...SELECTION} showFeedback />);

    const options = within(screen.getByRole("list", { name: "Opciones" })).getAllByRole("listitem");
    expect(options[0]).toHaveTextContent("Respuesta correcta");
    expect(options[0]).toHaveTextContent("Correcto: lo dice la tabla.");
    expect(options[1]).toHaveTextContent("Ese es el plazo de docentes.");
    expect(options[1]).not.toHaveTextContent("Respuesta correcta");
    expect(screen.getByRole("region", { name: "Explicación" })).toHaveTextContent(
      "La tabla indica el plazo por tipo de usuario.",
    );
  });

  it("una imagen del contexto se muestra con su texto alternativo", () => {
    render(
      <ContentView
        kind="selection"
        context={{
          kind: "image",
          title: "Aviso",
          image: { src: "/api/v1/content/media/1", alt: "Aviso de silencio en la biblioteca" },
        }}
        stem_md="Where can you see this notice?"
        options={[{ key: "A", text: "Library", correct: true, feedback: "" }]}
      />,
    );

    expect(screen.getByRole("img", { name: "Aviso de silencio en la biblioteca" })).toHaveAttribute(
      "src",
      "/api/v1/content/media/1",
    );
  });

  it("un emparejamiento usa las opciones compartidas del contexto", () => {
    render(
      <ContentView
        kind="matching"
        context={{
          kind: "shared_options",
          title: "Part 1",
          body_md: "Match the descriptions with the words.",
          shared_options: [
            { key: "G", text: "library", feedback: "Ya se usó en el ejemplo." },
            { key: "H", text: "wallet", feedback: "La billetera." },
          ],
        }}
        stem_md="1. You use this to keep money."
        answer_key="H"
        showFeedback
      />,
    );

    const options = within(screen.getByRole("list", { name: "Opciones" })).getAllByRole("listitem");
    expect(options.map((option) => option.textContent?.slice(0, 1))).toEqual(["G", "H"]);
    expect(options[1]).toHaveTextContent("Respuesta correcta");
  });

  it("una consigna muestra su contexto y su pregunta, sin opciones", () => {
    render(
      <ContentView
        kind="writing_prompt"
        prompt_context_md="Varias universidades evalúan permitir la IA."
        stem_md="¿Está de acuerdo? Escriba un texto argumentativo."
      />,
    );

    expect(screen.getByText(/Varias universidades/)).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Opciones" })).toBeNull();
  });

  it("no tiene violaciones de accesibilidad", async () => {
    const { container } = render(<ContentView {...SELECTION} showFeedback />);

    expect(await violations(container)).toEqual([]);
  });
});
