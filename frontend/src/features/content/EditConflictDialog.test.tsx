/**
 * T054: conflicto de edición (412; FR-027, R-09). Muestra los cambios propios y la versión
 * actual; la persona decide si conserva los suyos (sobre la revisión actual) o los descarta.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EditConflictDialog } from "@/features/content/EditConflictDialog";
import { item, version } from "@/features/content/testing";

const mine = { ...version().content, stem_md: "Mi enunciado corregido" };
const current = item({
  revision: 7,
  open: version({ content: { ...version().content, stem_md: "Enunciado de la otra persona" } }),
});

describe("conflicto de edición", () => {
  it("muestra las dos versiones y deja conservar o descartar", async () => {
    const onKeepMine = vi.fn();
    const onDiscard = vi.fn();
    render(
      <EditConflictDialog
        open
        mine={mine}
        current={current}
        onKeepMine={onKeepMine}
        onDiscard={onDiscard}
      />,
    );
    const user = userEvent.setup();

    const dialog = screen.getByRole("dialog", { name: "Otra persona cambió este ítem" });
    expect(
      within(within(dialog).getByRole("region", { name: "Tus cambios" })).getByText(
        "Mi enunciado corregido",
      ),
    ).toBeInTheDocument();
    expect(
      within(within(dialog).getByRole("region", { name: "Versión actual" })).getByText(
        "Enunciado de la otra persona",
      ),
    ).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Conservar mis cambios" }));
    expect(onKeepMine).toHaveBeenCalledOnce();
    await user.click(within(dialog).getByRole("button", { name: "Descartar mis cambios" }));
    expect(onDiscard).toHaveBeenCalledOnce();
  });

  it("cerrado no muestra nada", () => {
    render(
      <EditConflictDialog
        open={false}
        mine={mine}
        current={current}
        onKeepMine={vi.fn()}
        onDiscard={vi.fn()}
      />,
    );

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
