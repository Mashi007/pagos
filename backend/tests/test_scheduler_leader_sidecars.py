"""Sidecars del scheduler líder (idempotencia)."""
from app.core.scheduler_leader_sidecars import (
    scheduler_leader_sidecars_active,
    start_scheduler_leader_sidecars_once,
    stop_scheduler_leader_sidecars,
)


def test_sidecars_start_stop_idempotent(monkeypatch):
    calls = {"dash_start": 0, "dash_stop": 0, "liq_start": 0, "liq_stop": 0}

    class FakeLiq:
        def iniciar_scheduler(self):
            calls["liq_start"] += 1

        def detener_scheduler(self):
            calls["liq_stop"] += 1

    monkeypatch.setattr(
        "app.api.v1.endpoints.dashboard.start_dashboard_cache_refresh",
        lambda: calls.__setitem__("dash_start", calls["dash_start"] + 1),
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.dashboard.stop_dashboard_cache_refresh",
        lambda: calls.__setitem__("dash_stop", calls["dash_stop"] + 1),
    )
    fake_liq = FakeLiq()
    monkeypatch.setattr(
        "app.services.liquidado_scheduler.liquidado_scheduler",
        fake_liq,
    )
    stop_scheduler_leader_sidecars()
    assert not scheduler_leader_sidecars_active()

    assert start_scheduler_leader_sidecars_once() is True
    assert scheduler_leader_sidecars_active()
    assert start_scheduler_leader_sidecars_once() is False
    assert calls["dash_start"] == 1
    assert calls["liq_start"] == 1

    stop_scheduler_leader_sidecars()
    assert not scheduler_leader_sidecars_active()
    stop_scheduler_leader_sidecars()
    assert calls["liq_stop"] == 1
    assert calls["dash_stop"] == 1
