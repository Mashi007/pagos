# -*- coding: utf-8 -*-
"""
ESTADO_CUENTA: envio manual masivo de estado de cuenta PDF.

Reglas de producto (acordadas):
- Solo prestamos APROBADO (nunca LIQUIDADO ni DESISTIMIENTO).
- 1 correo por prestamo APROBADO (si el cliente tiene 2, recibe 2).
- Sin email en ficha: se omite del listado.
- From: tucuenta@ (servicio estado_cuenta). BCC solo itmaster@rapicreditca.com.
- Asunto fijo: VERIFICA TU ESTADO DE CUENTA. PDF adjunto del prestamo.
- Tope proactivo 600/dia (America/Caracas); al dia siguiente continua desde el cursor;
  al terminar la lista reinicia desde el primer prestamo (round-robin).
- Modo prueba: To = correo de prueba; CC visible cobranza@rapicreditca.com; BCC itmaster@.
- Convive con Recibos y con el resto de notificaciones de mora (1 cuota, 2 cuotas, dia siguiente, etc.).
- No excluye titulares por haber recibido otras notificaciones de cobranza.
"""
from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.email import EMAIL_AUDIT_COBRANZA, EMAIL_ITMASTER, es_limite_diario_gmail, send_email
from app.core.email_config_holder import get_modo_pruebas_email
from app.models.cliente import Cliente
from app.models.envio_notificacion import EnvioNotificacion
from app.models.prestamo import Prestamo
from app.services.cuota_estado import hoy_negocio
from app.services.estado_cuenta_datos import obtener_datos_estado_cuenta_prestamo
from app.services.estado_cuenta_notificacion_cursor import (
    MAX_ENVIOS_DIARIOS,
    obtener_cursor_estado_cuenta,
    persistir_cursor_estado_cuenta,
)
from app.services.estado_cuenta_pdf import (
    base_url_y_token_recibo_para_pdf_estado_cuenta,
    generar_pdf_estado_cuenta,
)
from app.services.envio_notificacion_snapshot import persistir_snapshot_envio_notificacion
from app.services.notificacion_plantilla_estado_cuenta import (
    ASUNTO_ESTADO_CUENTA,
    CUERPO_ESTADO_CUENTA,
    CUERPO_ESTADO_CUENTA_FALLBACK,
    asegurar_modulo_estado_cuenta,
)
from app.services.notificacion_service import _prestamo_no_excluido_notif
from app.services.notificaciones_envios_store import get_notificaciones_envios_dict
from app.services.notificaciones_exclusion_desistimiento import (
    item_bloqueado_para_envio_notificacion,
    sql_cliente_sin_desistimiento,
)
from app.utils.cliente_emails import (
    emails_destino_desde_objeto,
    lista_correo_principal_notificaciones_desde_objeto,
    unir_destinatarios_log,
)

ESTADO_PRESTAMO_APROBADO = "APROBADO"

logger = logging.getLogger(__name__)

TIPO_CASO = "ESTADO_CUENTA"
TIPO_TAB = "estado_cuenta"
ProgressCb = Optional[Callable[[Dict[str, Any]], None]]


def _prestamo_aprobado_expr():
    return func.upper(func.trim(func.coalesce(Prestamo.estado, ""))) == ESTADO_PRESTAMO_APROBADO


def build_estado_cuenta_items(db: Session) -> List[dict]:
    """
    Universo: prestamos APROBADO con email en ficha del cliente.
    Orden estable por prestamo_id (cursor round-robin).
    Incluye titulares aunque hayan recibido 1 cuota, 2 cuotas, dia siguiente, etc.
    """
    rows = db.execute(
        select(Prestamo, Cliente)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(
            _prestamo_aprobado_expr(),
            _prestamo_no_excluido_notif(),
            sql_cliente_sin_desistimiento(),
        )
        .order_by(Prestamo.id.asc())
    ).all()

    items: List[dict] = []
    for prestamo, cliente in rows:
        correos = lista_correo_principal_notificaciones_desde_objeto(cliente)
        if not correos:
            # Sin email en ficha: omitir (no entra al ciclo).
            continue
        correo_prim = correos[0]
        cedula = (getattr(cliente, "cedula", None) or "").strip()
        nombre = (getattr(cliente, "nombres", None) or "").strip()
        telefono = (getattr(cliente, "telefono", None) or "").strip()
        item = {
            "cliente_id": int(cliente.id),
            "prestamo_id": int(prestamo.id),
            "nombre": nombre,
            "cedula": cedula,
            "correo": correo_prim,
            "correos": correos,
            "telefono": telefono,
            "estado": ESTADO_PRESTAMO_APROBADO,
            "notificacion_caso": TIPO_CASO,
            "numero_credito": getattr(prestamo, "numero_credito", None)
            or getattr(prestamo, "codigo", None),
        }
        items.append(item)
    return items


