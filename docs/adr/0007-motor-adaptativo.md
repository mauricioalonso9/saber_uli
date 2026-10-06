# ADR 0007: Estrategia del motor adaptativo y del repaso espaciado

- **Estado**: Propuesto (se confirma al planear la spec 005)
- **Fecha**: 2026-10-05
- **Origen**: `specs/001-identidad-acceso/research.md`, R-38

## Contexto

La spec 005 estimará el dominio del estudiante por competencia o afirmación (y por parte en
Inglés) y la dificultad real de cada ítem, seleccionará ítems en la zona de desarrollo y
programará repasos según una curva de olvido, con reglas explicables. Al inicio el banco es
pequeño (43 ítems) y no hay respuestas para calibrar.

## Decisión propuesta

- **Estimación de dominio y dificultad**: calificación tipo Elo por estudiante–afirmación y por
  ítem, actualizada con cada respuesta. Se expone detrás del puerto `ProficiencyEstimator`, de
  modo que pueda reemplazarse por TRI (Rasch o 2PL) cuando cada ítem acumule respuestas
  suficientes para calibrar.
- **Repaso espaciado**: FSRS (librería `fsrs`, licencia MIT).

## Consecuencias

- Funciona desde la primera respuesta y es explicable ("subió porque acertaste un ítem más
  difícil que tu nivel").
- La migración a TRI no cambia los contratos públicos del contexto `learning`.

## Alternativas consideradas

- **SM-2**: más simple, pero con intervalos menos precisos que FSRS para la misma retención.
- **TRI desde el inicio**: exige calibración previa con cientos de respuestas por ítem.
