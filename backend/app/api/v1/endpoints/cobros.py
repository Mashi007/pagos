"""
Endpoints de administraciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n del mÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³dulo Cobros (requieren autenticaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n).
Listado de pagos reportados, detalle, aprobar, rechazar, histÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³rico por cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula.
"""
import logging
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from typing import Optional, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_, case

from app.core.database import get_db
from app.core.documento import normalize_documento
from app.core.deps import get_current_user
from app.models.pago_reportado import PagoReportado, PagoReportadoHistorial
from app.models.pago_reportado_exportado import PagoReportadoExportado
from app.models.pago_pendiente_descargar import PagoPendienteDescargar
from app.models.cedula_reportar_bs import CedulaReportarBs
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.services.cobros.recibo_pdf import generar_recibo_pago_reportado, WHATSAPP_LINK, WHATSAPP_DISPLAY
from app.services.cobros.recibo_cuotas_lookup import texto_cuotas_aplicadas_pago_reportado
from app.core.email import send_email
from app.core.email_config_holder import get_email_activo_servicio
from app.api.v1.endpoints.validadores import validate_cedula
from app.api.v1.endpoints.pagos import _aplicar_pago_a_cuotas_interno
from app.services.cobros.pagos_pendiente_descargar_service import obtener_pagos_aprobados_pendientes, vaciar_tabla_pendiente_descargar, obtener_datos_excel

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])

# Mensaje genÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©rico al rechazar: indicar que se comuniquen por WhatsApp (424-4579934)
MENSAJE_RECHAZO_GENERICO = (
    "Su reporte de pago no ha sido aprobado. "
    "Para mÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡s informaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n o aclaratorias, comunÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­quese con nosotros por WhatsApp: {whatsapp} ({link}).\n\n"
    "RapiCredit C.A."
).format(whatsapp=WHATSAPP_DISPLAY, link=WHATSAPP_LINK)


def _referencia_display(referencia_interna: str) -> str:
    ref = (referencia_interna or "").strip()
    if not ref:
        return "-"
    return ref if ref.startswith("#") else f"#{ref}"


def _monto_con_moneda(pr: PagoReportado) -> str:
    monto = getattr(pr, "monto", "")
    moneda = (getattr(pr, "moneda", "") or "").strip()
    monto_str = str(monto).strip()
    return f"{monto_str} {moneda}".strip()


def _generar_recibo_desde_pago(db: Session, pr: PagoReportado) -> bytes:
    cuotas_txt = texto_cuotas_aplicadas_pago_reportado(db, pr)
    saldo_init, saldo_fin, num_cuota = None, None, None
    try:
        from app.services.cobros.recibo_cuotas_lookup import obtener_saldos_cuota_aplicada
        saldo_init, saldo_fin, num_cuota = obtener_saldos_cuota_aplicada(db, pr)
    except Exception:
        pass
    fecha_pago_display = pr.fecha_pago.strftime("%d/%m/%Y") if pr.fecha_pago else None
    moneda = (pr.moneda or "BS").strip().upper()
    tasa_cambio = None
    if moneda == "BS":
        try:
            from app.services.tasa_cambio_service import obtener_tasa_hoy
            tasa_obj = obtener_tasa_hoy(db)
            tasa_cambio = float(tasa_obj.tasa_oficial) if tasa_obj else None
        except Exception:
            pass
    return generar_recibo_pago_reportado(
        referencia_interna=pr.referencia_interna,
        nombres=pr.nombres,
        apellidos=pr.apellidos,
        tipo_cedula=pr.tipo_cedula,
        numero_cedula=pr.numero_cedula,
        institucion_financiera=pr.institucion_financiera,
        monto=_monto_con_moneda(pr),
        numero_operacion=pr.numero_operacion,
        fecha_pago=pr.fecha_pago,
        aplicado_a_cuotas=cuotas_txt,
        saldo_inicial=saldo_init,
        saldo_final=saldo_fin,
        numero_cuota=num_cuota,
        fecha_pago_display=fecha_pago_display,
        moneda=moneda,
        tasa_cambio=tasa_cambio,
    )


def _observacion_solo_columnas(raw: Optional[str]) -> Optional[str]:
    """Devuelve la observaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n mostrando solo nombres de columnas (formato estÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ndar: separador ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºnico ' / '). Si raw ya es lista corta, normaliza separadores; si es texto largo, extrae columnas por palabras clave."""
    if not raw or not (raw := raw.strip()):
        return None
    # Si ya parece lista de columnas (corta, sin frases largas): normalizar a " / "
    if len(raw) <= 80 and not any(x in raw for x in ("en la imagen", "en el formulario", "mientras que", "incluye el", "no coincide")):
        parts = [p.strip() for p in raw.replace(",", " / ").split(" / ") if p.strip()]
        return " / ".join(parts) if parts else raw[:80]
    # Extraer columnas por palabras clave (registros antiguos con texto largo)
    lower = raw.lower()
    columnas = []
    if "cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula" in lower or "cedula" in lower:
        columnas.append("CÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula")
    if "banco" in lower or "instituciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n" in lower or "institucion" in lower or "financiera" in lower:
        columnas.append("Banco")
    if "fecha" in lower and ("pago" in lower or "operaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n" not in lower):
        columnas.append("Fecha pago")
    if "operaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n" in lower or "operacion" in lower or "referencia" in lower or "serial" in lower:
        columnas.append("NÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âº operaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n")
    if "monto" in lower or "cantidad" in lower:
        columnas.append("Monto")
    if "moneda" in lower:
        columnas.append("Moneda")
    return " / ".join(columnas) if columnas else raw[:100]


def _normalize_cedula_for_client_lookup(cedula: str) -> str:
    """Normaliza cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula para comparar con tabla clientes: sin guiÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n/espacios, mayÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºsculas, sin ceros a la izquierda en el nÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºmero (V08752971 -> V8752971)."""
    s = (cedula or "").replace("-", "").replace(" ", "").strip().upper()
    if not s:
        return s
    if len(s) >= 2 and s[0] in ("V", "E", "J", "G") and s[1:].isdigit():
        num = s[1:].lstrip("0") or "0"
        return s[0] + num
    return s


