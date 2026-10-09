import type { ReactNode } from "react";

/**
 * Contenedor de una tabla que se desplaza en horizontal en el celular. Recibe el foco del teclado
 * para desplazarla con las flechas (WCAG 2.1.1; axe scrollable-region-focusable) y se anuncia
 * con el mismo nombre que la tabla.
 */
export function ScrollRegion({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div
      role="region"
      aria-label={label}
      // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- región desplazable
      tabIndex={0}
      className="overflow-x-auto rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {children}
    </div>
  );
}
