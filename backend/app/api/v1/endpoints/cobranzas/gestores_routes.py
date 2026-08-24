# -*- coding: utf-8 -*-
"""API Gestores de cobranza (solo administradores)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.schemas.auth import UserResponse
from app.services.cobranzas import gestores_service as svc
from app.services.cobranzas.gestores_constantes import GESTOR_NOMBRES

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("")
def listar_gestores(_user: UserResponse = Depends(require_admin)):
    return {"gestores": svc.listar_gestores()}


@router.get("/dashboard")
def dashboard_gestores(
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    try:
        return svc.dashboard_gestores(db)
    except Exception as e:
        logger.exception("[gestores] dashboard: %s", e)
        raise HTTPException(status_code=500, detail="Error al cargar dashboard de gestores.")


@router.post("/asegurar-asignacion")
def asegurar_asignacion(
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    try:
        return svc.asegurar_asignaciones(db)
    except Exception as e:
        logger.exception("[gestores] asegurar: %s", e)
        raise HTTPException(status_code=500, detail="Error al asegurar asignacion de gestores.")


@router.get("/{gestor_slug}/excel")
def descargar_excel_gestor(
    gestor_slug: str,
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    slug = (gestor_slug or "").strip().lower()
    if slug not in GESTOR_NOMBRES:
        raise HTTPException(status_code=404, detail="Gestor no encontrado.")
    try:
        data, fname, _nombre = svc.excel_gestor_bytes(db, slug)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("[gestores] excel %s: %s", slug, e)
        raise HTTPException(status_code=500, detail="Error al generar Excel del gestor.")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post("/enviar-listas-ahora")
def enviar_listas_ahora(
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(require_admin),
):
    """Disparo manual del correo nocturno (prueba / reenvio)."""
    try:
        return svc.enviar_listas_gestores_email(db)
    except Exception as e:
        logger.exception("[gestores] enviar listas: %s", e)
        raise HTTPException(status_code=500, detail="Error al enviar listas de gestores.")