def _cedula_lookup_variants(cedula_norm: str) -> List[str]:
    """Para buscar cliente por cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula: si cedula_norm es V/E/J/G + dÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­gitos, incluir tambiÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©n solo los dÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­gitos (en clientes a veces estÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ solo el nÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºmero)."""
    if not cedula_norm:
        return []
    variants = [cedula_norm]
    if len(cedula_norm) >= 2 and cedula_norm[0] in ("V", "E", "J", "G") and cedula_norm[1:].isdigit():
        variants.append(cedula_norm[1:])
    return variants


def _cedulas_en_clientes_set(db: Session) -> set:
    """
    Devuelve el conjunto de cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dulas que se consideran "en clientes" para la regla NO CLIENTES.
    Incluye la forma normalizada de cada clientes.cedula y, si la cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula en BD es solo dÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­gitos (ej. 20149164),
    tambiÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©n aÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â±ade la variante con prefijo V (V20149164), porque en prÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©stamos/reportes suele usarse V+numero
    y el cliente puede estar guardado solo con el nÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºmero.
    """
    clientes_cedulas = db.execute(select(Cliente.cedula).select_from(Cliente)).scalars().all()
    out = set()
    for cedula in clientes_cedulas:
        if cedula is None:
            continue
        # scalars().all() devuelve valores escalares (str/int), no tuplas
        raw = str(cedula).strip().upper().replace("-", "").replace(" ", "")
        if not raw:
            continue
        norm = _normalize_cedula_for_client_lookup(raw)
        if not norm:
            continue
        out.add(norm)
        # Si en clientes estÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ solo el nÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºmero (con o sin ceros a la izq.), aÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â±adir variante sin ceros y V+numero
        if len(norm) >= 6 and norm.isdigit():
            num = norm.lstrip("0") or "0"
            out.add(num)
            out.add("V" + num)
    return out


