"""
GET/PUT configuración informe de pagos (Google Drive, Sheets, OCR, destinatarios email, horarios).
Usado por flujo cobranza WhatsApp: imágenes → Drive → OCR → digitalización → email 6:00, 13:00, 16:30.
"""
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.core.database import get_db
from app.core.informe_pagos_config_holder import (
    CLAVE_INFORME_PAGOS_CONFIG,
    get_informe_pagos_config,
    sync_from_db,
    update_from_api,
)
from app.models.configuracion import Configuracion
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


class InformePagosConfigUpdate(BaseModel):
    """Campos permitidos para informe de pagos (Google Drive, Sheets, OCR, email)."""
    google_drive_folder_id: Optional[str] = None
    google_credentials_json: Optional[str] = None
    google_sheets_id: Optional[str] = None
    destinatarios_informe_emails: Optional[str] = None
    horarios_envio: Optional[list] = None


@router.get("/configuracion", response_model=dict)
def get_informe_pagos_configuracion(db: Session = Depends(get_db)):
    """
    Configuración informe de pagos (Google Drive, Sheets, OCR, destinatarios, horarios).
    google_credentials_json se devuelve enmascarado (***) por seguridad.
    """
    sync_from_db()
    cfg = get_informe_pagos_config()
    out = dict(cfg)
    if out.get("google_credentials_json"):
        out["google_credentials_json"] = "***"
    return out


@router.put("/configuracion", response_model=dict)
def put_informe_pagos_configuracion(
    payload: InformePagosConfigUpdate = Body(...),
    db: Session = Depends(get_db),
):
    """
    Actualizar configuración informe de pagos. Persiste en BD (clave informe_pagos_config).
    Si envías google_credentials_json vacío o "***", no se sobrescribe el valor guardado.
    """
    sync_from_db()
    data = payload.model_dump(exclude_none=True)
    if data.get("google_credentials_json") in ("", "***", None):
        data.pop("google_credentials_json", None)
    update_from_api(data)
    valor = json.dumps(get_informe_pagos_config())
    row = db.get(Configuracion, CLAVE_INFORME_PAGOS_CONFIG)
    if row:
        row.valor = valor
    else:
        db.add(Configuracion(clave=CLAVE_INFORME_PAGOS_CONFIG, valor=valor))
    db.commit()
    logger.info("Configuración informe pagos actualizada (campos: %s)", list(data.keys()))
    out = get_informe_pagos_config()
    if out.get("google_credentials_json"):
        out["google_credentials_json"] = "***"
    return {"message": "Configuración informe pagos actualizada", "configuracion": out}