def _indice_inicio_ciclo(
    items: List[dict], *, ultimo_prestamo_id: Optional[int]
) -> int:
    """Indice 0-based del proximo item tras el cursor (wrap a 0 si termino el ciclo)."""
    if not items:
        return 0
    if ultimo_prestamo_id is None:
        return 0
    for i, it in enumerate(items):
        pid = it.get("prestamo_id")
        try:
            if pid is not None and int(pid) > int(ultimo_prestamo_id):
                return i
        except (TypeError, ValueError):
            continue
    return 0


def _slice_round_robin(
    items: List[dict],
    *,
    ultimo_prestamo_id: Optional[int],
    cupo: int,
) -> Tuple[List[dict], int]:
    """
    Toma hasta `cupo` items empezando despues de ultimo_prestamo_id; wrap al inicio.
    Devuelve (lote, indice_inicio_0based).
    """
    if not items or cupo <= 0:
        return [], 0
    n = len(items)
    start = _indice_inicio_ciclo(items, ultimo_prestamo_id=ultimo_prestamo_id)

    out: List[dict] = []
    i = start
    while len(out) < cupo and len(out) < n:
        out.append(items[i % n])
        i += 1
        if i - start >= n:
            break
    return out, start


def _payload_progreso(
    *,
    procesados_abs: int,
    total_universo: int,
    enviados: int,
    fallidos: int,
    sin_email: int,
    indice_inicio: int,
    enviados_hoy: int,
    omitidos: int = 0,
) -> Dict[str, Any]:
    """Progreso absoluto en el universo: dia 1 → 600; dia 2 reanuda en 601."""
    hasta = max(0, int(total_universo))
    proc = max(0, int(procesados_abs))
    if hasta > 0:
        proc = min(proc, hasta)
    return {
        "procesados": proc,
        "total_en_lista": hasta,
        "enviados": enviados,
        "fallidos": fallidos,
        "sin_email": sin_email,
        "omitidos_bloqueados": omitidos,
        "desde_checkpoint": max(0, int(indice_inicio)),
        "cupo_diario": MAX_ENVIOS_DIARIOS,
        "enviados_hoy": max(0, int(enviados_hoy)),
        "tipo_caso": TIPO_CASO,
    }


def _resolver_destinos_y_modo_prueba(
    db: Session, correos_cliente: List[str]
) -> Tuple[List[str], bool]:
    """
    Destinos efectivos. Prioriza modo prueba de Notificaciones (notificaciones_envios)
    y luego el de servicio estado_cuenta.
    """
    cfg = get_notificaciones_envios_dict(db)
    raw_modo = cfg.get("modo_pruebas")
    modo_np = raw_modo is True or (
        isinstance(raw_modo, str) and raw_modo.strip().lower() == "true"
    )
    emails_np: List[str] = []
    raw_list = cfg.get("emails_pruebas")
    if isinstance(raw_list, list):
        emails_np = [
            e.strip()
            for e in raw_list
            if e and isinstance(e, str) and "@" in e.strip()
            and e.strip().lower() != "itmaster@rapicreditca.com"
        ]
    if not emails_np:
        ep = cfg.get("email_pruebas")
        if isinstance(ep, str) and "@" in ep.strip():
            if ep.strip().lower() != "itmaster@rapicreditca.com":
                emails_np = [ep.strip()]

    if modo_np and emails_np:
        return emails_np, True

    mp, emails_svc = get_modo_pruebas_email(servicio="estado_cuenta")
    if mp and emails_svc:
        limpios = [
            e.strip()
            for e in emails_svc
            if e and isinstance(e, str) and "@" in e.strip()
            and e.strip().lower() != "itmaster@rapicreditca.com"
        ]
        if limpios:
            return limpios, True

    return list(correos_cliente), False


