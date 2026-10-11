import { useId, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/shared/ui/button";

/** Búsqueda de un listado: se aplica al enviar, no con cada tecla. */
export function SearchBox({
  value,
  onSearch,
  hint,
}: {
  value: string;
  onSearch: (text: string) => void;
  hint?: string;
}) {
  const { t } = useTranslation();
  const id = useId();
  const [text, setText] = useState(value);
  return (
    <form
      role="search"
      className="flex flex-wrap items-end gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        onSearch(text.trim());
      }}
    >
      <div>
        <label htmlFor={id} className="font-medium">
          {t("search.label")}
        </label>
        <input
          id={id}
          type="search"
          maxLength={100}
          className="mt-1 block h-11 w-64 rounded-md border border-input bg-background px-3"
          value={text}
          aria-describedby={hint ? `${id}-hint` : undefined}
          onChange={(event) => setText(event.target.value)}
        />
        {hint ? (
          <p id={`${id}-hint`} className="mt-1 text-sm text-muted-foreground">
            {hint}
          </p>
        ) : null}
      </div>
      <Button type="submit" variant="outline">
        {t("search.submit")}
      </Button>
    </form>
  );
}
