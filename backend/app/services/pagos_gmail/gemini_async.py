"""
Ejecutar llamadas bloqueantes a Gemini fuera del event loop (UvicornWorker).

Con --workers 1, varias peticiones async que llaman sync a la API de Google bloquean
auth/me, validar-cedula, tasas, etc. hasta terminar. asyncio.to_thread + semáforo
limita concurrencia sin cambiar lógica de negocio.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable, Dict, Optional, TypeVar

from app.services.pagos_gmail.gemini_service import (
    compare_form_with_image,
    extract_infopagos_campos_desde_comprobante,
    extract_infopagos_campos_desde_comprobante_con_rescate_plantilla,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _resolve_max_concurrent() -> int:
    raw = os.environ.get("GEMINI_MAX_CONCURRENT_PER_WORKER", "2")
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = 2
    return max(1, min(n, 8))


_GEMINI_SEMAPHORE = asyncio.Semaphore(_resolve_max_concurrent())


async def run_blocking_gemini(fn: Callable[..., T], /, *args, **kwargs) -> T:
    """Ejecuta callable sync de Gemini en un hilo, con tope de concurrencia por worker."""
    async with _GEMINI_SEMAPHORE:
        return await asyncio.to_thread(fn, *args, **kwargs)


async def extract_infopagos_campos_desde_comprobante_async(
    cedula_deudor_contexto: str,
    image_bytes: bytes,
    filename: str = "comprobante.jpg",
    api_key: Optional[str] = None,
    institucion_plantilla: Optional[str] = None,
) -> Dict[str, Any]:
    return await run_blocking_gemini(
        extract_infopagos_campos_desde_comprobante,
        cedula_deudor_contexto,
        image_bytes,
        filename,
        api_key,
        institucion_plantilla,
    )


async def extract_infopagos_campos_desde_comprobante_con_rescate_plantilla_async(
    cedula_deudor_contexto: str,
    image_bytes: bytes,
    filename: str = "comprobante.jpg",
    api_key: Optional[str] = None,
    institucion_plantilla: Optional[str] = None,
) -> Dict[str, Any]:
    return await run_blocking_gemini(
        extract_infopagos_campos_desde_comprobante_con_rescate_plantilla,
        cedula_deudor_contexto,
        image_bytes,
        filename,
        api_key,
        institucion_plantilla,
    )


async def compare_form_with_image_async(
    form_data: Dict[str, Any],
    image_bytes: bytes,
    filename: str = "comprobante.jpg",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    return await run_blocking_gemini(
        compare_form_with_image,
        form_data,
        image_bytes,
        filename,
        api_key,
    )
