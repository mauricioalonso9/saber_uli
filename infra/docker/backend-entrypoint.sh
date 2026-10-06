#!/bin/sh
# Punto de entrada de la imagen del backend (T008). El primer argumento elige el servicio; `exec`
# deja el proceso como PID 1 para que reciba las señales de Docker.
set -eu

service="${1:-api}"
[ "$#" -gt 0 ] && shift

case "$service" in
  api)
    # `--factory`: la configuración se lee al crear la app, no al importar el módulo.
    # Logs: cada worker crea la app, que llama a configure_logging (T019) y redirige los
    # loggers de uvicorn al manejador JSON. Solo el proceso supervisor conserva el formato de
    # uvicorn en sus mensajes de arranque.
    exec uvicorn --factory saber_uli.main:create_app --host 0.0.0.0 --port 8000 --workers "${API_WORKERS:-4}" \
      --proxy-headers --forwarded-allow-ips "*" "$@"
    ;;
  worker)
    exec celery -A saber_uli.worker worker --loglevel "${LOG_LEVEL:-INFO}" "$@"
    ;;
  beat)
    # HeartbeatScheduler (T034) toca /tmp/beat-heartbeat en cada ciclo; el health check lo revisa.
    exec celery -A saber_uli.worker beat --loglevel "${LOG_LEVEL:-INFO}" \
      --scheduler saber_uli.worker:HeartbeatScheduler --schedule /tmp/celerybeat-schedule "$@"
    ;;
  migrate)
    exec saber-uli migrate "$@"
    ;;
  *)
    # Cualquier otro comando (por ejemplo `saber-uli grant-admin ...`) se ejecuta tal cual.
    exec "$service" "$@"
    ;;
esac
