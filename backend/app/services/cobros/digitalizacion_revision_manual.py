"""
Digitalización incompleta / imagen compleja → revisión manual (sin truncar el archivo).
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any, Optional, Tuple

from app.services.cobros.pago_reportado_documento import reportado_tiene_serial_banco
from app.services.institucion_bancaria_requerida import es_institucion_bancaria_valida
from app.services.pagos_gmail.parse_campos_comprobante import ocr_borroso_indicado_en_texto

# Staff (escáner interno): puede completar campos manualmente.
MSG_REVISION_MANUAL_BASE_STAFF = (
    "Comprobante complejo o ilegible: no se pudo digitalizar con consistencia. "
    "Pase a revisión manual, complete los campos y guarde. "
    "El archivo no se trunca: el comprobante queda en borrador/servidor para continuar."
)

# Público / genérico: no pedir al cliente que complete campos (integridad cobranza).
MSG_REVISION_MANUAL_BASE = (
    "Comprobante complejo o ilegible: no se pudo digitalizar con consistencia. "
    "El reporte se enviará a revisión manual. "
    "El archivo no se trunca: el comprobante queda en borrador/servidor para continuar."
)

MSG_REVISION_MANUAL_CALIDAD = (
    "La calidad de la imagen no permite leer el comprobante con certeza. "
    "El reporte se enviará a revisión manual."
)


def es_institucion_binance_digitalizacion(institucion: Optional[str]) -> bool:
    return "binance" in (institucion or "").strip().lower()


def campos_criticos_faltantes_digitalizacion(
    *,
    fecha_pago: Any,
    institucion_financiera: Optional[str],
    numero_operacion: Optional[str],
    monto: Any,
) -> Tuple[str, ...]:
    """Nombres de campos críticos ausentes o inválidos tras OCR.

    Binance Pay no imprime fecha: no exige fecha (se usa hoy Caracas en el flujo).
    """
    faltan: list[str] = []
    es_binance = es_institucion_binance_digitalizacion(institucion_financiera)
    if not es_binance and not isinstance(fecha_pago, date):
        faltan.append("fecha")
    if not es_institucion_bancaria_valida(institucion_financiera):
        faltan.append("institución bancaria")
    if not reportado_tiene_serial_banco(
        SimpleNamespace(numero_operacion=numero_operacion, referencia_interna="")
    ):
        faltan.append("número de operación")
    if monto is None:
        faltan.append("monto")
    return tuple(faltan)


def mensaje_revision_manual_digitalizacion_incompleta(
    faltan: Tuple[str, ...],
) -> str:
    if not faltan:
        return MSG_REVISION_MANUAL_BASE
    lista = ", ".join(faltan)
    return (
        f"{MSG_REVISION_MANUAL_BASE} "
        f"Campos no digitalizados: {lista}."
    )


def fusionar_mensaje_revision(
    actual: Optional[str],
    nuevo: str,
) -> str:
    a = (actual or "").strip()
    n = (nuevo or "").strip()
    if not a:
        return n
    if not n or n in a:
        return a
    return f"{a} {n}".strip()


def digitalizacion_requiere_revision_manual(
    *,
    fecha_pago: Any,
    institucion_financiera: Optional[str],
    numero_operacion: Optional[str],
    monto: Any,
    notas_modelo: Any = None,
) -> Optional[str]:
    """
    Si faltan campos críticos tras OCR o el modelo indica campos borrosos
    (calidad de imagen insuficiente), devuelve mensaje de revisión manual.
    Si está completo y legible, None.

    Binance: ignora indicios de «fecha borrosa» en notas (la captura no trae fecha)
    y no exige fecha como campo crítico.
    """
    es_binance = es_institucion_binance_digitalizacion(institucion_financiera)
    if ocr_borroso_indicado_en_texto(
        notas_modelo,
        ignorar_fecha=es_binance,
    ):
        return MSG_REVISION_MANUAL_CALIDAD
    faltan = campos_criticos_faltantes_digitalizacion(
        fecha_pago=fecha_pago,
        institucion_financiera=institucion_financiera,
        numero_operacion=numero_operacion,
        monto=monto,
    )
    if not faltan:
        return None
    return mensaje_revision_manual_digitalizacion_incompleta(faltan)
