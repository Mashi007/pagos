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


def test_liquidado_reinicia_tras_perder_liderazgo(monkeypatch):
    """Shutdown deja el scheduler apagado; el mismo proceso debe poder volver a programar 00:40."""
    created = []

    class FakeSched:
        def __init__(self, timezone=None):
            self.timezone = timezone
            self.running = False
            self.jobs = []
            self.shutdowns = 0
            created.append(self)

        def add_job(self, *args, **kwargs):
            self.jobs.append(kwargs.get("id"))

        def start(self):
            self.running = True

        def shutdown(self, wait=True):
            self.shutdowns += 1
            self.running = False

    monkeypatch.setattr(
        "app.services.liquidado_scheduler.BackgroundScheduler",
        FakeSched,
    )
    from app.services.liquidado_scheduler import LiquidadoScheduler

    sched = LiquidadoScheduler()
    sched.iniciar_scheduler()
    assert created[0].running is True
    assert created[0].jobs == ["actualizar_liquidado_diario"]

    sched.detener_scheduler()
    assert sched.scheduler is None
    assert created[0].running is False
    assert created[0].shutdowns == 1

    sched.iniciar_scheduler()
    assert len(created) == 2
    assert sched.scheduler is created[1]
    assert created[1].running is True
    assert created[1].jobs == ["actualizar_liquidado_diario"]

    sched.iniciar_scheduler()
    assert len(created) == 2


def test_dashboard_cache_reanuda_o_reemplaza_tras_stop(monkeypatch):
    import app.api.v1.endpoints.dashboard as dash

    class FakeThread:
        def __init__(self, target=None, name=None, daemon=None):
            self.target = target
            self._alive = False

        def start(self):
            self._alive = True

        def is_alive(self):
            return self._alive

    monkeypatch.setattr(dash.threading, "Thread", FakeThread)
    prev_thread = dash._dashboard_cache_thread
    prev_stop = dash._dashboard_cache_stop.is_set()
    try:
        vivo = FakeThread()
        vivo._alive = True
        dash._dashboard_cache_thread = vivo
        dash._dashboard_cache_stop.set()

        dash.start_dashboard_cache_refresh()
        assert dash._dashboard_cache_stop.is_set() is False
        assert dash._dashboard_cache_thread is vivo

        muerto = FakeThread()
        muerto._alive = False
        dash._dashboard_cache_thread = muerto
        dash._dashboard_cache_stop.set()

        dash.start_dashboard_cache_refresh()
        assert dash._dashboard_cache_stop.is_set() is False
        assert dash._dashboard_cache_thread is not muerto
        assert dash._dashboard_cache_thread.is_alive() is True
    finally:
        dash._dashboard_cache_thread = prev_thread
        if prev_stop:
            dash._dashboard_cache_stop.set()
        else:
            dash._dashboard_cache_stop.clear()
