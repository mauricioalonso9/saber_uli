# Quickstart: Banco de ítems

**Feature**: `002-banco-items` | **Plan**: [plan.md](./plan.md) |
**Contrato**: [contracts/openapi.yaml](./contracts/openapi.yaml) |
**Modelo**: [data-model.md](./data-model.md)

Cómo levantar el entorno con el banco cargado y validar la funcionalidad de punta a punta. El
entorno base (Docker, `.env`, Entra ID simulado, Mailpit) es el de
[001/quickstart.md](../001-identidad-acceso/quickstart.md); aquí solo se agrega lo propio de 002.

## 1. Requisitos previos

- Los de 001 (Docker Desktop o Docker Engine con Compose v2, uv y Node.js 24).
- Dos cuentas con rol Administrador y una con rol Docente, para probar la revisión (FR-012).
  En desarrollo:

  ```bash
  docker compose exec api saber-uli identity grant-admin --email admin1@unilibre.edu.co
  docker compose exec api saber-uli identity grant-admin --email admin2@unilibre.edu.co
  ```

  El rol Docente se asigna en `/admin/usuarios`.

## 2. Levantar el entorno

```bash
docker compose up -d --build --wait
docker compose logs migrate | grep content_seed_loaded
```

El servicio `migrate` ejecuta Alembic y después `saber-uli content load-seed`. En la primera
carga, el log `content_seed_loaded` informa:

- 5 módulos, la taxonomía y 1 rúbrica;
- 8 contextos;
- 46 ítems: 43 de selección y emparejamiento y 3 consignas, todos En revisión con origen `ai`.

Al repetir `docker compose up`, la carga informa 0 agregados y 0 versionados (SC-002).

Carga manual o con otro archivo (por ejemplo, para probar un banco inicial actualizado):

```bash
docker compose run --rm migrate saber-uli content load-seed --file /app/seeds/banco_inicial_saber_uli.json
```

Si el archivo tiene errores, el comando termina con código 1 y no aplica nada (FR-023).

## 3. Pruebas automatizadas

```bash
# Backend: unitarias del dominio content e integración con PostgreSQL 18 real
cd backend
uv run pytest tests/unit/content tests/integration/content

# Esquema del formato de intercambio: falla si backend/schemas/banco_items.schema.json
# no coincide con los modelos (research R-03)
uv run pytest tests/unit/content/test_interchange_schema.py

# Contrato de 002 (Schemathesis sobre las 35 operaciones de contracts/openapi.yaml)
uv run pytest tests/contract/test_content_contract.py

# Metas de rendimiento con 500 y 10 000 ítems (se miden siempre; se exigen con la variable)
PERF_BUDGETS_ENFORCE=1 uv run pytest tests/integration/content/test_performance_budgets.py

# Frontend
cd ../frontend
npm run api:generate      # orval: src/api (001) y src/api/content (002)
npm run lint && npm run typecheck && npm test

# Extremo a extremo y accesibilidad (stack con perfil e2e, como en 001)
npm run test:e2e -- tests/e2e/content-*.spec.ts
```

## 4. Escenarios de validación

Cada escenario indica la historia o el requisito que comprueba. "Docente" y "Admin1"/"Admin2"
son las cuentas del paso 1.

| # | Escenario | Pasos | Resultado esperado |
|---|-----------|-------|--------------------|
| B1 | Banco inicial cargado (US1, SC-001) | Despliegue desde cero → `/banco` como Docente | 46 ítems En revisión con origen "IA"; 8 contextos; la tabla de LC-CTX-003 y las fórmulas se ven bien en la vista previa |
| B2 | Recarga sin cambios (US1, FR-022, SC-002) | Admin1 edita LC-0001 y lo envía a revisión → `docker compose run --rm migrate saber-uli content load-seed` | El resumen dice 0 agregados y 0 versionados; LC-0001 conserva la edición |
| B3 | Banco inicial actualizado (US1, FR-021, FR-022a) | Copiar el archivo, agregar un ítem `LC-9001`, cambiar el enunciado de `LC-0002` y de `LC-0001` (que tiene versión abierta) → cargar con `--file` | `LC-9001` entra En revisión; `LC-0002` recibe una versión nueva En revisión; `LC-0001` aparece en `pending_manual` y no cambia |
| B4 | Archivo del banco con errores (FR-023) | Cargar una copia con un ítem de LC con dos opciones correctas | Código de salida 1; el error nombra el ítem y la regla `single_correct_option`; no se aplica nada |
| B5 | Aprobación por otro administrador (US2, FR-013, FR-014) | Admin1 abre `/banco/revision` → aprueba RC-0001 marcando las dos confirmaciones | Pasa a Publicado; la historia registra a Admin1, la fecha y las confirmaciones |
| B6 | Sin autoaprobación (FR-012) | Admin1 edita CC-0001 y lo envía → intenta aprobarlo | 403 `self-approval-forbidden`; la interfaz dice que lo debe aprobar otro administrador; Admin2 sí puede |
| B7 | Docente no revisa (FR-013) | Docente abre un ítem En revisión | No ve aprobar, devolver ni rechazar; `POST …/approval` responde 403 `forbidden`; puede comentar |
| B8 | Devolver y rechazar (US2) | Admin2 devuelve LC-0003 con un comentario → Docente lo corrige y lo envía → Admin2 rechaza LC-0004 con un motivo | LC-0003 vuelve a Borrador con el comentario visible y luego a En revisión; LC-0004 queda Retirado con el motivo, sin haberse publicado |
| B9 | Versión nueva de lo publicado (US3, FR-015) | Docente edita RC-0001 (Publicado) → envía → Admin2 aprueba | Durante la revisión, la versión 1 sigue Publicada; al aprobar, la versión 2 queda Publicada y la 1 Retirada (`superseded`) |
| B10 | Validaciones del editor (US3, FR-024, FR-007, FR-009) | Crear un ítem de LC sin retroalimentación en una opción; pegar un texto de 501 palabras en un contexto; subir una imagen sin texto alternativo | No se puede enviar ni guardar en cada caso; el error aparece junto al campo con el conteo 501/500 |
| B11 | Vista previa móvil (US3, FR-025) | Abrir la vista previa de ING-0001 (parte 1) y de LC-0007 (tabla de LC-CTX-003) | Marco de 360 × 800 px con contexto, enunciado, opciones y la retroalimentación de cada una; axe sin violaciones |
| B12 | Contexto compartido (FR-020, FR-026) | Con ING-0001 Publicado, editar ING-CTX-P1-001 | Antes de confirmar dice cuántos ítems lo usan y cuántos están Publicados; al confirmar, los publicados reciben versión nueva En revisión |
| B13 | Edición simultánea (FR-027) | Abrir LC-0005 en dos navegadores → guardar en ambos | El segundo recibe "Otra persona cambió este ítem" con ambas versiones; no se pierde ningún cambio |
| B14 | Importación con errores (US4, FR-030 a FR-034) | Descargar la plantilla → llenar 20 filas válidas y 3 inválidas → subirla | Vista previa: 20 nuevos y 3 con error, con campo y regla; el reporte se descarga; al confirmar En revisión con la declaración, entran 20 |
| B15 | Duplicado (FR-032) | Subir un JSON con un ítem igual a LC-0001 pero con otro código | Marcado `duplicate_item`; no se importa |
| B16 | Actualización en lote (US5, FR-035, SC-008) | Exportar RC en JSON → cambiar el enunciado de 3 ítems → importar → confirmar | Vista previa: 3 actualizaciones con diferencias y el resto "sin cambios"; solo esos 3 reciben versión nueva; reimportar el mismo archivo da 0 cambios |
| B17 | Plantilla y tipos no soportados (FR-029) | Exportar Inglés en XLSX | El archivo tiene las partes 2 a 7; `X-Skipped-Items` y la interfaz informan los ítems de la parte 1 que quedaron fuera |
| B18 | Cobertura (US7, FR-039) | Publicar algunos ítems → `/banco/cobertura` → Inglés | Cada parte con publicados, En revisión, porcentaje, peso objetivo y "Faltan N"; las que están bajo el objetivo se distinguen sin depender del color |
| B19 | Estadísticas sin datos (US8, FR-042) | Abrir las estadísticas de RC-0001 | "Aún no hay datos suficientes" (sin respuestas hasta 003) |
| B20 | Taxonomía (US9, FR-045) | Admin1 crea una evidencia nueva → la usa en un ítem → intenta borrarla → la desactiva | Borrar responde `taxonomy-node-in-use`; desactivada no aparece al crear ítems y el ítem sigue válido; un Docente no ve `/admin/taxonomia` |
| B21 | Historia y auditoría (FR-018, FR-047) | Abrir la historia de RC-0001 → intentar `UPDATE content.item_events` con el rol `saber_app` | Versiones y eventos con autor, revisor y fechas; el `UPDATE` responde `permission denied` |
| B22 | Escala (SC-009, SC-010) | `test_performance_budgets.py` con 10 000 ítems | Búsqueda, filtros, cobertura y estadísticas en menos de 2 s; exportación completa en menos de 1 minuto |
| B23 | Logs sin datos personales (principio V) | Revisar `docker compose logs api worker` tras B5–B17 | Solo códigos, conteos e identificadores; sin textos de ítems, nombres de archivo, correos ni nombres |

## 5. Diferencias encontradas en la implementación

- **Comandos en Windows**: en Git Bash, los comandos con rutas del contenedor (`/app/...`) se
  ejecutan con `MSYS_NO_PATHCONV=1`; en PowerShell funcionan tal cual.
- **B17**: la plantilla deja fuera, además de la parte 1 de Inglés, las consignas de Comunicación
  escrita y los ítems cuyo contexto no es de texto (imagen, tabla u opciones compartidas). En el
  banco inicial, LC-CTX-003 es una tabla: LC-0007 y LC-0008 se exportan solo en JSON.
- **Plantilla XLSX**: tiene la columna opcional `contexto_subtipo` (al final) para no perder el
  subtipo de los textos de Lectura crítica al reimportar. Una plantilla anterior sin esa columna
  se sigue leyendo.
- **Códigos**: los de un archivo importado deben tener el formato de la API (`LC-0001`,
  `ING-CTX-P1-001`); otro código es un error de esa entrada.
- **B19 y B20**: las estadísticas y la taxonomía están en la página de cada ítem y en
  `/admin/taxonomia`. La lista del banco con filtros (`/banco`), incluido el filtro de señales de
  problema, sigue pendiente de una tarea (decisión pendiente en T095 y T101); la API ya filtra
  (`listItems?signal=…`).
- **WebKit**: como en 001, los e2e en `iphone-14` necesitan `127.0.0.1 oidc` en el archivo hosts y
  `E2E_OIDC_RESOLVES=1`.

## 6. Notas para producción

- El banco inicial se actualiza con cada versión de la aplicación que traiga un archivo nuevo. El
  resumen de la carga queda en `content.seed_loads` y en el log de `migrate`. Los códigos en
  `pending_manual` se deben revisar a mano.
- Antes de abrir la práctica (003), un administrador de cada área debe revisar y aprobar los ítems
  del banco inicial (constitución VI).
