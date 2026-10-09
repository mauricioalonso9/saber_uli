/**
 * T054: vista previa del ítem tal como lo verá el estudiante en el celular (FR-025, R-17).
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ItemPreview } from "@/features/content/ItemPreview";
import { version } from "@/features/content/testing";

const content = version().content;

describe("vista previa", () => {
  it("muestra el ítem en un marco de 360 × 800 sin revelar la respuesta", () => {
    render(
      <ItemPreview
        kind="selection"
        content={content}
        context={{ kind: "text", title: "Desconectar", body_md: "Texto del contexto." }}
      />,
    );

    const frame = screen.getByRole("region", { name: "Vista en un celular de 360 × 800" });
    expect(frame).toHaveStyle({ width: "360px", height: "800px" });
    expect(within(frame).getByText("Texto del contexto.")).toBeInTheDocument();
    expect(within(frame).getByText(content.options![0].text)).toBeInTheDocument();
    expect(within(frame).queryByText(content.options![0].feedback)).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Vista previa" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("la pestaña Retroalimentación muestra la de cada opción y la explicación", async () => {
    render(<ItemPreview kind="selection" content={content} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("tab", { name: "Retroalimentación" }));

    const panel = screen.getByRole("tabpanel", { name: "Retroalimentación" });
    for (const option of content.options!) {
      expect(within(panel).getByText(option.feedback)).toBeInTheDocument();
    }
    expect(within(panel).getByText(content.explanation_md)).toBeInTheDocument();
  });
});
