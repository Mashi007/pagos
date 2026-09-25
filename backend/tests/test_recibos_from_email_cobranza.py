"""
Servicio Recibos (/pagos/notificaciones/recibos): remitente "From" fijado a
cobranza@rapicreditca.com (ya verificado como "Enviar como"/Send As en la
cuenta SMTP asignada). Solo cambia el remitente visible del servicio recibos;
no toca la autenticacion SMTP ni otros servicios (cobros, estado_cuenta,
notificaciones).
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import Settings
from app.core import email_config_holder as holder


def test_recibos_from_email_default_es_cobranza():
    """Sin override de entorno, el default apunta a cobranza@rapicreditca.com."""
    s = Settings(
        DATABASE_URL="sqlite:///./test.db",
        SECRET_KEY="test-secret-key-with-32-chars-123456",
    )
    assert s.RECIBOS_FROM_EMAIL == "cobranza@rapicreditca.com"


def test_recibos_from_email_sobreescribible_por_env(monkeypatch):
    """La variable de entorno RECIBOS_FROM_EMAIL sigue pudiendo sobreescribir el default."""
    monkeypatch.setenv("RECIBOS_FROM_EMAIL", "otra@rapicreditca.com")
    s = Settings(
        DATABASE_URL="sqlite:///./test.db",
        SECRET_KEY="test-secret-key-with-32-chars-123456",
    )
    assert s.RECIBOS_FROM_EMAIL == "otra@rapicreditca.com"


def test_get_smtp_config_recibos_usa_from_cobranza(monkeypatch):
    """
    get_smtp_config(servicio='recibos') aplica el From de RECIBOS_FROM_EMAIL
    (cobranza@) sin cambiar smtp_user/smtp_password (autenticacion sigue
    siendo la de la cuenta asignada, p. ej. tucuenta@).
    """
    holder._current.clear()
    holder._cuentas_data.clear()
    holder._current.update(
        {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": "587",
            "smtp_user": "tucuenta@rapicreditca.com",
            "smtp_password": "secret",
            "from_email": "tucuenta@rapicreditca.com",
            "from_name": "RapiCredit",
        }
    )
    monkeypatch.setattr(holder, "sync_from_db", lambda: None)
    from app.core import config as config_module

    monkeypatch.setattr(config_module.settings, "RECIBOS_FROM_EMAIL", "cobranza@rapicreditca.com")

    cfg = holder.get_smtp_config(servicio="recibos")

    assert cfg["from_email"] == "cobranza@rapicreditca.com"
    assert cfg["smtp_user"] == "tucuenta@rapicreditca.com"


def test_get_smtp_config_estado_cuenta_no_afectado_por_recibos_from(monkeypatch):
    """El override de RECIBOS_FROM_EMAIL no debe filtrarse a otros servicios."""
    holder._current.clear()
    holder._cuentas_data.clear()
    holder._current.update(
        {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": "587",
            "smtp_user": "tucuenta@rapicreditca.com",
            "smtp_password": "secret",
            "from_email": "tucuenta@rapicreditca.com",
            "from_name": "RapiCredit",
        }
    )
    monkeypatch.setattr(holder, "sync_from_db", lambda: None)
    from app.core import config as config_module

    monkeypatch.setattr(config_module.settings, "RECIBOS_FROM_EMAIL", "cobranza@rapicreditca.com")

    cfg = holder.get_smtp_config(servicio="estado_cuenta")

    assert cfg["from_email"] == "tucuenta@rapicreditca.com"
