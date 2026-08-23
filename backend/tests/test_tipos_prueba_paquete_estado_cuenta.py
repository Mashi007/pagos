"""ESTADO_CUENTA debe aceptar diagnostico/prueba de paquete (sin Carta_Cobranza)."""
from app.services.notificaciones_prueba_paquete import TIPOS_PRUEBA_PAQUETE


def test_estado_cuenta_en_tipos_prueba_paquete():
    assert "ESTADO_CUENTA" in TIPOS_PRUEBA_PAQUETE
