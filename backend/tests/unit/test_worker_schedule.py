"""T033: programación de Celery Beat (research R-09)."""

import time
from datetime import timedelta
from pathlib import Path

import pytest
from celery.beat import PersistentScheduler
from celery.schedules import crontab

from saber_uli.worker import HeartbeatScheduler, celery_app

TASKS = {
    "dispatch-outbox": "saber_uli.dispatch_outbox",
    "expire-invitations": "saber_uli.expire_invitations",
    "process-retention": "saber_uli.process_retention",
    "process-deletion-requests": "saber_uli.process_deletion_requests",
    "purge-expired-auth-artifacts": "saber_uli.purge_expired_auth_artifacts",
}


def entry(name: str) -> dict[str, object]:
    schedule: dict[str, dict[str, object]] = celery_app.conf.beat_schedule
    return schedule[name]


def test_zona_horaria_de_bogota() -> None:
    assert celery_app.conf.timezone == "America/Bogota"
    assert celery_app.conf.enable_utc is True


def test_las_cinco_tareas_programadas_y_registradas() -> None:
    assert set(celery_app.conf.beat_schedule) == set(TASKS)
    for name, task in TASKS.items():
        assert entry(name)["task"] == task
        assert task in celery_app.tasks


def test_dispatch_outbox_cada_5_segundos_y_sin_acumular() -> None:
    assert entry("dispatch-outbox")["schedule"] == timedelta(seconds=5)
    # Si el worker está caído no se acumulan miles de despachos pendientes.
    assert entry("dispatch-outbox")["options"] == {"expires": 5}


def test_expire_invitations_cada_hora() -> None:
    assert entry("expire-invitations")["schedule"] == crontab(minute=0)


def test_process_retention_diaria_a_las_2() -> None:
    assert entry("process-retention")["schedule"] == crontab(hour=2, minute=0)


def test_process_deletion_requests_cada_15_minutos() -> None:
    assert entry("process-deletion-requests")["schedule"] == timedelta(minutes=15)


def test_purge_expired_auth_artifacts_diaria() -> None:
    assert entry("purge-expired-auth-artifacts")["schedule"] == crontab(hour=3, minute=30)


def test_entrega_confiable() -> None:
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_el_scheduler_escribe_el_latido_en_cada_tick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    heartbeat = tmp_path / "beat-heartbeat"
    monkeypatch.setenv("BEAT_HEARTBEAT_FILE", str(heartbeat))
    monkeypatch.setattr(PersistentScheduler, "tick", lambda self, *a, **k: 1.0)
    scheduler = HeartbeatScheduler(app=celery_app, schedule_filename=str(tmp_path / "schedule"))

    assert scheduler.tick() == 1.0
    assert heartbeat.exists()
    assert time.time() - heartbeat.stat().st_mtime < 5
    scheduler.close()
