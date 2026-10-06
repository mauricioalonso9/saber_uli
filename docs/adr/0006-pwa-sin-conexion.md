# ADR 0006: PWA con práctica sin conexión

- **Estado**: Aceptado
- **Fecha**: 2026-10-05
- **Origen**: `specs/001-identidad-acceso/plan.md`, research R-17, R-33 y R-34

## Contexto

La experiencia principal es una PWA instalable en celulares de gama media que debe tolerar
conexiones intermitentes (principio VIII). La spec 001 fija 7 días de uso sin conexión y la
revalidación del acceso antes de sincronizar (FR-038, FR-039); la spec 003 agregará lecciones
descargadas y respuestas pendientes.

## Decisión

- React + TypeScript + Vite con `vite-plugin-pwa` (Workbox): *precache* del shell de la app,
  manifest con íconos y guía de "Agregar a pantalla de inicio" para iPhone.
- IndexedDB con Dexie para datos sin conexión: en 001, instantánea de la cuenta y la marca
  `lastValidatedAt`; en 003, lecciones y cola de respuestas con claves de idempotencia.
- Regla de acceso sin conexión: se permite mientras `ahora − lastValidatedAt ≤ 7 días`.
- Al reconectar, la cola **primero** renueva la sesión y consulta `/api/v1/me`; solo sincroniza
  si el acceso y la autorización de datos siguen vigentes.
- Nginx sirve `sw.js` y el manifest sin caché y con `Service-Worker-Allowed: /`; producción
  siempre con HTTPS.

## Consecuencias

- La revocación hecha mientras el dispositivo está sin red tarda como máximo 7 días en
  aplicarse en ese dispositivo, pero nunca se aceptan datos sin revalidar.
- Las pruebas extremo a extremo incluyen modo avión y viewport móvil.

## Alternativas descartadas

- **Aplicaciones nativas**: requieren tiendas y dos bases de código.
- **Tokens de acceso de larga duración para trabajar sin red**: impiden revocar con conexión.
