# ADR 0004: Eventos de dominio con outbox transaccional y Celery

- **Estado**: Aceptado
- **Fecha**: 2026-10-05
- **Origen**: `specs/001-identidad-acceso/plan.md`, research R-08, R-09 y R-19

## Contexto

Varias reacciones deben ocurrir si y solo si la transacción que las origina se confirma: enviar
el correo de invitación, emitir enlaces de acceso, suprimir datos y, en especificaciones
futuras, otorgar XP al completar una lección. Además hay tareas programadas (conservación de
datos, vencimientos, rachas, ligas).

## Decisión

- Bus de eventos en proceso para reacciones dentro de la misma transacción.
- Tabla `shared.outbox_events` escrita en la misma transacción que el cambio de negocio. Sus
  payloads llevan solo identificadores: nunca datos personales ni tokens.
- Celery (worker) + Celery Beat sobre Redis. La tarea `dispatch_outbox` (cada 5 s) reclama
  eventos con `FOR UPDATE SKIP LOCKED`, los despacha y los marca como procesados, con reintentos
  y espera exponencial. Los manejadores son idempotentes por `event_id`.
- Los secretos de un solo uso (enlaces de acceso) los genera el manejador en el worker, de modo
  que nunca quedan guardados en claro.

## Consecuencias

- Entrega al menos una vez, sin pérdida de eventos aunque un proceso caiga.
- Latencia de hasta unos segundos para efectos asíncronos (aceptable: SC-007 pide 2 minutos).
- Hay que vigilar el tamaño de la tabla: los eventos procesados se purgan a los 7 días.

## Alternativas descartadas

- **Publicar a Celery después del commit**: se pierden eventos si el proceso cae entre ambos.
- **LISTEN/NOTIFY**: no persiste si no hay oyente.
- **Broker dedicado (Kafka, RabbitMQ)**: infraestructura adicional sin necesidad.
