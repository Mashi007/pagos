"""
Recibos: correo con PDF de estado de cuenta tras pagos conciliados (tabla pagos).

Criterio de negocio (alineado a BD real):
- Conciliación y marca de pago están en ``pagos`` (``conciliado``, ``fecha_registro``, ``estado``).
- Vínculo con cuotas: ``cuotas.pago_id = pagos.id`` o fila en ``cuota_pagos`` (pagos aplicados a cuotas).
- Ventana por **fecha_registro** (recepción/registro en sistema) en America/Caracas (naive = reloj Caracas).

Ventana (por día de referencia ``fecha_dia`` en America/Caracas): **``fecha_registro`` del mismo día
calendario desde 00:00 hasta 23:45 inclusive**. El envío masivo Recibos es **manual** (UI admin o POST
``/notificaciones/recibos/ejecutar``); no hay cron en APScheduler. Los registros con hora de recepción
**después de 23:45** ese día quedan fuera de la ventana de ese ``fecha_dia`` (no se reinterpretan al día
siguiente en esta lógica).

Regla: el **envío real** (no simulación) solo corre si ``fecha_dia`` es **hoy** ``hoy_negocio()``,
salvo reenvío admin con ``permite_envio_real_fecha_no_hoy``.

Idempotencia en BD: columna ``slot`` fija ``RECIBOS_VENTANA_SLOT`` (histórico puede tener valores antiguos).
El listado admin y el envío real consideran solo cédulas **pendientes** (sin fila en ``recibos_email_envio``
para ese ``fecha_dia`` y slot); tras un envío exitoso esas filas dejan de mostrarse hasta otro día/ventana.

PDF: misma fuente que el portal (``obtener_datos_estado_cuenta_cliente`` + ``generar_pdf_estado_cuenta``),
con ``base_url`` y ``recibo_token`` resueltos por ``base_url_y_token_recibo_para_pdf_estado_cuenta`` (sin
``Request``: URL pública vía ``get_effective_api_public_base_url()``). Si no hay base resolvible, el PDF va
sin enlaces «Ver recibo».
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.email import send_email
from app.core.email_config_holder import get_email_activo_servicio, get_modo_pruebas_email
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.envio_notificacion import EnvioNotificacion
from app.models.recibos_email_envio import RecibosEmailEnvio
from app.services.cuota_estado import TZ_NEGOCIO, hoy_negocio
from app.services.documentos_cliente_centro import (
    base_url_y_token_recibo_para_pdf_estado_cuenta,
    generar_pdf_estado_cuenta,
    obtener_datos_estado_cuenta_cliente,
    obtener_recibos_cliente_estado_cuenta,
)
from app.services.notificaciones_exclusion_desistimiento import cliente_bloqueado_por_desistimiento
from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd

logger = logging.getLogger(__name__)

# Slot actual en recibos_email_envio (ventana día calendario 00:00–23:45 Caracas).
RECIBOS_VENTANA_SLOT = "dia_00_2345"
# Ventana histórica (24 h hasta 15:00). Se sigue considerando al decidir «ya enviado» para no duplicar.
RECIBOS_VENTANA_SLOT_LEGACY = "hasta_15_24h"
RECIBOS_VENTANA_SLOTS_IDEMPOTENCIA = (RECIBOS_VENTANA_SLOT, RECIBOS_VENTANA_SLOT_LEGACY)

# PDF adjunto: enlaces «Ver recibo» (GET …/estado-cuenta/public/recibo-pago) requieren URL absoluta + JWT.
# La base pública se resuelve con ``get_effective_api_public_base_url()`` (BACKEND_PUBLIC_URL u orígenes de
# FRONTEND_PUBLIC_URL / GOOGLE_REDIRECT_URI en el mismo host).


def _base_url_publico_recibos_pdf() -> str:
    from app.core.config import get_effective_api_public_base_url

    return get_effective_api_public_base_url()


def _recibo_token_para_pdf_recibos(cedula_lookup_norm: str) -> Optional[str]:
    """Mismo tipo `recibo` que `create_recibo_token` en estado de cuenta público; sub = cédula comparable."""
    from app.core.security import create_recibo_token

    ced = (cedula_lookup_norm or "").strip()
    if not ced:
        return None
    return create_recibo_token(ced, expire_hours=168)


def ruta_archivo_plantilla_recibos_confirmacion() -> Path:
    """Ruta absoluta de ``recibos_confirmacion_pago_email.html`` (mismo directorio que este módulo)."""
    return Path(__file__).resolve().with_name("recibos_confirmacion_pago_email.html")


# Clave en ``configuracion.valor`` (Text): HTML crudo guardado desde admin. Prioridad sobre archivo en disco
# para que job y API en varias réplicas usen la misma plantilla (p. ej. cloud sin FS compartido).
RECIBOS_PLANTILLA_HTML_CLAVE = "recibos_plantilla_correo_html"


def persistir_plantilla_recibos_html_en_bd(db: Session, html: str) -> None:
    """Inserta o actualiza la plantilla Recibos en la tabla ``configuracion``."""
    from app.models.configuracion import Configuracion

    row = db.get(Configuracion, RECIBOS_PLANTILLA_HTML_CLAVE)
    if row:
        row.valor = html
    else:
        db.add(Configuracion(clave=RECIBOS_PLANTILLA_HTML_CLAVE, valor=html))


def _cuerpo_html_recibos_confirmacion(db: Optional[Session] = None) -> str:
    """HTML del correo Recibos (confirmación + adjunto).

    Orden: si ``db`` está disponible y existe fila ``recibos_plantilla_correo_html`` no vacía en
    ``configuracion``, se usa (misma copia en todos los workers). Si no, se lee el archivo en disco
    empaquetado con el código (fallback / desarrollo local).
    """
    if db is not None:
        try:
            from app.models.configuracion import Configuracion

            row = db.get(Configuracion, RECIBOS_PLANTILLA_HTML_CLAVE)
            if isinstance(row, Configuracion):
                v = (row.valor or "").strip()
                if v:
                    return v
        except Exception:
            logger.exception("recibos: error leyendo plantilla HTML desde configuracion; se usa archivo")
    return ruta_archivo_plantilla_recibos_confirmacion().read_text(encoding="utf-8")


def bounds_fecha_registro_recibos_dia_caracas_00_2345(fecha_dia: date) -> Tuple[datetime, datetime]:
    """
    Inicio y fin inclusive (naive reloj Caracas) para ``pagos.fecha_registro`` en el día calendario
    ``fecha_dia``: [00:00:00, 23:45:00].
    """
    tz = ZoneInfo(TZ_NEGOCIO)
    start = datetime.combine(fecha_dia, time(0, 0, 0), tzinfo=tz).replace(tzinfo=None)
    end = datetime.combine(fecha_dia, time(23, 45, 0), tzinfo=tz).replace(tzinfo=None)
    return start, end


def _pago_aplicado_a_cuota_exists():
    cuota_direct = select(1).where(Cuota.pago_id == Pago.id).exists()
    via_cp = select(1).where(CuotaPago.pago_id == Pago.id).exists()
    return or_(cuota_direct, via_cp)


def cedulas_recibos_ya_enviadas_en_fecha(db: Session, fecha_dia: date) -> set[str]:
    """Cédulas (normalizadas) con envío Recibos persistido para ``fecha_dia`` (slot actual o legado)."""
    rows = db.execute(
        select(RecibosEmailEnvio.cedula_normalizada).where(
            RecibosEmailEnvio.fecha_dia == fecha_dia,
            RecibosEmailEnvio.slot.in_(RECIBOS_VENTANA_SLOTS_IDEMPOTENCIA),
        )
    ).scalars().all()
    return {(str(x) or "").strip() for x in rows if x and str(x).strip()}


def listar_pagos_recibos_ventana(
    db: Session,
    *,
    fecha_dia: date,
    excluir_cedulas_ya_enviadas: bool = False,
) -> List[Dict[str, Any]]:
    """Pagos conciliados PAGADO en la ventana 00:00–23:45 Caracas del día de referencia.

    Si ``excluir_cedulas_ya_enviadas`` es True, omite filas cuya cédula ya tiene fila en
    ``recibos_email_envio`` para ese ``fecha_dia`` y algún slot de idempotencia (listado y envío real
    solo pendientes). La simulación (``solo_simular``) usa False para seguir viendo toda la ventana.
    """
    start_naive, end_naive = bounds_fecha_registro_recibos_dia_caracas_00_2345(fecha_dia)
    rows = db.execute(
        select(Pago)
        .where(
            Pago.conciliado.is_(True),
            func.upper(func.coalesce(Pago.estado, "")) == "PAGADO",
            Pago.fecha_registro >= start_naive,
            Pago.fecha_registro <= end_naive,
            Pago.cedula_cliente.isnot(None),
            func.length(func.trim(Pago.cedula_cliente)) > 0,
            _pago_aplicado_a_cuota_exists(),
        )
        .order_by(Pago.fecha_registro.asc(), Pago.id.asc())
    ).scalars().all()
    out: List[Dict[str, Any]] = []
    for pg in rows:
        ced = (getattr(pg, "cedula_cliente", None) or "").strip()
        out.append(
            {
                "pago_id": int(pg.id),
                "cedula": ced,
                "cedula_normalizada": texto_cedula_comparable_bd(ced),
                "fecha_registro": pg.fecha_registro.isoformat() if pg.fecha_registro else None,
                "monto_pagado": float(getattr(pg, "monto_pagado", 0) or 0),
            }
        )
    if not excluir_cedulas_ya_enviadas:
        return out
    omit = cedulas_recibos_ya_enviadas_en_fecha(db, fecha_dia)
    if not omit:
        return out
    return [r for r in out if (r.get("cedula_normalizada") or "").strip() not in omit]


def _cedulas_distintas_desde_pagos(rows: List[Dict[str, Any]]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for r in rows:
        k = (r.get("cedula_normalizada") or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        ordered.append(k)
    return ordered


def _ya_enviado_recibo(db: Session, cedula_norm: str, fecha_dia: date) -> bool:
    row = db.execute(
        select(RecibosEmailEnvio.id).where(
            RecibosEmailEnvio.cedula_normalizada == cedula_norm,
            RecibosEmailEnvio.fecha_dia == fecha_dia,
            RecibosEmailEnvio.slot.in_(RECIBOS_VENTANA_SLOTS_IDEMPOTENCIA),
        ).limit(1)
    ).scalar_one_or_none()
    return row is not None


def ejecutar_recibos_envio_slot(
    db: Session,
    *,
    fecha_dia: date,
    solo_simular: bool = False,
    permite_envio_real_fecha_no_hoy: bool = False,
) -> Dict[str, Any]:
    """
    Por cada cédula distinta con pagos en ventana: genera estado de cuenta y envía a correos del cliente.
    Si ``solo_simular`` es True: no persiste ``recibos_email_envio`` ni idempotencia de envío real;
    sí genera el **mismo PDF** de estado de cuenta que el envío real. Si además está activo
    **modo pruebas Recibos** (config Email) con correos de prueba, envía **una muestra por SMTP**
    (mismo adjunto y HTML) redirigido a esos correos. Si modo pruebas está apagado, solo devuelve
    detalle con tamaño del PDF y destinatarios del cliente (sin SMTP).

    Envío real: por defecto ``fecha_dia`` debe ser ``hoy_negocio()`` (jobs programados). El endpoint
    admin puede pasar ``permite_envio_real_fecha_no_hoy=True`` para reenviar un lote de recepción de
    un día anterior (misma ventana ``fecha_registro`` 00:00–23:45 Caracas de ese día).
    """
    hoy = hoy_negocio()
    if (
        not solo_simular
        and fecha_dia != hoy
        and not permite_envio_real_fecha_no_hoy
    ):
        logger.info(
            "recibos: envío real rechazado — fecha_dia=%s ≠ hoy Caracas %s (solo recepción del día del job).",
            fecha_dia.isoformat(),
            hoy.isoformat(),
        )
        return {
            "fecha_dia": fecha_dia.isoformat(),
            "hoy_negocio": hoy.isoformat(),
            "slot": RECIBOS_VENTANA_SLOT,
            "solo_simular": solo_simular,
            "sin_casos_en_ventana": False,
            "error": "envio_real_solo_fecha_recepcion_hoy_caracas",
            "pagos_en_ventana": 0,
            "cedulas_distintas": 0,
            "enviados": 0,
            "fallidos": 0,
            "omitidos_sin_email": 0,
            "omitidos_ya_enviado": 0,
            "omitidos_desistimiento": 0,
            "omitidos_sin_datos": 0,
            "omitidos_error_estado_cuenta": 0,
            "omitidos_cedula_desalineada": 0,
            "detalles": [],
        }

    pagos = listar_pagos_recibos_ventana(
        db,
        fecha_dia=fecha_dia,
        excluir_cedulas_ya_enviadas=not solo_simular,
    )
    cedulas = _cedulas_distintas_desde_pagos(pagos)

    if not pagos or not cedulas:
        logger.info(
            "recibos: sin casos en ventana (no se envía correo a nadie): fecha_dia=%s slot=%s pagos=%s",
            fecha_dia.isoformat(),
            RECIBOS_VENTANA_SLOT,
            len(pagos),
        )
        return {
            "fecha_dia": fecha_dia.isoformat(),
            "slot": RECIBOS_VENTANA_SLOT,
            "solo_simular": solo_simular,
            "sin_casos_en_ventana": True,
            "pagos_en_ventana": len(pagos),
            "cedulas_distintas": len(cedulas),
            "enviados": 0,
            "fallidos": 0,
            "omitidos_sin_email": 0,
            "omitidos_ya_enviado": 0,
            "omitidos_desistimiento": 0,
            "omitidos_sin_datos": 0,
            "omitidos_error_estado_cuenta": 0,
            "omitidos_cedula_desalineada": 0,
            "detalles": [],
        }

    if not solo_simular and not get_email_activo_servicio("recibos"):
        return {
            "fecha_dia": fecha_dia.isoformat(),
            "slot": RECIBOS_VENTANA_SLOT,
            "solo_simular": solo_simular,
            "sin_casos_en_ventana": False,
            "error": "email_activo_recibos_desactivado",
            "pagos_en_ventana": len(pagos),
            "cedulas_distintas": len(cedulas),
            "enviados": 0,
            "fallidos": 0,
            "omitidos_sin_email": 0,
            "omitidos_ya_enviado": 0,
            "omitidos_desistimiento": 0,
            "omitidos_sin_datos": 0,
            "omitidos_error_estado_cuenta": 0,
            "omitidos_cedula_desalineada": 0,
            "detalles": [],
        }
    enviados = 0
    fallidos = 0
    omitidos_sin_email = 0
    omitidos_ya_enviado = 0
    omitidos_desistimiento = 0
    omitidos_sin_datos = 0
    omitidos_error_estado_cuenta = 0
    omitidos_cedula_desalineada = 0
    detalles: List[Dict[str, Any]] = []
    recibos_pdf_sin_base_url_logged = False

    for cedula_norm in cedulas:
        if not solo_simular and _ya_enviado_recibo(db, cedula_norm, fecha_dia):
            omitidos_ya_enviado += 1
            detalles.append({"cedula": cedula_norm, "motivo": "ya_enviado"})
            continue

        try:
            datos = obtener_datos_estado_cuenta_cliente(db, cedula_norm)
        except Exception as e:
            logger.exception(
                "recibos: error cargando datos estado de cuenta (obtener_datos_estado_cuenta_cliente) cedula_norm=%s",
                cedula_norm,
            )
            omitidos_error_estado_cuenta += 1
            detalles.append(
                {
                    "cedula": cedula_norm,
                    "motivo": "error_carga_datos_ec",
                    "error": str(e)[:500],
                }
            )
            continue

        if not datos:
            omitidos_sin_datos += 1
            detalles.append({"cedula": cedula_norm, "motivo": "sin_datos_estado_cuenta"})
            continue

        emails = datos.get("emails")
        if not isinstance(emails, list) or not emails:
            omitidos_sin_email += 1
            detalles.append({"cedula": cedula_norm, "motivo": "sin_email"})
            continue

        email0 = (emails[0] or "").strip() if emails else ""
        if cliente_bloqueado_por_desistimiento(db, cedula=cedula_norm, email=email0):
            omitidos_desistimiento += 1
            detalles.append({"cedula": cedula_norm, "motivo": "desistimiento"})
            continue

        cedula_raw_ventana = next(
            (
                (p.get("cedula") or "").strip()
                for p in pagos
                if (p.get("cedula_normalizada") or "").strip() == cedula_norm
            ),
            "",
        )
        cedula_display = (datos.get("cedula_display") or "").strip()
        cedula_para_comparar = cedula_display or cedula_raw_ventana
        if texto_cedula_comparable_bd(cedula_para_comparar) != cedula_norm:
            omitidos_cedula_desalineada += 1
            logger.error(
                "recibos: cédula del estado de cuenta no coincide con pagos en ventana (no se envía): "
                "cedula_norm=%s cedula_cliente=%s cedula_pago_ventana=%s",
                cedula_norm,
                cedula_display or "(vacío)",
                cedula_raw_ventana or "(vacío)",
            )
            detalles.append(
                {
                    "cedula": cedula_norm,
                    "motivo": "cedula_desalineada",
                    "cedula_cliente": cedula_display or None,
                    "cedula_pago_ventana": cedula_raw_ventana or None,
                }
            )
            continue

        cedula_pdf = cedula_display or cedula_raw_ventana or cedula_norm
        nombre = (datos.get("nombre") or "").strip()
        fecha_corte = datos.get("fecha_corte") or fecha_dia
        if isinstance(fecha_corte, datetime):
            fecha_corte_d = fecha_corte.date()
        else:
            fecha_corte_d = fecha_corte if isinstance(fecha_corte, date) else fecha_dia

        asunto = f"Estado de cuenta - {fecha_corte_d.isoformat()} (Recibos)"
        html_body = _cuerpo_html_recibos_confirmacion(db)
        body_plain = (
            "Confirmación de pago – RapiCredit. Adjunto: estado de cuenta actualizado (PDF). "
            f"Cédula: {cedula_pdf}. Fecha de corte: {fecha_corte_d.isoformat()}."
        )

        base_pdf, tok_pdf = base_url_y_token_recibo_para_pdf_estado_cuenta(cedula_norm)
        if not base_pdf and not recibos_pdf_sin_base_url_logged:
            logger.info(
                "recibos: sin URL pública de API resolvible (BACKEND_PUBLIC_URL, o mismo host desde "
                "FRONTEND_PUBLIC_URL / GOOGLE_REDIRECT_URI): el PDF adjunto no incluirá enlaces «Ver recibo»."
            )
            recibos_pdf_sin_base_url_logged = True

        try:
            recibos = obtener_recibos_cliente_estado_cuenta(db, cedula_norm)
            pdf_bytes = generar_pdf_estado_cuenta(
                cedula=cedula_pdf,
                nombre=nombre,
                prestamos=datos.get("prestamos_list") or [],
                fecha_corte=fecha_corte_d,
                amortizaciones_por_prestamo=datos.get("amortizaciones_por_prestamo") or [],
                pagos_realizados=datos.get("pagos_realizados") or [],
                recibos=recibos,
                recibo_token=tok_pdf,
                base_url=base_pdf,
            )
        except Exception as e:
            logger.exception(
                "recibos: error generando PDF estado de cuenta cedula_norm=%s",
                cedula_norm,
            )
            omitidos_error_estado_cuenta += 1
            detalles.append(
                {
                    "cedula": cedula_norm,
                    "motivo": "error_generacion_pdf_ec",
                    "error": str(e)[:500],
                }
            )
            continue

        if not pdf_bytes or len(pdf_bytes) < 8 or not pdf_bytes.startswith(b"%PDF"):
            logger.error(
                "recibos: PDF invalido o vacio cedula_norm=%s len=%s",
                cedula_norm,
                len(pdf_bytes or b""),
            )
            omitidos_error_estado_cuenta += 1
            detalles.append({"cedula": cedula_norm, "motivo": "pdf_invalido_ec"})
            continue

        fname_seguro = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in cedula_pdf)[:80]
        fname = f"estado_cuenta_{fname_seguro.replace('-', '_')}.pdf"
        to_list = [e.strip() for e in emails if e and isinstance(e, str) and "@" in e.strip()]

        if solo_simular:
            mp_prueba, emails_muestra = get_modo_pruebas_email(servicio="recibos")
            n_pagos_ced = len([p for p in pagos if p.get("cedula_normalizada") == cedula_norm])
            if mp_prueba and emails_muestra:
                smtp_meta_sim: Dict[str, Any] = {}
                ok_sim, err_sim = send_email(
                    to_list,
                    asunto,
                    body_plain,
                    body_html=html_body,
                    attachments=[(fname, pdf_bytes)],
                    servicio="recibos",
                    tipo_tab="recibos",
                    respetar_destinos_manuales=False,
                    smtp_session_metadata=smtp_meta_sim,
                )
                detalles.append(
                    {
                        "cedula": cedula_norm,
                        "motivo": "simulacion_muestra_smtp_ok" if ok_sim else "simulacion_muestra_smtp_fallo",
                        "error": None if ok_sim else (err_sim or "")[:500],
                        "pdf_bytes": len(pdf_bytes),
                        "emails_cliente": emails,
                        "emails_muestra_modo_pruebas": emails_muestra,
                        "pagos_en_ventana": n_pagos_ced,
                    }
                )
            else:
                detalles.append(
                    {
                        "cedula": cedula_norm,
                        "motivo": "simulacion_ok",
                        "emails": emails,
                        "pdf_bytes": len(pdf_bytes),
                        "pagos_en_ventana": n_pagos_ced,
                        "nota": "Active modo pruebas Recibos y correos de prueba en Configuración > Email para enviar muestra SMTP con el mismo PDF y HTML.",
                    }
                )
            continue

        smtp_meta: Dict[str, Any] = {}
        ok, err = send_email(
            to_list,
            asunto,
            body_plain,
            body_html=html_body,
            attachments=[(fname, pdf_bytes)],
            servicio="recibos",
            tipo_tab="recibos",
            respetar_destinos_manuales=False,
            smtp_session_metadata=smtp_meta,
        )
        email_log = ", ".join(to_list)[:255] if to_list else ""
        pid_log: Optional[int] = None
        pl = datos.get("prestamos_list") or []
        if pl and isinstance(pl[0], dict):
            try:
                raw_id = pl[0].get("id")
                pid_log = int(raw_id) if raw_id is not None else None
            except (TypeError, ValueError):
                pid_log = None
        db.add(
            EnvioNotificacion(
                tipo_tab="recibos",
                asunto=(asunto or "")[:500],
                email=email_log,
                nombre=(nombre or "")[:255],
                cedula=(cedula_display or cedula_norm)[:50],
                exito=bool(ok),
                error_mensaje=None if ok else (err or "")[:5000],
                prestamo_id=pid_log,
                correlativo=None,
                mensaje_texto=(body_plain or "")[:8000] if body_plain else None,
                metadata_tecnica=smtp_meta if smtp_meta else None,
            )
        )
        if ok:
            enviados += 1
            db.add(
                RecibosEmailEnvio(
                    cedula_normalizada=cedula_norm,
                    fecha_dia=fecha_dia,
                    slot=RECIBOS_VENTANA_SLOT,
                )
            )
            detalles.append({"cedula": cedula_norm, "motivo": "enviado", "emails": emails})
        else:
            fallidos += 1
            detalles.append({"cedula": cedula_norm, "motivo": "fallo_smtp", "error": (err or "")[:500]})

    if not solo_simular and (enviados or fallidos):
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.exception("recibos: commit tras envíos: %s", e)
            raise

    return {
        "fecha_dia": fecha_dia.isoformat(),
        "slot": RECIBOS_VENTANA_SLOT,
        "solo_simular": solo_simular,
        "sin_casos_en_ventana": False,
        "pagos_en_ventana": len(pagos),
        "cedulas_distintas": len(cedulas),
        "enviados": enviados,
        "fallidos": fallidos,
        "omitidos_sin_email": omitidos_sin_email,
        "omitidos_ya_enviado": omitidos_ya_enviado,
        "omitidos_desistimiento": omitidos_desistimiento,
        "omitidos_sin_datos": omitidos_sin_datos,
        "omitidos_error_estado_cuenta": omitidos_error_estado_cuenta,
        "omitidos_cedula_desalineada": omitidos_cedula_desalineada,
        "detalles": detalles[:200],
    }


def enviar_correo_prueba_recibos_datos_reales(
    db: Session,
    *,
    email_destino: str,
    fecha_dia: date,
    html_plantilla_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Correo de prueba desde Configuración Recibos: mismo PDF y mismas reglas que el envío real, tomando el
    **primer** cliente en orden de lote (cédulas distintas en ventana) que cumpla validaciones del job.

    HTML: si ``html_plantilla_override`` viene relleno (API avanzada), se usa tal cual; si no, **la misma
    plantilla que ``ejecutar_recibos_envio_slot``** — ``_cuerpo_html_recibos_confirmacion(db)`` (BD
    ``recibos_plantilla_correo_html`` o archivo). Tras ``send_email``, el cuerpo pasa por
    ``preparar_body_html_para_mime`` (igual que la vista previa admin).

    El mensaje se envía **solo** a ``email_destino``, no a los correos del cliente. No escribe
    ``recibos_email_envio`` ni ``envios_notificacion`` (un solo SMTP de muestra).
    """
    dest = (email_destino or "").strip()
    if not dest or "@" not in dest:
        return {"success": False, "mensaje": "Indique un correo de destino válido."}

    pagos = listar_pagos_recibos_ventana(
        db,
        fecha_dia=fecha_dia,
        excluir_cedulas_ya_enviadas=True,
    )
    cedulas = _cedulas_distintas_desde_pagos(pagos)
    if not pagos or not cedulas:
        return {
            "success": False,
            "mensaje": (
                "No hay pagos pendientes de envío Recibos para esa fecha (Caracas); no se puede generar una muestra "
                "con datos reales. Revise el listado Recibos o la fecha de corte."
            ),
            "fecha_dia": fecha_dia.isoformat(),
            "slot": RECIBOS_VENTANA_SLOT,
        }

    intentos: List[Dict[str, Any]] = []
    prueba_pdf_sin_base_logged = False

    for cedula_norm in cedulas:
        try:
            datos = obtener_datos_estado_cuenta_cliente(db, cedula_norm)
        except Exception as e:
            intentos.append({"cedula": cedula_norm, "motivo": "error_carga_datos_ec", "error": str(e)[:300]})
            continue

        if not datos:
            intentos.append({"cedula": cedula_norm, "motivo": "sin_datos_estado_cuenta"})
            continue

        emails = datos.get("emails")
        if not isinstance(emails, list) or not emails:
            intentos.append({"cedula": cedula_norm, "motivo": "sin_email"})
            continue

        email0 = (emails[0] or "").strip() if emails else ""
        if cliente_bloqueado_por_desistimiento(db, cedula=cedula_norm, email=email0):
            intentos.append({"cedula": cedula_norm, "motivo": "desistimiento"})
            continue

        cedula_raw_ventana = next(
            (
                (p.get("cedula") or "").strip()
                for p in pagos
                if (p.get("cedula_normalizada") or "").strip() == cedula_norm
            ),
            "",
        )
        cedula_display = (datos.get("cedula_display") or "").strip()
        cedula_para_comparar = cedula_display or cedula_raw_ventana
        if texto_cedula_comparable_bd(cedula_para_comparar) != cedula_norm:
            intentos.append({"cedula": cedula_norm, "motivo": "cedula_desalineada"})
            continue

        cedula_pdf = cedula_display or cedula_raw_ventana or cedula_norm
        nombre = (datos.get("nombre") or "").strip()
        fecha_corte = datos.get("fecha_corte") or fecha_dia
        if isinstance(fecha_corte, datetime):
            fecha_corte_d = fecha_corte.date()
        else:
            fecha_corte_d = fecha_corte if isinstance(fecha_corte, date) else fecha_dia

        asunto = f"[Prueba] Estado de cuenta - {fecha_corte_d.isoformat()} (Recibos)"
        raw_ov = (html_plantilla_override or "").strip()
        html_body = raw_ov if raw_ov else _cuerpo_html_recibos_confirmacion(db)
        body_plain = (
            "Confirmación de pago – RapiCredit. Adjunto: estado de cuenta actualizado (PDF). "
            f"Cédula: {cedula_pdf}. Fecha de corte: {fecha_corte_d.isoformat()}."
        )

        base_pdf, tok_pdf = base_url_y_token_recibo_para_pdf_estado_cuenta(cedula_norm)
        if not base_pdf and not prueba_pdf_sin_base_logged:
            logger.info(
                "recibos (prueba PDF): sin URL pública de API resolvible; sin enlaces «Ver recibo» en el adjunto."
            )
            prueba_pdf_sin_base_logged = True

        try:
            recibos = obtener_recibos_cliente_estado_cuenta(db, cedula_norm)
            pdf_bytes = generar_pdf_estado_cuenta(
                cedula=cedula_pdf,
                nombre=nombre,
                prestamos=datos.get("prestamos_list") or [],
                fecha_corte=fecha_corte_d,
                amortizaciones_por_prestamo=datos.get("amortizaciones_por_prestamo") or [],
                pagos_realizados=datos.get("pagos_realizados") or [],
                recibos=recibos,
                recibo_token=tok_pdf,
                base_url=base_pdf,
            )
        except Exception as e:
            intentos.append(
                {"cedula": cedula_norm, "motivo": "error_generacion_pdf_ec", "error": str(e)[:300]}
            )
            continue

        if not pdf_bytes or len(pdf_bytes) < 8 or not pdf_bytes.startswith(b"%PDF"):
            intentos.append({"cedula": cedula_norm, "motivo": "pdf_invalido_ec"})
            continue

        fname_seguro = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in cedula_pdf)[:80]
        fname = f"estado_cuenta_{fname_seguro.replace('-', '_')}.pdf"

        ok, err = send_email(
            [dest],
            asunto,
            body_plain,
            body_html=html_body,
            attachments=[(fname, pdf_bytes)],
            servicio="recibos",
            tipo_tab="recibos",
            respetar_destinos_manuales=True,
        )
        if ok:
            return {
                "success": True,
                "mensaje": (
                    "Muestra enviada: mismo HTML y PDF que Recibos, datos del primer cliente válido en la ventana; "
                    f"destino solo {dest} (no se usó el correo del cliente como To)."
                ),
                "email_destino": dest,
                "fecha_dia": fecha_dia.isoformat(),
                "slot": RECIBOS_VENTANA_SLOT,
                "cedula_normalizada": cedula_norm,
                "cedula_muestra": cedula_pdf,
                "nombre_cliente": nombre or None,
                "emails_cliente_ficha": emails,
                "pdf_bytes": len(pdf_bytes),
            }
        return {
            "success": False,
            "mensaje": err or "Error SMTP al enviar la muestra.",
            "email_destino": dest,
            "fecha_dia": fecha_dia.isoformat(),
            "cedula_intento": cedula_norm,
            "smtp_error": (err or "")[:500],
        }

    return {
        "success": False,
        "mensaje": (
            "Ninguna cédula en la ventana pudo usarse como muestra (mismas reglas que el envío real: "
            "datos de estado de cuenta, email en ficha, alineación de cédula, etc.)."
        ),
        "fecha_dia": fecha_dia.isoformat(),
        "slot": RECIBOS_VENTANA_SLOT,
        "cedulas_en_ventana": len(cedulas),
        "intentos_resumen": intentos[:15],
    }


def job_recibos_programado_caracas(db: Session) -> None:
    """Misma lógica que un envío manual del día hoy (Caracas); útil para scripts o pruebas sin cron."""
    ejecutar_recibos_envio_slot(db, fecha_dia=hoy_negocio(), solo_simular=False)


def job_recibos_1500(db: Session) -> None:
    """Compatibilidad: antes 15:00; delega al job diario actual."""
    job_recibos_programado_caracas(db)
