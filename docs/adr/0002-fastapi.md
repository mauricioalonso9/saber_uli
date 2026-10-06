# ADR 0002: Backend en Python con FastAPI y contrato OpenAPI 3.1

- **Estado**: Aceptado
- **Fecha**: 2026-10-05
- **Origen**: `specs/001-identidad-acceso/plan.md`, research R-05

## Contexto

La decisión de proyecto excluye PHP y fija Python para el backend. La constitución (principio
III) exige definir el contrato OpenAPI 3.1 antes de implementar y generar el cliente del
frontend desde él.

## Decisión

- FastAPI + Pydantic v2 sobre Uvicorn, Python 3.13.
- El archivo `contracts/openapi.yaml` de cada especificación es la fuente de verdad. La
  implementación se valida contra él con Schemathesis en CI; el cliente TypeScript se genera con
  `orval`.
- Errores con RFC 9457 (Problem Details) y tipos `urn:saber-uli:problem:<slug>`.
- Los recursos viven en `/api/v1`; los flujos de autenticación por redirección en `/api/auth`
  (la URL de retorno está registrada en Entra ID). Un cambio incompatible crea `/api/v2`.

## Consecuencias

- Validación y documentación automáticas, soporte asíncrono nativo.
- Hay que mantener sincronizados el contrato y los modelos Pydantic: la prueba de contrato lo
  garantiza.

## Alternativas descartadas

- **Django REST Framework**: modelo síncrono y ORM propio, que duplica a SQLAlchemy.
- **Litestar**: técnicamente sólido, pero con comunidad y ecosistema menores.