def _logo_url() -> str:
    """URL pública del logo (misma ruta que el resto de plantillas de correo)."""
    from app.core.email import _logo_url_for_email

    return _logo_url_for_email()


def _cuerpo_html_para_item(item: dict, plantilla_html: str) -> str:
    nombre = (item.get("nombre") or "").strip() or "cliente"
    cedula = (item.get("cedula") or "").strip()
    logo = _logo_url()
    html = plantilla_html or CUERPO_ESTADO_CUENTA
    # Soporta {{var}} y {var}
    for key, val in (
        ("nombre", nombre),
        ("cedula", cedula),
        ("logo_url", logo),
        ("LOGO_URL", logo),
    ):
        html = html.replace("{{" + key + "}}", str(val))
        html = html.replace("{" + key + "}", str(val))
    return html


def _generar_pdf_prestamo(db: Session, prestamo_id: int, item: dict) -> Optional[bytes]:
    datos = obtener_datos_estado_cuenta_prestamo(db, prestamo_id, sincronizar=True)
    if not datos:
        return None
    # Defensa: si el prestamo dejo de ser APROBADO entre listado y envio.
    prestamos_list = datos.get("prestamos_list") or []
    for p in prestamos_list:
        est = str((p or {}).get("estado") or "").strip().upper()
        if est in ("LIQUIDADO", "DESISTIMIENTO", "DESESTIMADO", "DESISTIDO"):
            logger.info(
                "ESTADO_CUENTA: omitido prestamo_id=%s estado=%s",
                prestamo_id,
                est,
            )
            return None

    cedula_pdf = (datos.get("cedula") or item.get("cedula") or "").strip()
    nombre = (datos.get("nombre") or item.get("nombre") or "").strip()
    fecha_corte = datos.get("fecha_corte") or hoy_negocio()
    if hasattr(fecha_corte, "date") and not isinstance(fecha_corte, date):
        fecha_corte = fecha_corte.date()

    base_pdf, tok_pdf = base_url_y_token_recibo_para_pdf_estado_cuenta(cedula_pdf)
    pdf_bytes = generar_pdf_estado_cuenta(
        cedula=cedula_pdf,
        nombre=nombre,
        prestamos=prestamos_list,
        fecha_corte=fecha_corte,
        amortizaciones_por_prestamo=datos.get("amortizaciones_por_prestamo") or [],
        pagos_realizados=datos.get("pagos_realizados") or [],
        recibos=None,
        recibo_token=tok_pdf,
        base_url=base_pdf,
    )
    if not pdf_bytes or len(pdf_bytes) < 8 or not pdf_bytes.startswith(b"%PDF"):
        return None
    return pdf_bytes


