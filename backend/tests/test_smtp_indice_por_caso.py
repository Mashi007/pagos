from app.core.email_cuentas import (
    ASIGNACION_DEFAULT,
    indice_cuenta_para_tipo_caso_notificacion,
)


def test_dia_siguiente_cuenta_distinta_de_prejudicial():
    a = ASIGNACION_DEFAULT
    assert indice_cuenta_para_tipo_caso_notificacion("PREJUDICIAL", a) == 3
    assert indice_cuenta_para_tipo_caso_notificacion("PAGO_1_DIA_ATRASADO", a) == 4
    assert indice_cuenta_para_tipo_caso_notificacion("PAGO_10_DIAS_ATRASADO", a) == 4
    assert indice_cuenta_para_tipo_caso_notificacion("COBRANZAS_EXCEL", a) == 3