def _observacion_reglas_carga(
    db: Session,
    rows: list,
    cedulas_en_clientes: set,
    cedulas_bolivares: set,
    numeros_doc_en_pagos: set,
) -> list:
    """Para cada fila de pagos_reportados, devuelve lista de observaciones por reglas: NO CLIENTES, Monto (Bs no autorizado), DUPLICADO DOC. CÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula normalizada igual que en clientes (sin ceros a la izquierda)."""
    result = []
    for r in rows:
        partes = []
        raw_cedula = ((r.tipo_cedula or "") + (r.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
        cedula_norm = _normalize_cedula_for_client_lookup(raw_cedula)
        if cedula_norm and cedula_norm not in cedulas_en_clientes:
            partes.append("NO CLIENTES")
            # AuditorÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­a: log para diagnosticar por quÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â© se marca NO CLIENTES
            logger.info(
                "[COBROS] NO CLIENTES: ref=%s tipo_cedula=%r numero_cedula=%r raw=%r cedula_norm=%r | set_size=%s V20149164_in_set=%s",
                getattr(r, "referencia_interna", None),
                getattr(r, "tipo_cedula", None),
                getattr(r, "numero_cedula", None),
                raw_cedula,
                cedula_norm,
                len(cedulas_en_clientes),
                "V20149164" in cedulas_en_clientes,
            )
        moneda = (r.moneda or "BS").strip().upper()
        if moneda == "BS" and cedula_norm and cedula_norm not in cedulas_bolivares:
            partes.append("Monto: solo Bs si estÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ en lista BolÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­vares")
        num_op = (r.numero_operacion or "").strip()
        n_doc = normalize_documento(num_op) if num_op else None
        if n_doc and n_doc in numeros_doc_en_pagos:
            partes.append("DUPLICADO DOC")
        result.append(partes)
    return result


@router.get("/pagos-reportados", response_model=dict)
def list_pagos_reportados(
    db: Session = Depends(get_db),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    cedula: Optional[str] = Query(None),
    institucion: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """Lista paginada de pagos reportados con filtros. Por defecto excluye aprobados para mostrar solo casos pendientes."""
    q = select(PagoReportado)
    count_q = select(func.count(PagoReportado.id))
    exportados_subq = select(PagoReportadoExportado.pago_reportado_id)
    if estado:
        q = q.where(PagoReportado.estado == estado)
        count_q = count_q.where(PagoReportado.estado == estado)
    else:
        # Por defecto ocultar aprobados: solo casos pendientes (revisiÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¯ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¿ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â½n, pendiente, rechazado)
        q = q.where(~PagoReportado.estado.in_(("aprobado", "importado")))
        count_q = count_q.where(~PagoReportado.estado.in_(("aprobado", "importado")))

    # Ocultar aprobados ya exportados (persistido en BD).
    q = q.where(~and_(PagoReportado.estado == "aprobado", PagoReportado.id.in_(exportados_subq)))
    count_q = count_q.where(~and_(PagoReportado.estado == "aprobado", PagoReportado.id.in_(exportados_subq)))
    if fecha_desde:
        q = q.where(PagoReportado.created_at >= datetime.combine(fecha_desde, datetime.min.time()))
        count_q = count_q.where(PagoReportado.created_at >= datetime.combine(fecha_desde, datetime.min.time()))
    if fecha_hasta:
        q = q.where(PagoReportado.created_at <= datetime.combine(fecha_hasta, datetime.max.time()))
        count_q = count_q.where(PagoReportado.created_at <= datetime.combine(fecha_hasta, datetime.max.time()))
    # BÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºsqueda por cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula: todas las formas posibles (tipo+numero, solo numero, con/sin guiÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n)
    if cedula:
        ced_clean = cedula.strip().replace("-", "").replace(" ", "").upper()
        # Coincide: concatenaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n tipo+numero, o solo numero_cedula, o tipo
        cond_cedula = or_(
            func.concat(PagoReportado.tipo_cedula, PagoReportado.numero_cedula).like(f"%{ced_clean}%"),
            PagoReportado.numero_cedula.like(f"%{ced_clean}%"),
            func.concat(PagoReportado.tipo_cedula, PagoReportado.numero_cedula) == ced_clean,
            PagoReportado.numero_cedula == ced_clean,
        )
        if len(ced_clean) >= 1 and ced_clean[0:1] in ("V", "E", "J") and ced_clean[1:].isdigit():
            cond_cedula = or_(
                cond_cedula,
                and_(PagoReportado.tipo_cedula == ced_clean[0:1], PagoReportado.numero_cedula == ced_clean[1:]),
            )
        q = q.where(cond_cedula)
        count_q = count_q.where(cond_cedula)
    if institucion:
        q = q.where(PagoReportado.institucion_financiera.ilike(f"%{institucion}%"))
        count_q = count_q.where(PagoReportado.institucion_financiera.ilike(f"%{institucion}%"))

    total = db.execute(count_q).scalar()
    # Rechazados al final de la lista; luego por fecha (mÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡s viejo primero)
    q = q.order_by(
        case((PagoReportado.estado == "rechazado", 1), else_=0),
        PagoReportado.created_at.asc(),
    ).offset((page - 1) * per_page).limit(per_page)
    rows = db.execute(q).scalars().all()

    # Conjuntos para reglas de observaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n al cargar (cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula en clientes, lista Bs, duplicado en pagos).
    # Normalizar cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula igual que en clientes: sin guiÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n/espacios y sin ceros a la izquierda (V08752971 = V8752971).
    cedula_norms = [
        _normalize_cedula_for_client_lookup(
            ((r.tipo_cedula or "") + (r.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
        )
        for r in rows
    ]
    unique_cedulas = set(c for c in cedula_norms if c)
    # Conjunto de cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dulas que existen en clientes (incluye variante V+numero si en BD estÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ solo el nÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºmero)
    cedulas_en_clientes = _cedulas_en_clientes_set(db)
    logger.debug(
        "[COBROS] pagos-reportados: cedulas_en_clientes set_size=%s V20149164_in_set=%s",
        len(cedulas_en_clientes),
        "V20149164" in cedulas_en_clientes,
    )

    cedulas_bolivares = set()
    list_bs = db.execute(select(CedulaReportarBs.cedula)).scalars().all()
    cedulas_bolivares = {
        _normalize_cedula_for_client_lookup((row[0] or "").strip().upper().replace("-", "").replace(" ", ""))
        for row in list_bs if row[0]
    }

    num_ops_raw = list({(r.numero_operacion or "").strip() for r in rows if (r.numero_operacion or "").strip()})
    norms_for_query = {n for o in num_ops_raw for n in [normalize_documento(o)] if n}
    numeros_doc_en_pagos = set()
    if norms_for_query:
        existing_docs = db.execute(
            select(Pago.numero_documento).where(Pago.numero_documento.in_(list(norms_for_query)))
        ).scalars().all()
        numeros_doc_en_pagos = {str(d) for d in existing_docs if d}

    partes_por_fila = _observacion_reglas_carga(
        db, rows, cedulas_en_clientes, cedulas_bolivares, numeros_doc_en_pagos
    )

    items = []
    for i, r in enumerate(rows):
        obs_gemini = _observacion_solo_columnas(r.gemini_comentario)
        partes_reglas = partes_por_fila[i] if i < len(partes_por_fila) else []
        # Orden estÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ndar: reglas (NO CLIENTES, DUPLICADO DOC, Monto...) primero; luego divergencias Gemini (columnas). Un solo separador " / ".
        partes_final = partes_reglas + ([obs_gemini] if obs_gemini else [])
        observacion = " / ".join(partes_final) if partes_final else None
        items.append(PagoReportadoListItem(
            id=r.id,
            referencia_interna=r.referencia_interna,
            nombres=r.nombres,
            apellidos=r.apellidos,
            cedula_display=f"{r.tipo_cedula}{r.numero_cedula}",
            institucion_financiera=r.institucion_financiera,
            monto=float(r.monto),
            moneda=r.moneda or "BS",
            fecha_pago=r.fecha_pago,
            numero_operacion=r.numero_operacion,
            fecha_reporte=r.created_at,
            estado=r.estado,
            gemini_coincide_exacto=r.gemini_coincide_exacto,
            observacion=observacion,
            correo_enviado_a=r.correo_enviado_a,
            tiene_recibo_pdf=bool(r.recibo_pdf),
        ))
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/pagos-reportados/kpis", response_model=dict)
def kpis_pagos_reportados(
    db: Session = Depends(get_db),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    cedula: Optional[str] = Query(None),
    institucion: Optional[str] = Query(None),
):
    """Conteos por estado (pendiente, en_revision, aprobado, rechazado) con los mismos filtros opcionales que el listado."""
    base = select(PagoReportado.estado, func.count(PagoReportado.id).label("cnt")).where(True)
    if fecha_desde:
        base = base.where(PagoReportado.created_at >= datetime.combine(fecha_desde, datetime.min.time()))
    if fecha_hasta:
        base = base.where(PagoReportado.created_at <= datetime.combine(fecha_hasta, datetime.max.time()))
    if cedula:
        ced_clean = cedula.strip().replace("-", "").replace(" ", "").upper()
        cond_cedula = or_(
            func.concat(PagoReportado.tipo_cedula, PagoReportado.numero_cedula).like(f"%{ced_clean}%"),
            PagoReportado.numero_cedula.like(f"%{ced_clean}%"),
            func.concat(PagoReportado.tipo_cedula, PagoReportado.numero_cedula) == ced_clean,
            PagoReportado.numero_cedula == ced_clean,
        )
        if len(ced_clean) >= 1 and ced_clean[0:1] in ("V", "E", "J") and ced_clean[1:].isdigit():
            cond_cedula = or_(
                cond_cedula,
                and_(PagoReportado.tipo_cedula == ced_clean[0:1], PagoReportado.numero_cedula == ced_clean[1:]),
            )
        base = base.where(cond_cedula)
    if institucion:
        base = base.where(PagoReportado.institucion_financiera.ilike(f"%{institucion}%"))
    base = base.group_by(PagoReportado.estado)
    rows = db.execute(base).all()
    counts = {"pendiente": 0, "en_revision": 0, "aprobado": 0, "rechazado": 0, "importado": 0}
    for row in rows:
        if row.estado in counts:
            counts[row.estado] = row.cnt
    counts["total"] = sum(counts[k] for k in ("pendiente", "en_revision", "aprobado", "rechazado", "importado"))
    return counts


@router.get("/pagos-reportados/{pago_id}", response_model=PagoReportadoDetalle)
def get_pago_reportado_detalle(pago_id: int, db: Session = Depends(get_db)):
    """Detalle de un pago reportado + historial de cambios de estado."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    hist = db.execute(
        select(PagoReportadoHistorial)
        .where(PagoReportadoHistorial.pago_reportado_id == pago_id)
        .order_by(PagoReportadoHistorial.created_at.asc())
    ).scalars().all()
    historial = [
        {
            "estado_anterior": h.estado_anterior,
            "estado_nuevo": h.estado_nuevo,
            "usuario_email": h.usuario_email,
            "motivo": h.motivo,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in hist
    ]
    return PagoReportadoDetalle(
        id=pr.id,
        referencia_interna=pr.referencia_interna,
        nombres=pr.nombres,
        apellidos=pr.apellidos,
        tipo_cedula=pr.tipo_cedula,
        numero_cedula=pr.numero_cedula,
        fecha_pago=pr.fecha_pago,
        institucion_financiera=pr.institucion_financiera,
        numero_operacion=pr.numero_operacion,
        monto=float(pr.monto),
        moneda=pr.moneda or "BS",
        ruta_comprobante=pr.ruta_comprobante,
        tiene_comprobante=bool(pr.comprobante),
        tiene_recibo_pdf=bool(pr.recibo_pdf),
        observacion=pr.observacion,
        correo_enviado_a=pr.correo_enviado_a,
        estado=pr.estado,
        motivo_rechazo=pr.motivo_rechazo,
        gemini_coincide_exacto=pr.gemini_coincide_exacto,
        gemini_comentario=pr.gemini_comentario,
        created_at=pr.created_at,
        updated_at=pr.updated_at,
        historial=historial,
    )


def _email_cliente_pago_reportado(db: Session, pr: PagoReportado) -> str:
    """Email del cliente para enviar recibo: pr.correo_enviado_a o, si falta, busqueda por cedula en clientes."""
    to = (pr.correo_enviado_a or "").strip()
    if to and "@" in to:
        return to
    cedula_raw = (f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}").replace("-", "").replace(" ", "").strip().upper()
    if not cedula_raw:
        return ""
    cedula_norm = _normalize_cedula_for_client_lookup(cedula_raw)
    variants = _cedula_lookup_variants(cedula_norm)
    if not variants:
        return ""
    cedula_lookup = func.upper(func.replace(func.replace(Cliente.cedula, "-", ""), " ", ""))
    cliente = db.execute(select(Cliente).where(cedula_lookup.in_(variants))).scalars().first()
    if cliente and (cliente.email or "").strip():
        return (cliente.email or "").strip()
    return ""


def _registrar_historial(db: Session, pago_id: int, estado_anterior: str, estado_nuevo: str, usuario_email: Optional[str], motivo: Optional[str]):
    h = PagoReportadoHistorial(
        pago_reportado_id=pago_id,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        usuario_email=usuario_email,
        motivo=motivo,
    )
    db.add(h)



def _crear_pago_desde_reportado_y_aplicar_cuotas(db: Session, pr: PagoReportado, usuario_email: Optional[str]) -> None:
    """Tras aprobar un pago reportado: crea registro en tabla pagos y aplica a cuotas (FIFO) para que prestamos y estado de cuenta se actualicen. Debe llamarse ANTES de commit; si falla lanza HTTPException."""
    _rechazar_si_numero_operacion_duplicado(db, pr.numero_operacion)
    cedula_norm = _normalize_cedula_for_client_lookup(
        ((pr.tipo_cedula or "") + (pr.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
    )
    if not cedula_norm:
        raise HTTPException(status_code=400, detail="CÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula del reporte vacÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­a; no se puede crear el pago en prÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©stamos.")
    variants = _cedula_lookup_variants(cedula_norm)
    cedula_lookup = func.upper(func.replace(func.replace(Cliente.cedula, "-", ""), " ", ""))
    cliente = db.execute(
        select(Cliente).where(cedula_lookup.in_(variants))
    ).scalars().first()
    if not cliente:
        raise HTTPException(
            status_code=400,
            detail="No se encontrÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³ cliente con la cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula indicada. Verifique la cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula o registre al cliente para que el estado de cuenta se actualice.",
        )
    prestamo = db.execute(
        select(Prestamo)
        .where(Prestamo.cliente_id == cliente.id, func.upper(Prestamo.estado) == "APROBADO")
        .order_by(Prestamo.id.desc())
        .limit(1)
    ).scalars().first()
    if not prestamo:
        raise HTTPException(
            status_code=400,
            detail="El cliente no tiene un prÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©stamo APROBADO activo. No se puede actualizar estado de cuenta.",
        )
    num_doc = ("COB-" + pr.referencia_interna)[:100]
    if db.execute(select(Pago.id).where(Pago.numero_documento == num_doc)).scalar() is not None:
        logger.info("[COBROS] Aprobar ref=%s: ya existe pago con documento %s; omitir creacion (idempotente).", pr.referencia_interna, num_doc)
        return
    fecha_ts = datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now()
    monto = Decimal(str(round(float(pr.monto), 2)))
    if monto <= 0:
        raise HTTPException(status_code=400, detail="El monto del reporte debe ser mayor que cero.")
    row = Pago(
        cedula_cliente=cedula_norm,
        prestamo_id=prestamo.id,
        fecha_pago=fecha_ts,
        monto_pagado=monto,
        numero_documento=num_doc,
        institucion_bancaria=(pr.institucion_financiera or "").strip()[:255] or None,
        estado="PENDIENTE",
        referencia_pago=num_doc,
        usuario_registro=usuario_email or "cobros@rapicredit.com",
        conciliado=True,
        fecha_conciliacion=datetime.now(),
        verificado_concordancia="SI",
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    _aplicar_pago_a_cuotas_interno(row, db)
    row.estado = "PAGADO"
    logger.info("[COBROS] Aprobar ref=%s: creado pago id=%s y aplicado a cuotas del prestamo %s.", pr.referencia_interna, row.id, prestamo.id)


@router.post("/pagos-reportados/{pago_id}/aprobar")
def aprobar_pago_reportado(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Aprueba el pago reportado: genera recibo PDF, envÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­a por correo, guarda en recibos/."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
    if pr.estado == "importado":
        return {"ok": True, "mensaje": "Ya importado a la tabla de pagos."}
    if pr.estado == "aprobado":
        try:
            _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)
            db.commit()
        except HTTPException:
            pass
        return {"ok": True, "mensaje": "Ya estaba aprobado."}
    if pr.estado == "rechazado":
        raise HTTPException(status_code=400, detail="No se puede aprobar un pago rechazado.")
    estado_anterior = pr.estado
    pr.estado = "aprobado"
    pr.motivo_rechazo = None
    
    # Agregar a tabla temporal de descargas
    from app.services.cobros.pagos_pendiente_descargar_service import agregar_a_pendiente_descargar
    agregar_a_pendiente_descargar(db, pr.id)
    pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)

    try:
        _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("[COBROS] Aprobar ref=%s: error al crear pago o aplicar a cuotas: %s", pr.referencia_interna, e)
        raise HTTPException(status_code=500, detail=f"Error al aprobar: {e!s}")
    db.refresh(pr)
    try:
        pdf_bytes = _generar_recibo_desde_pago(db, pr)
    except Exception as e:
        logger.exception("[COBROS] Aprobar ref=%s: error generando recibo PDF: %s", pr.referencia_interna, e)
        raise HTTPException(status_code=500, detail=f"Error al generar el recibo PDF: {e!s}")
    pr.recibo_pdf = pdf_bytes
    to_email = _email_cliente_pago_reportado(db, pr)
    if not pr.correo_enviado_a and to_email:
        pr.correo_enviado_a = to_email
    mensaje_final = "Pago aprobado y recibo enviado por correo."
    if to_email:
        body = f"Su reporte de pago ha sido aprobado. NÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºmero de referencia: {_referencia_display(pr.referencia_interna)}. Adjunto encontrarÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ el recibo.\n\nRapiCredit C.A."
        ok_mail, err_mail = send_email([to_email], f"Recibo de reporte de pago {_referencia_display(pr.referencia_interna)}", body, attachments=[(f"recibo_{pr.referencia_interna}.pdf", pdf_bytes)], servicio="cobros", respetar_destinos_manuales=True)
        if ok_mail:
            logger.info("[COBROS] Aprobar ref=%s: recibo enviado por correo a %s.", pr.referencia_interna, to_email)
        else:
            logger.error(
                "[COBROS] Aprobar ref=%s: correo NO enviado a %s. Error: %s.",
                pr.referencia_interna, to_email, err_mail or "desconocido",
            )
            mensaje_final = "Pago aprobado. El recibo no pudo enviarse por correo; use 'Enviar recibo por correo' desde el detalle."
    _registrar_historial(db, pago_id, estado_anterior, "aprobado", usuario_email, None)
    db.commit()
    return {"ok": True, "mensaje": mensaje_final}


@router.post("/pagos-reportados/{pago_id}/rechazar")
def rechazar_pago_reportado(
  pago_id: int,
  body: AprobarRechazarBody,
  db: Session = Depends(get_db),
  current_user: dict = Depends(get_current_user),
):
    """Rechaza el pago reportado. Motivo obligatorio. EnvÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­a correo al cliente informando que no fue aprobado."""
    if not (body.motivo or "").strip():
        raise HTTPException(status_code=400, detail="El motivo de rechazo es obligatorio.")
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if pr.estado == "rechazado":
        return {"ok": True, "mensaje": "Ya estaba rechazado."}
    estado_anterior = pr.estado
    pr.estado = "rechazado"
    pr.motivo_rechazo = (body.motivo or "").strip()[:2000]
    usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
    pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)

    to_email = _email_cliente_pago_reportado(db, pr)
    notif_activo = get_email_activo_servicio("notificaciones")
    logger.info(
        "[COBROS] Rechazar ref=%s: destino=%s servicio_notificaciones_activo=%s.",
        pr.referencia_interna, to_email or "sin correo", notif_activo,
    )
    if to_email and notif_activo:
        body_text = (
            f"Referencia: {pr.referencia_interna}\n\n"
            f"Su reporte de pago no ha sido aprobado.\n\n"
            f"Motivo del rechazo: {pr.motivo_rechazo}\n\n"
            f"Para mÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡s informaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n o aclaratorias, comunÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­quese con nosotros por WhatsApp: {WHATSAPP_DISPLAY} ({WHATSAPP_LINK}).\n\n"
            "RapiCredit C.A."
        )
        attachments: List[Tuple[str, bytes]] = []
        if pr.comprobante:
            nombre_adj = (pr.comprobante_nombre or "comprobante").strip() or "comprobante"
            if not nombre_adj or "." not in nombre_adj:
                ext = "pdf" if (pr.comprobante_tipo or "").lower().find("pdf") >= 0 else "jpg"
                nombre_adj = f"comprobante_{pr.referencia_interna}.{ext}"
            attachments.append((nombre_adj, bytes(pr.comprobante)))
        ok_mail, err_mail = send_email(
            [to_email],
            f"Reporte de pago no aprobado #{pr.referencia_interna}",
            body_text,
            attachments=attachments if attachments else None,
            servicio="notificaciones",
            respetar_destinos_manuales=True,
        )
        if ok_mail:
            logger.info("[COBROS] Rechazar ref=%s: correo enviado a %s (servicio notificaciones OK).", pr.referencia_interna, to_email)
        else:
            logger.error(
                "[COBROS] Rechazar ref=%s: correo NO enviado a %s. Error: %s.",
                pr.referencia_interna, to_email, err_mail or "desconocido",
            )
    elif to_email and not notif_activo:
        logger.warning("[COBROS] Rechazar ref=%s: servicio notificaciones desactivado, no se enviÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³ correo a %s.", pr.referencia_interna, to_email)
    elif not to_email:
        logger.info("[COBROS] Rechazar ref=%s: no hay correo del cliente, no se enviÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³ notificaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n.", pr.referencia_interna)
    _registrar_historial(db, pago_id, estado_anterior, "rechazado", usuario_email, pr.motivo_rechazo)
    db.commit()
    return {"ok": True, "mensaje": "Pago rechazado y cliente notificado."}


@router.delete("/pagos-reportados/{pago_id}")
def eliminar_pago_reportado(
    pago_id: int,
    db: Session = Depends(get_db),
):
    """Elimina un pago reportado y su historial (CASCADE). AcciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n irreversible."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    ref = pr.referencia_interna
    db.delete(pr)
    db.commit()
    logger.info("[COBROS] Pago reportado eliminado: id=%s ref=%s", pago_id, ref)
    return {"ok": True, "mensaje": f"Pago reportado {ref} eliminado."}


@router.get("/historico-cliente", response_model=dict)
def historico_por_cliente(
    cedula: str = Query(..., min_length=6),
    db: Session = Depends(get_db),
):
    """Lista todos los pagos reportados por un cliente (por cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula). Incluye acceso a recibos PDF."""
    ced_clean = cedula.strip().replace("-", "").replace(" ", "").upper()
    if len(ced_clean) < 6:
        raise HTTPException(status_code=400, detail="CÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula invÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lida.")
    if ced_clean[0:1] in ("V", "E", "J") and ced_clean[1:].isdigit():
        tipo, num = ced_clean[0:1], ced_clean[1:]
        q = select(PagoReportado).where(
            PagoReportado.tipo_cedula == tipo,
            PagoReportado.numero_cedula == num,
        )
    else:
        q = select(PagoReportado).where(PagoReportado.numero_cedula == ced_clean)
    rows = db.execute(q.order_by(PagoReportado.created_at.desc())).scalars().all()
    items = [
        {
            "id": r.id,
            "referencia_interna": r.referencia_interna,
            "fecha_pago": r.fecha_pago.isoformat() if r.fecha_pago else None,
            "fecha_reporte": r.created_at.isoformat() if r.created_at else None,
            "monto": float(r.monto),
            "moneda": r.moneda,
            "estado": r.estado,
            "tiene_recibo": bool(r.recibo_pdf),
        }
        for r in rows
    ]
    return {"cedula": cedula, "items": items}


@router.get("/pagos-reportados/{pago_id}/comprobante")
def get_comprobante(pago_id: int, db: Session = Depends(get_db)):
    """Devuelve el archivo comprobante (imagen o PDF) desde BD."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if not pr.comprobante:
        raise HTTPException(status_code=404, detail="No hay comprobante almacenado.")
    media = (pr.comprobante_tipo or "application/octet-stream").split(";")[0].strip()
    nombre = pr.comprobante_nombre or "comprobante"
    return Response(content=bytes(pr.comprobante), media_type=media, headers={"Content-Disposition": f'inline; filename="{nombre}"'})


@router.get("/pagos-reportados/{pago_id}/recibo.pdf")
def get_recibo_pdf(pago_id: int, db: Session = Depends(get_db)):
    """Devuelve el PDF del recibo regenerado desde el pago reportado."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    pdf_bytes = _generar_recibo_desde_pago(db, pr)
    pr.recibo_pdf = pdf_bytes
    db.commit()
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo_{pr.referencia_interna}.pdf"'},
    )


@router.post("/pagos-reportados/{pago_id}/enviar-recibo")
def enviar_recibo_manual(
    pago_id: int,
    db: Session = Depends(get_db),
):
    """EnvÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­a por correo el recibo PDF del pago (manual). Genera el PDF si no existe y lo guarda en BD."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    to_email = _email_cliente_pago_reportado(db, pr)
    if not to_email:
        raise HTTPException(status_code=400, detail="No hay correo del cliente para este pago. Registre el correo en el detalle del pago o en la ficha del cliente.")
    pdf_bytes = _generar_recibo_desde_pago(db, pr)
    pr.recibo_pdf = pdf_bytes
    db.commit()
    body = (
        f"Recibo de reporte de pago. NÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºmero de referencia: {_referencia_display(pr.referencia_interna)}.\n\n"
        "Adjunto encontrarÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ el recibo.\n\nRapiCredit C.A."
    )
    send_email([to_email], f"Recibo de reporte de pago {_referencia_display(pr.referencia_interna)}", body, attachments=[(f"recibo_{pr.referencia_interna}.pdf", bytes(pdf_bytes))], servicio="cobros", respetar_destinos_manuales=True)
    return {"ok": True, "mensaje": "Recibo enviado por correo."}


class CambiarEstadoBody(BaseModel):
    estado: str  # pendiente | en_revision | aprobado | rechazado
    motivo: Optional[str] = None


class EditarPagoReportadoBody(BaseModel):
    """Campos editables para que el pago cumpla con los validadores (cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula, fecha, monto, etc.)."""
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    tipo_cedula: Optional[str] = None
    numero_cedula: Optional[str] = None
    fecha_pago: Optional[date] = None
    institucion_financiera: Optional[str] = None
    numero_operacion: Optional[str] = None
    monto: Optional[float] = None
    moneda: Optional[str] = None
    correo_enviado_a: Optional[str] = None
    observacion: Optional[str] = None


def _rechazar_si_numero_operacion_duplicado(db: Session, numero_operacion: str) -> None:
    """Si el nÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºmero de operaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n ya existe en tabla pagos (numero_documento), lanza HTTPException 400. Nunca se permite guardar duplicado."""
    num_op = (numero_operacion or "").strip()
    if not num_op:
        return
    existe = db.execute(select(Pago.id).where(Pago.numero_documento == num_op)).scalar() is not None
    if existe:
        raise HTTPException(
            status_code=400,
            detail="NÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºmero de operaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n duplicado. No se permite guardar. Ya existe un pago con ese documento.",
        )


def _normalizar_cedula_editar(tipo: Optional[str], numero: Optional[str]) -> Tuple[str, str]:
    """Devuelve (tipo, numero) normalizados; si solo viene numero con 6-11 dÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­gitos, antepone V."""
    if tipo is None and numero is None:
        return "", ""
    t = (tipo or "").strip().upper()
    n = (numero or "").strip().replace(" ", "").replace("-", "").replace(".", "")
    if not n:
        return t[:1] if t else "", ""
    if t and t in ("V", "E", "J", "G") and n.isdigit() and 6 <= len(n) <= 11:
        return t, n
    if not t and n.isdigit() and 6 <= len(n) <= 11:
        return "V", n
    # Intentar validar como cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula completa
    cedula_input = f"{t}{n}" if t else n
    val = validate_cedula(cedula_input)
    if val.get("valido"):
        formateado = val.get("valor_formateado", "") or cedula_input
        if "-" in formateado:
            a, b = formateado.split("-", 1)
            return a.strip(), b.strip()
        return (formateado[0] if formateado else "V", formateado[1:] if len(formateado) > 1 else n)
    return t[:1] if t else "V", n


@router.patch("/pagos-reportados/{pago_id}")
def editar_pago_reportado(
    pago_id: int,
    body: EditarPagoReportadoBody,
    db: Session = Depends(get_db),
):
    """Edita los datos del pago reportado para que cumplan con los validadores (cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula, fecha, monto, etc.). Solo actualiza los campos enviados."""
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if pr.estado in ("aprobado", "importado"):
        raise HTTPException(status_code=400, detail="No se puede editar un pago ya aprobado o importado a pagos.")
    if pr.estado == "rechazado":
        raise HTTPException(status_code=400, detail="No se puede editar un pago rechazado.")

    if body.nombres is not None:
        pr.nombres = (body.nombres or "").strip()[:200] or pr.nombres
    if body.apellidos is not None:
        pr.apellidos = (body.apellidos or "").strip()[:200] or pr.apellidos
    if body.tipo_cedula is not None or body.numero_cedula is not None:
        t_env = body.tipo_cedula if body.tipo_cedula is not None else pr.tipo_cedula
        n_env = body.numero_cedula if body.numero_cedula is not None else pr.numero_cedula
        tipo, numero = _normalizar_cedula_editar(t_env, n_env)
        if tipo and numero:
            val = validate_cedula(f"{tipo}{numero}")
            if not val.get("valido"):
                raise HTTPException(status_code=400, detail=val.get("error", "CÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula invÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lida."))
            pr.tipo_cedula = tipo
            pr.numero_cedula = numero[:13]
    if body.fecha_pago is not None:
        pr.fecha_pago = body.fecha_pago
    if body.institucion_financiera is not None:
        pr.institucion_financiera = (body.institucion_financiera or "").strip()[:100] or pr.institucion_financiera
    if body.numero_operacion is not None:
        pr.numero_operacion = (body.numero_operacion or "").strip()[:100] or pr.numero_operacion
    if body.monto is not None:
        if body.monto < 0:
            raise HTTPException(status_code=400, detail="El monto no puede ser negativo.")
        pr.monto = body.monto
    if body.moneda is not None:
        m = (body.moneda or "BS").strip().upper()[:10]
        # USDT = DÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³lares = USD = $; normalizar a USD
        if m in ("USD", "USDT"):
            m = "USD"
        pr.moneda = m or pr.moneda
    if body.correo_enviado_a is not None:
        pr.correo_enviado_a = (body.correo_enviado_a or "").strip()[:255] or None
    if body.observacion is not None:
        pr.observacion = (body.observacion or "").strip()[:500] or None

    # NÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºmero de operaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n: nunca permitir duplicado en tabla pagos
    _rechazar_si_numero_operacion_duplicado(db, pr.numero_operacion)

    # Si la moneda queda en BS, la cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula debe estar en la lista de autorizadas para BolÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­vares (misma normalizaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n que en listado)
    moneda_final = (pr.moneda or "").strip().upper()
    if moneda_final == "BS":
        raw_cedula = ((pr.tipo_cedula or "") + (pr.numero_cedula or "")).replace("-", "").replace(" ", "").strip().upper()
        cedula_norm = _normalize_cedula_for_client_lookup(raw_cedula)
        if cedula_norm:
            list_bs_all = db.execute(select(CedulaReportarBs.cedula)).scalars().all()
            cedulas_bs_norm = {
                _normalize_cedula_for_client_lookup((r[0] or "").strip().upper().replace("-", "").replace(" ", ""))
                for r in list_bs_all if r[0]
            }
            permitido_bs = cedula_norm in cedulas_bs_norm
            if not permitido_bs:
                raise HTTPException(
                    status_code=400,
                    detail="ObservaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n: BolÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­vares. No puede guardar con moneda Bs; la cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula no estÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ en la lista autorizada. Cambie a USD.",
                )

    if pr.recibo_pdf:
        pr.recibo_pdf = _generar_recibo_desde_pago(db, pr)
    db.commit()
    logger.info("[COBROS] Pago reportado editado: id=%s ref=%s", pago_id, pr.referencia_interna)
    return {"ok": True, "mensaje": "Datos actualizados. Los cambios cumplen con los validadores."}


@router.patch("/pagos-reportados/{pago_id}/estado")
def cambiar_estado_pago(
    pago_id: int,
    body: CambiarEstadoBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Cambia el estado del pago reportado (pendiente, en_revision, aprobado, rechazado). Si pasa a aprobado, genera recibo PDF y envÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­a por correo al email del cliente (cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©dula)."""
    if body.estado not in ("pendiente", "en_revision", "aprobado", "rechazado"):
        raise HTTPException(status_code=400, detail="Estado no vÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lido.")
    pr = db.execute(select(PagoReportado).where(PagoReportado.id == pago_id)).scalars().first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pago reportado no encontrado.")
    if body.estado == "rechazado" and not (body.motivo or "").strip():
        raise HTTPException(status_code=400, detail="El motivo es obligatorio al rechazar.")
    if body.estado == "aprobado" and pr.estado == "rechazado":
        raise HTTPException(status_code=400, detail="No se puede aprobar un pago rechazado.")
    estado_anterior = pr.estado
    pr.estado = body.estado
    pr.motivo_rechazo = (body.motivo or "").strip()[:2000] if body.estado == "rechazado" else None
    pr.usuario_gestion_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
    usuario_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)

    mensaje = f"Estado actualizado a {body.estado}."
    if body.estado == "aprobado":
        try:
            _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)
            db.commit()
        except HTTPException:
            raise
        
        # Agregar a tabla temporal de descargas
        from app.services.cobros.pagos_pendiente_descargar_service import agregar_a_pendiente_descargar
        agregar_a_pendiente_descargar(db, pr.id)
        
        db.refresh(pr)
        pdf_bytes = _generar_recibo_desde_pago(db, pr)
        pr.recibo_pdf = pdf_bytes
        to_email = _email_cliente_pago_reportado(db, pr)
        if not pr.correo_enviado_a and to_email:
            pr.correo_enviado_a = to_email
        if to_email:
            body_mail = f"Su reporte de pago ha sido aprobado. NÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºmero de referencia: {_referencia_display(pr.referencia_interna)}. Adjunto encontrarÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ el recibo.\n\nRapiCredit C.A."
            ok_mail, err_mail = send_email(
                [to_email],
                f"Recibo de reporte de pago {_referencia_display(pr.referencia_interna)}",
                body_mail,
                attachments=[(f"recibo_{pr.referencia_interna}.pdf", pdf_bytes)],
                servicio="cobros",
                respetar_destinos_manuales=True,
            )
            if ok_mail:
                logger.info("[COBROS] Cambiar a aprobado ref=%s: recibo enviado por correo a %s.", pr.referencia_interna, to_email)
                mensaje = "Estado actualizado a aprobado. Recibo enviado por correo."
            else:
                logger.error(
                    "[COBROS] Cambiar a aprobado ref=%s: correo NO enviado a %s. Error: %s.",
                    pr.referencia_interna, to_email, err_mail or "desconocido",
                )
                mensaje = "Estado actualizado a aprobado. El recibo no pudo enviarse por correo."
        else:
            mensaje = "Estado actualizado a aprobado. No hay correo registrado para este pago (no se enviÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³ recibo)."

    elif body.estado == "rechazado":
        to_email = _email_cliente_pago_reportado(db, pr)
        notif_activo = get_email_activo_servicio("notificaciones")
        logger.info(
            "[COBROS] PATCH estado=rechazado ref=%s: destino=%s servicio_notificaciones_activo=%s.",
            pr.referencia_interna, to_email or "sin correo", notif_activo,
        )
        if to_email and notif_activo:
            body_text = (
                f"Referencia: {pr.referencia_interna}\n\n"
                f"Su reporte de pago no ha sido aprobado.\n\n"
                f"Motivo del rechazo: {pr.motivo_rechazo}\n\n"
                f"Para mÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡s informaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n o aclaratorias, comunÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­quese con nosotros por WhatsApp: {WHATSAPP_DISPLAY} ({WHATSAPP_LINK}).\n\n"
                "RapiCredit C.A."
            )
            attachments_rech: List[Tuple[str, bytes]] = []
            if pr.comprobante:
                nombre_adj = (pr.comprobante_nombre or "comprobante").strip() or "comprobante"
                if not nombre_adj or "." not in nombre_adj:
                    ext = "pdf" if (pr.comprobante_tipo or "").lower().find("pdf") >= 0 else "jpg"
                    nombre_adj = f"comprobante_{pr.referencia_interna}.{ext}"
                attachments_rech.append((nombre_adj, bytes(pr.comprobante)))
            ok_mail, err_mail = send_email(
                [to_email],
                f"Reporte de pago no aprobado #{pr.referencia_interna}",
                body_text,
                attachments=attachments_rech if attachments_rech else None,
                servicio="notificaciones",
                respetar_destinos_manuales=True,
            )
            if ok_mail:
                logger.info("[COBROS] PATCH estado=rechazado ref=%s: correo enviado a %s (servicio notificaciones OK).", pr.referencia_interna, to_email)
                mensaje = "Estado actualizado a rechazado. Cliente notificado por correo (notificaciones@rapicreditca.com)."
            else:
                logger.error(
                    "[COBROS] PATCH estado=rechazado ref=%s: correo NO enviado a %s. Error: %s.",
                    pr.referencia_interna, to_email, err_mail or "desconocido",
                )
                mensaje = "Estado actualizado a rechazado. El correo al cliente no pudo enviarse."
        elif to_email and not notif_activo:
            logger.warning("[COBROS] PATCH estado=rechazado ref=%s: servicio notificaciones desactivado, no se enviÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³ correo a %s.", pr.referencia_interna, to_email)
            mensaje = "Estado actualizado a rechazado. Servicio de correo desactivado."
        else:
            logger.info("[COBROS] PATCH estado=rechazado ref=%s: no hay correo del cliente, no se enviÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³ notificaciÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³n.", pr.referencia_interna)
            mensaje = "Estado actualizado a rechazado."

    _registrar_historial(db, pago_id, estado_anterior, body.estado, usuario_email, body.motivo)
    db.commit()
    return {"ok": True, "mensaje": mensaje}



@router.post("/pagos-reportados/marcar-exportados")
def marcar_pagos_reportados_exportados(
    body: MarcarExportadosBody,
    db: Session = Depends(get_db),
):
    ids = sorted({int(x) for x in (body.pago_reportado_ids or []) if int(x) > 0})
    if not ids:
        raise HTTPException(status_code=400, detail="Debe indicar al menos un pago reportado aprobado para marcar exportado.")

    rows = db.execute(
        select(PagoReportado.id, PagoReportado.estado).where(PagoReportado.id.in_(ids))
    ).all()
    estado_por_id = {int(r.id): str(r.estado or "") for r in rows}

    faltantes = [pid for pid in ids if pid not in estado_por_id]
    if faltantes:
        raise HTTPException(status_code=404, detail=f"Pagos reportados no encontrados: {faltantes}")

    no_aprobados = [pid for pid in ids if estado_por_id[pid] != "aprobado"]
    if no_aprobados:
        raise HTTPException(
            status_code=400,
            detail=f"Solo se pueden marcar exportados pagos en estado aprobado. IDs invÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lidos: {no_aprobados}",
        )

    ya_exportados = set(
        db.execute(
            select(PagoReportadoExportado.pago_reportado_id).where(PagoReportadoExportado.pago_reportado_id.in_(ids))
        ).scalars().all()
    )

    nuevos = [
        PagoReportadoExportado(pago_reportado_id=pid)
        for pid in ids
        if pid not in ya_exportados
    ]

    if nuevos:
        db.add_all(nuevos)
        db.commit()

    return {
        "ok": True,
        "marcados": len(nuevos),
        "ya_exportados": len(ya_exportados),
        "total_solicitados": len(ids),
    }


@router.get("/descargar-pagos-aprobados-excel")
def descargar_pagos_aprobados_excel(db: Session = Depends(get_db)):
    """
    Descarga los pagos aprobados pendientes en Excel y luego vacÃƒÆ’Ã‚Â­a la tabla temporal.
    Columnas: CÃƒÆ’Ã‚Â©dula, Fecha, Comentario, NÃƒÆ’Ã‚Âºmero de Documento.
    """
    from io import BytesIO
    from openpyxl import Workbook
    from fastapi.responses import StreamingResponse
    from datetime import datetime
    
    # Obtener pagos pendientes de descargar
    pagos = obtener_pagos_aprobados_pendientes(db)
    
    if not pagos:
        raise HTTPException(status_code=204, detail="No hay pagos aprobados pendientes para descargar.")
    
    # Generar datos para Excel
    datos = obtener_datos_excel(pagos)
    
    # Crear workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Pagos Aprobados"
    
    # Encabezados
    headers = ["Cedula", "Fecha", "Comentario", "Numero de Documento"]
    ws.append(headers)
    
    # Datos
    for row in datos:
        ws.append([
            row["Cedula"],
            row["Fecha"],
            row["Comentario"],
            row["Numero de Documento"],
        ])
    
    # Ajustar ancho de columnas
    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 30
    ws.column_dimensions["D"].width = 25
    
    # Generar bytes
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Vaciar tabla despuÃƒÆ’Ã‚Â©s de generar el Excel
    cantidad_vaciada = vaciar_tabla_pendiente_descargar(db)
    
    fecha = datetime.now().strftime("%Y%m%d")
    filename = f"pagos_aprobados_{fecha}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )