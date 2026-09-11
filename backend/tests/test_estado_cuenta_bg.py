# -*- coding: utf-8 -*-
from app.services import estado_cuenta_notificacion_envio as ec


def test_lanzar_estado_cuenta_en_bg_omits_if_job_activo(monkeypatch):
    monkeypatch.setattr(
        "app.services.notificaciones_envio_bg_runner.job_activo",
        lambda clave: True,
    )
    spawned = []

    def _spawn(*a, **k):
        spawned.append(a)
        return True

    monkeypatch.setattr(
        "app.services.notificaciones_envio_bg_runner.spawn_envio_bg",
        _spawn,
    )
    assert ec.lanzar_estado_cuenta_en_bg(origen="cron") is False
    assert spawned == []


def test_lanzar_estado_cuenta_en_bg_spawns(monkeypatch):
    monkeypatch.setattr(
        "app.services.notificaciones_envio_bg_runner.job_activo",
        lambda clave: False,
    )
    spawned = []

    def _spawn(clave, target, *args, **kwargs):
        spawned.append((clave, target, args))
        return True

    monkeypatch.setattr(
        "app.services.notificaciones_envio_bg_runner.spawn_envio_bg",
        _spawn,
    )
    assert ec.lanzar_estado_cuenta_en_bg(origen="cron") is True
    assert spawned[0][0] == ec.CLAVE_BG_ESTADO_CUENTA
    assert spawned[0][1] is ec._worker_cron_estado_cuenta
