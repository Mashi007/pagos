"""Helpers y constantes para subida/servido de imágenes de comprobante de pago."""

from typing import Optional

from fastapi import Request

# Alineado con `cobros_publico_reporte_service.ALLOWED_COMPROBANTE_TYPES` (PDF + imágenes incl. HEIC).
_COMPROBANTE_IMG_CT = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/heic",
        "image/heif",
        "application/pdf",
    },
)
_MAX_COMPROBANTE_IMAGEN_BYTES = 10 * 1024 * 1024


def _public_base_url_para_comprobante(request: Request) -> str:
    xf_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    xf_host = (
        (request.headers.get("x-forwarded-host") or request.headers.get("host") or "")
        .split(",")[0]
        .strip()
    )
    scheme = (xf_proto or request.url.scheme or "https").lower()
    if xf_host:
        return f"{scheme}://{xf_host}".rstrip("/")
    return str(request.base_url).rstrip("/")


def _normalizar_id_comprobante_imagen(raw: str) -> Optional[str]:
    s = (raw or "").strip().lower()
    if not s:
        return None
    s = s.split(".")[0]
    s = s.replace("-", "")
    if len(s) == 32 and all(c in "0123456789abcdef" for c in s):
        return s
    return None
