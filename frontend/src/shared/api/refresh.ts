import type { QueryClient, QueryKey } from "@tanstack/react-query";

/**
 * Vuelve a pedir los datos tras un cambio. `invalidateQueries` no cancela la primera carga de
 * una consulta que aún no tiene datos: si la persona guarda antes de que termine, esa carga (ya
 * desactualizada) sería la que se muestra. Por eso se cancela antes de invalidar.
 */
export async function refreshQueries(queryClient: QueryClient, queryKey: QueryKey): Promise<void> {
  await queryClient.cancelQueries({ queryKey });
  await queryClient.invalidateQueries({ queryKey });
}