def ejecutar_envio_estado_cuenta(
    db: Session,
    *,
    on_progress: ProgressCb = None,
    token_seguimiento: Optional[str] = None,
) -> dict:
    """
    Envia hasta 600 correos del dia (Caracas) desde el cursor, con PDF por prestamo.
    Continua el dia siguiente; al terminar la lista vuelve a empezar.
    """
    try:
        asegurar_modulo_estado_cuenta(db, forzar_contenido_plantilla=True)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("ESTADO_CUENTA: no se pudo asegurar plantilla")

    items_all = build_estado_cuenta_items(db)
    total_universo = len(items_all)
    cursor = obtener_cursor_estado_cuenta(db)
    cupo = int(cursor.get("cupo_restante") or 0)
    enviados_hoy = int(cursor.get("enviados_hoy") or 0)
    ultimo_id = cursor.get("ultimo_prestamo_id")
    fecha_neg = str(cursor.get("fecha_negocio") or hoy_negocio().isoformat())
    indice_inicio = _indice_inicio_ciclo(
        items_all, ultimo_prestamo_id=ultimo_id
    )

    if cupo <= 0:
        # Ya se enviaron 600 hoy: barra en checkpoint (ej. 600) / universo; reanuda manana en 601.
        resumen = {
            "enviados": 0,
            "fallidos": 0,
            "sin_email": 0,
            "omitidos_bloqueados": 0,
            "omitidos_pdf": 0,
            "total_en_lista": total_universo,
            "total_universo": total_universo,
            "procesados": indice_inicio,
            "desde_checkpoint": indice_inicio,
            "pausado_limite_gmail": True,
            "pausado_cupo_diario": True,
            "cupo_diario": MAX_ENVIOS_DIARIOS,
            "enviados_hoy": enviados_hoy,
            "cursor": cursor,
            "motivo_pausa": "cupo_proactivo_600",
            "tipo_caso": TIPO_CASO,
        }
        if on_progress:
            try:
                on_progress(
                    _payload_progreso(
                        procesados_abs=indice_inicio,
                        total_universo=total_universo,
                        enviados=0,
                        fallidos=0,
                        sin_email=0,
                        indice_inicio=indice_inicio,
                        enviados_hoy=enviados_hoy,
                    )
                )
            except Exception:
                pass
        return resumen

    lote, indice_inicio = _slice_round_robin(
        items_all, ultimo_prestamo_id=ultimo_id, cupo=cupo
    )

    # Cargar HTML plantilla desde BD si existe
    plantilla_html = CUERPO_ESTADO_CUENTA
    try:
        from app.models.plantilla_notificacion import PlantillaNotificacion

        cfg = get_notificaciones_envios_dict(db)
        row = cfg.get(TIPO_CASO) if isinstance(cfg, dict) else None
        pid = None
        if isinstance(row, dict) and row.get("plantilla_id") is not None:
            try:
                pid = int(row.get("plantilla_id"))
            except (TypeError, ValueError):
                pid = None
        if pid:
            p = db.get(PlantillaNotificacion, pid)
            if p and (p.cuerpo or "").strip():
                plantilla_html = p.cuerpo
    except Exception:
        logger.exception("ESTADO_CUENTA: no se pudo cargar plantilla BD; usando HTML archivo")

    enviados = 0
    fallidos = 0
    sin_email = 0
    omitidos_bloqueados = 0
    omitidos_pdf = 0
    pausado_gmail = False
    motivo_pausa = None
    procesados_lote = 0

    if on_progress:
        try:
            on_progress(
                _payload_progreso(
                    procesados_abs=indice_inicio,
                    total_universo=total_universo,
                    enviados=0,
                    fallidos=0,
                    sin_email=0,
                    indice_inicio=indice_inicio,
                    enviados_hoy=enviados_hoy,
                )
            )
        except Exception:
            pass

    for item in lote:
        # Cancelacion de emergencia
        if token_seguimiento:
            try:
                from app.services.notificaciones_envio_cancel import (
                    cancelacion_lote_activa,
                )

                if cancelacion_lote_activa(
                    db, tipo_caso=TIPO_CASO, token_seguimiento=token_seguimiento
                ):
                    motivo_pausa = "cancelado_usuario"
                    break
            except Exception:
                pass

        prestamo_id = item.get("prestamo_id")
        try:
            prestamo_id_int = int(prestamo_id) if prestamo_id is not None else None
        except (TypeError, ValueError):
            prestamo_id_int = None

        def _avanzar_progreso(*, omitido: bool = False) -> int:
            nonlocal procesados_lote
            procesados_lote += 1
            # Posicion 1-based en el universo: tras 600 → reanuda en 601.
            return indice_inicio + procesados_lote

        if prestamo_id_int is None:
            fallidos += 1
            abs_proc = _avanzar_progreso()
            if on_progress:
                try:
                    on_progress(
                        _payload_progreso(
                            procesados_abs=abs_proc,
                            total_universo=total_universo,
                            enviados=enviados,
                            fallidos=fallidos,
                            sin_email=sin_email,
                            indice_inicio=indice_inicio,
                            enviados_hoy=enviados_hoy,
                            omitidos=omitidos_bloqueados + omitidos_pdf,
                        )
                    )
                except Exception:
                    pass
            continue

        bloqueado, _motivo_bloqueo = item_bloqueado_para_envio_notificacion(
            db, item
        )
        if bloqueado:
            omitidos_bloqueados += 1
            ultimo_id = prestamo_id_int
            abs_proc = _avanzar_progreso(omitido=True)
            if on_progress:
                try:
                    on_progress(
                        _payload_progreso(
                            procesados_abs=abs_proc,
                            total_universo=total_universo,
                            enviados=enviados,
                            fallidos=fallidos,
                            sin_email=sin_email,
                            indice_inicio=indice_inicio,
                            enviados_hoy=enviados_hoy,
                            omitidos=omitidos_bloqueados + omitidos_pdf,
                        )
                    )
                except Exception:
                    pass
            continue

        correos = list(item.get("correos") or [])
        if not correos:
            correos = emails_destino_desde_objeto(
                type("C", (), {"email": item.get("correo"), "email_secundario": None})()
            )
        if not correos:
            sin_email += 1
            ultimo_id = prestamo_id_int
            abs_proc = _avanzar_progreso()
            if on_progress:
                try:
                    on_progress(
                        _payload_progreso(
                            procesados_abs=abs_proc,
                            total_universo=total_universo,
                            enviados=enviados,
                            fallidos=fallidos,
                            sin_email=sin_email,
                            indice_inicio=indice_inicio,
                            enviados_hoy=enviados_hoy,
                            omitidos=omitidos_bloqueados + omitidos_pdf,
                        )
                    )
                except Exception:
                    pass
            continue

        destinos, modo_prueba = _resolver_destinos_y_modo_prueba(db, correos)
        if not destinos:
            sin_email += 1
            ultimo_id = prestamo_id_int
            abs_proc = _avanzar_progreso()
            if on_progress:
                try:
                    on_progress(
                        _payload_progreso(
                            procesados_abs=abs_proc,
                            total_universo=total_universo,
                            enviados=enviados,
                            fallidos=fallidos,
                            sin_email=sin_email,
                            indice_inicio=indice_inicio,
                            enviados_hoy=enviados_hoy,
                            omitidos=omitidos_bloqueados + omitidos_pdf,
                        )
                    )
                except Exception:
                    pass
            continue

        try:
            pdf_bytes = _generar_pdf_prestamo(db, prestamo_id_int, item)
        except Exception:
            logger.exception(
                "ESTADO_CUENTA: error PDF prestamo_id=%s", prestamo_id_int
            )
            pdf_bytes = None

        if not pdf_bytes:
            omitidos_pdf += 1
            fallidos += 1
            ultimo_id = prestamo_id_int
            persistir_cursor_estado_cuenta(
                db,
                ultimo_prestamo_id=ultimo_id,
                enviados_hoy=enviados_hoy,
                fecha_negocio=fecha_neg,
            )
            try:
                db.commit()
            except Exception:
                db.rollback()
            abs_proc = _avanzar_progreso()
            if on_progress:
                try:
                    on_progress(
                        _payload_progreso(
                            procesados_abs=abs_proc,
                            total_universo=total_universo,
                            enviados=enviados,
                            fallidos=fallidos,
                            sin_email=sin_email,
                            indice_inicio=indice_inicio,
                            enviados_hoy=enviados_hoy,
                            omitidos=omitidos_bloqueados + omitidos_pdf,
                        )
                    )
                except Exception:
                    pass
            continue

        ced_safe = "".join(
            ch if ch.isalnum() or ch in ("-", "_") else "_"
            for ch in str(item.get("cedula") or prestamo_id_int)
        )[:80]
        fname = f"estado_cuenta_{ced_safe}_{prestamo_id_int}.pdf"
        body_html = _cuerpo_html_para_item(item, plantilla_html)
        body_plain = CUERPO_ESTADO_CUENTA_FALLBACK
        smtp_meta: Dict[str, Any] = {}

        ok, msg = send_email(
            destinos,
            ASUNTO_ESTADO_CUENTA,
            body_plain,
            body_html=body_html,
            cc_emails=[EMAIL_AUDIT_COBRANZA] if modo_prueba else None,
            bcc_emails=[EMAIL_ITMASTER],
            attachments=[(fname, pdf_bytes)],
            respetar_destinos_manuales=modo_prueba,
            servicio="estado_cuenta",
            tipo_tab=TIPO_TAB,
            smtp_session_metadata=smtp_meta,
            aplicar_cco_automatica=False,
        )

        if ok:
            enviados += 1
            enviados_hoy += 1
        else:
            fallidos += 1
            if es_limite_diario_gmail(msg) or bool(
                smtp_meta.get("limite_diario_gmail")
            ):
                pausado_gmail = True
                motivo_pausa = (msg or "limite_diario_gmail")[:500]

        envio_row = EnvioNotificacion(
            tipo_tab=TIPO_TAB,
            asunto=ASUNTO_ESTADO_CUENTA[:500],
            email=unir_destinatarios_log(destinos, max_len=255),
            nombre=(item.get("nombre") or "")[:255],
            cedula=(item.get("cedula") or "")[:50],
            exito=ok,
            error_mensaje=None if ok else (msg or "")[:5000],
            prestamo_id=prestamo_id_int,
            mensaje_html=body_html,
            mensaje_texto=body_plain,
            metadata_tecnica=smtp_meta if smtp_meta else None,
        )
        try:
            db.add(envio_row)
            persistir_snapshot_envio_notificacion(
                db, envio_row, [(fname, pdf_bytes)] if ok else None
            )
            ultimo_id = prestamo_id_int
            persistir_cursor_estado_cuenta(
                db,
                ultimo_prestamo_id=ultimo_id,
                enviados_hoy=enviados_hoy,
                fecha_negocio=fecha_neg,
            )
            db.commit()
        except Exception as e:
            db.rollback()
            logger.exception(
                "ESTADO_CUENTA: fallo persistencia prestamo_id=%s: %s",
                prestamo_id_int,
                e,
            )

        abs_proc = _avanzar_progreso()
        if on_progress:
            try:
                on_progress(
                    _payload_progreso(
                        procesados_abs=abs_proc,
                        total_universo=total_universo,
                        enviados=enviados,
                        fallidos=fallidos,
                        sin_email=sin_email,
                        indice_inicio=indice_inicio,
                        enviados_hoy=enviados_hoy,
                        omitidos=omitidos_bloqueados + omitidos_pdf,
                    )
                )
            except Exception:
                pass

        if pausado_gmail:
            break
        if enviados_hoy >= MAX_ENVIOS_DIARIOS:
            motivo_pausa = "cupo_proactivo_600"
            break
        time.sleep(0.5)

    procesados_abs_final = indice_inicio + procesados_lote
    cursor_final = persistir_cursor_estado_cuenta(
        db,
        ultimo_prestamo_id=ultimo_id,
        enviados_hoy=enviados_hoy,
        fecha_negocio=fecha_neg,
    )
    try:
        db.commit()
    except Exception:
        db.rollback()

    pausado_cupo = enviados_hoy >= MAX_ENVIOS_DIARIOS or motivo_pausa == "cupo_proactivo_600"
    return {
        "enviados": enviados,
        "fallidos": fallidos,
        "sin_email": sin_email,
        "omitidos_bloqueados": omitidos_bloqueados,
        "omitidos_pdf": omitidos_pdf,
        "total_en_lista": total_universo,
        "total_universo": total_universo,
        "procesados": procesados_abs_final,
        "desde_checkpoint": indice_inicio,
        "pausado_limite_gmail": bool(pausado_gmail or pausado_cupo),
        "pausado_cupo_diario": pausado_cupo,
        "cupo_diario": MAX_ENVIOS_DIARIOS,
        "enviados_hoy": enviados_hoy,
        "cursor": cursor_final,
        "motivo_pausa": motivo_pausa,
        "tipo_caso": TIPO_CASO,
    }
