"""Mensajes de error Gemini legibles para operacion (escaner, cobros publico, finiquito OCR)."""
from __future__ import annotations


def mensaje_error_gemini_para_usuario(exc: BaseException) -> str:
    raw = str(exc).lower()
    if "dunning" in raw and "deny" in raw:
        return (
            "Google sigue bloqueando Gemini por facturacion (dunning) en el proyecto de la API key. "
            "Si ya pago: confirme que el pago es en el MISMO proyecto de la clave en Render, "
            "cree una API key nueva en https://aistudio.google.com/apikey, actualice GEMINI_API_KEY "
            "y reinicie el servicio en Render. Mientras tanto, complete el comprobante a mano."
        )
    if "gemini no configurado" in raw or "clave vac" in raw:
        return "Gemini no esta configurado (falta GEMINI_API_KEY en el servidor)."
    if "permission_denied" in raw or "403" in raw:
        return (
            "Acceso denegado a Gemini (403). Suele ser facturacion o permisos del proyecto de Google."
        )
    if "resource_exhausted" in raw or "429" in raw:
        return "Limite de uso de Gemini alcanzado. Intente de nuevo en unos minutos."
    if "503" in raw or "unavailable" in raw:
        return "Servicio Gemini temporalmente no disponible. Intente de nuevo."
    if "no se pudo interpretar" in raw:
        return str(exc)[:500]
    return "No se pudo procesar el comprobante en este momento. Intente de nuevo."
