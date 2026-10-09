/**
 * Prueba de humo de la herramienta (T004): Vitest + jsdom + Testing Library + user-event
 * funcionan y los componentes base de shadcn/ui son utilizables.
 *
 * No sustituye las pruebas funcionales de T060 y siguientes.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

describe("cadena de herramientas del frontend", () => {
  it("renderiza e interactúa con los componentes base", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(
      <Card>
        <CardHeader>
          <CardTitle>Prueba de humo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <Label htmlFor="correo">Correo</Label>
          <Input id="correo" name="correo" type="email" />
          <Button type="button" onClick={onClick}>
            Ingresar
          </Button>
        </CardContent>
      </Card>,
    );

    expect(screen.getByText("Prueba de humo")).toBeTruthy();

    await user.type(screen.getByLabelText("Correo"), "estudiante@unilibre.edu.co");
    expect(screen.getByLabelText("Correo")).toHaveProperty("value", "estudiante@unilibre.edu.co");

    await user.click(screen.getByRole("button", { name: "Ingresar" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
