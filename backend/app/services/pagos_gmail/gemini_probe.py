"""Prueba real contra la API de Gemini (facturacion, permisos, modelo)."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.pagos_gmail.gemini_errors import mensaje_error_gemini_para_usuario
from app.services.pagos_gmail.gemini_service import _gemini_client

logger = logging.getLogger(__name__)

_PROJECT_RE = re.compile(r"projects/(\d+)")


def _clasificar_error_gemini(exc: BaseException) -> str:
    raw = str(exc).lower()
    if "dunning" in raw and "deny" in raw:
        return "billing_dunning"
    if "api key" in raw or "api_key" in raw or "invalid" in raw and "key" in raw:
        return "invalid_api_key"
    if "permission_denied" in raw or "403" in raw:
        return "permission_denied"
    if "resource_exhausted" in raw or "429" in raw:
        return "rate_limit"
    if "503" in raw or "unavailable" in raw:
        return "unavailable"
    if "not found" in raw and "model" in raw:
        return "model_not_found"
    return "unknown"


def _extraer_proyecto_google(exc: BaseException) -> Optional[str]:
    m = _PROJECT_RE.search(str(exc))
    return m.group(1) if m else None


def probe_gemini_live() -> Dict[str, Any]:
    """
    Llama a Gemini con un prompt minimo. No expone la API key.
    Util para comprobar si el pago en Google ya desbloqueo el proyecto.
    """
    key = (getattr(settings, "GEMINI_API_KEY", None) or "").strip()
    model_name = (getattr(settings, "GEMINI_MODEL", None) or "gemini-2.5-flash").strip()
    if not key:
        return {
            "ok": False,
            "code": "not_configured",
            "model": model_name,
            "message": "GEMINI_API_KEY no esta configurado en el servidor.",
            "user_message": mensaje_error_gemini_para_usuario(
                RuntimeError("GEMINI_API_KEY no configurado")
            ),
            "google_project_number": None,
        }

    try:
        from google.genai import types

        client = _gemini_client(key)
        response = client.models.generate_content(
            model=model_name,
            contents="Responde exactamente: OK",
            config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=16),
        )
        sample = ((response.text or "").strip())[:80]
        return {
            "ok": True,
            "code": "ok",
            "model": model_name,
            "message": "Gemini respondio correctamente.",
            "user_message": None,
            "sample": sample or "(vacio)",
            "google_project_number": None,
        }
    except Exception as e:
        code = _clasificar_error_gemini(e)
        proj = _extraer_proyecto_google(e)
        logger.warning("[GEMINI_PROBE] fallo code=%s project=%s: %s", code, proj, e)
        out: Dict[str, Any] = {
            "ok": False,
            "code": code,
            "model": model_name,
            "message": str(e)[:400],
            "user_message": mensaje_error_gemini_para_usuario(e),
            "google_project_number": proj,
        }
        if code == "billing_dunning":
            out["accion_recomendada"] = (
                "Pague o reactive facturacion en el MISMO proyecto Google de esta API key "
                f"(proyecto {proj or 'desconocido'}). Si pago en otra cuenta, cree una API key nueva "
                "en AI Studio del proyecto pagado, actualice GEMINI_API_KEY en Render y reinicie el servicio."
            )
        return out
