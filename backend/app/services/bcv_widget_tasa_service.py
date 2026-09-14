# -*- coding: utf-8 -*-
"""
Lectura puntual del recuadro de tasas de la portada BCV (EUR + USD + fecha valor).

Un GET a la URL pública, sin reintentos agresivos, sin proxies y sin desactivar TLS.
Si el WAF bloquea, el job registra el error y no insiste.
"""
from __future__ import annotations

import logging
import re
import ssl
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.tasa_cambio_service import aplicar_tasa_bcv_desde_widget

logger = logging.getLogger(__name__)

BCV_WIDGET_USER_AGENT = (
    "RapicreditTasaBot/1.0 (lectura EUR+USD+fecha valor; 1-2 GET/dia)"
)

# bcv.org.ve publica el leaf firmado por Sectigo Public Server Authentication CA DV R36
# pero envía un intermediario incorrecto en la cadena TLS. Sin este CA en el trust store,
# OpenSSL falla con CERTIFICATE_VERIFY_FAILED (unable to get local issuer certificate).
# Fuente pública: http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt
_SECTIGO_PUBLIC_SERVER_AUTH_CA_DV_R36_PEM = """-----BEGIN CERTIFICATE-----
MIIGTDCCBDSgAwIBAgIQOXpmzCdWNi4NqofKbqvjsTANBgkqhkiG9w0BAQwFADBf
MQswCQYDVQQGEwJHQjEYMBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMTYwNAYDVQQD
Ey1TZWN0aWdvIFB1YmxpYyBTZXJ2ZXIgQXV0aGVudGljYXRpb24gUm9vdCBSNDYw
HhcNMjEwMzIyMDAwMDAwWhcNMzYwMzIxMjM1OTU5WjBgMQswCQYDVQQGEwJHQjEY
MBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMTcwNQYDVQQDEy5TZWN0aWdvIFB1Ymxp
YyBTZXJ2ZXIgQXV0aGVudGljYXRpb24gQ0EgRFYgUjM2MIIBojANBgkqhkiG9w0B
AQEFAAOCAY8AMIIBigKCAYEAljZf2HIz7+SPUPQCQObZYcrxLTHYdf1ZtMRe7Yeq
RPSwygz16qJ9cAWtWNTcuICc++p8Dct7zNGxCpqmEtqifO7NvuB5dEVexXn9RFFH
12Hm+NtPRQgXIFjx6MSJcNWuVO3XGE57L1mHlcQYj+g4hny90aFh2SCZCDEVkAja
EMMfYPKuCjHuuF+bzHFb/9gV8P9+ekcHENF2nR1efGWSKwnfG5RawlkaQDpRtZTm
M64TIsv/r7cyFO4nSjs1jLdXYdz5q3a4L0NoabZfbdxVb+CUEHfB0bpulZQtH1Rv
38e/lIdP7OTTIlZh6OYL6NhxP8So0/sht/4J9mqIGxRFc0/pC8suja+wcIUna0HB
pXKfXTKpzgis+zmXDL06ASJf5E4A2/m+Hp6b84sfPAwQ766rI65mh50S0Di9E3Pn
2WcaJc+PILsBmYpgtmgWTR9eV9otfKRUBfzHUHcVgarub/XluEpRlTtZudU5xbFN
xx/DgMrXLUAPaI60fZ6wA+PTAgMBAAGjggGBMIIBfTAfBgNVHSMEGDAWgBRWc1hk
lfmSGrASKgRieaFAFYghSTAdBgNVHQ4EFgQUaMASFhgOr872h6YyV6NGUV3LBycw
DgYDVR0PAQH/BAQDAgGGMBIGA1UdEwEB/wQIMAYBAf8CAQAwHQYDVR0lBBYwFAYI
KwYBBQUHAwEGCCsGAQUFBwMCMBsGA1UdIAQUMBIwBgYEVR0gADAIBgZngQwBAgEw
VAYDVR0fBE0wSzBJoEegRYZDaHR0cDovL2NybC5zZWN0aWdvLmNvbS9TZWN0aWdv
UHVibGljU2VydmVyQXV0aGVudGljYXRpb25Sb290UjQ2LmNybDCBhAYIKwYBBQUH
AQEEeDB2ME8GCCsGAQUFBzAChkNodHRwOi8vY3J0LnNlY3RpZ28uY29tL1NlY3Rp
Z29QdWJsaWNTZXJ2ZXJBdXRoZW50aWNhdGlvblJvb3RSNDYucDdjMCMGCCsGAQUF
BzABhhdodHRwOi8vb2NzcC5zZWN0aWdvLmNvbTANBgkqhkiG9w0BAQwFAAOCAgEA
YtOC9Fy+TqECFw40IospI92kLGgoSZGPOSQXMBqmsGWZUQ7rux7cj1du6d9rD6C8
ze1B2eQjkrGkIL/OF1s7vSmgYVafsRoZd/IHUrkoQvX8FZwUsmPu7amgBfaY3g+d
q1x0jNGKb6I6Bzdl6LgMD9qxp+3i7GQOnd9J8LFSietY6Z4jUBzVoOoz8iAU84OF
h2HhAuiPw1ai0VnY38RTI+8kepGWVfGxfBWzwH9uIjeooIeaosVFvE8cmYUB4TSH
5dUyD0jHct2+8ceKEtIoFU/FfHq/mDaVnvcDCZXtIgitdMFQdMZaVehmObyhRdDD
4NQCs0gaI9AAgFj4L9QtkARzhQLNyRf87Kln+YU0lgCGr9HLg3rGO8q+Y4ppLsOd
unQZ6ZxPNGIfOApbPVf5hCe58EZwiWdHIMn9lPP6+F404y8NNugbQixBber+x536
WrZhFZLjEkhp7fFXf9r32rNPfb74X/U90Bdy4lzp3+X1ukh1BuMxA/EEhDoTOS3l
7ABvc7BYSQubQ2490OcdkIzUh3ZwDrakMVrbaTxUM2p24N6dB+ns2zptWCva6jzW
r8IWKIMxzxLPv5Kt3ePKcUdvkBU/smqujSczTzzSjIoR5QqQA6lN1ZRSnuHIWCvh
JEltkYnTAH41QJ6SAWO66GrrUESwN/cgZzL4JLEqz1Y=
-----END CERTIFICATE-----
"""


def _ssl_context_para_bcv() -> ssl.SSLContext:
    """TLS con verificación: trust store + intermediario Sectigo que el BCV no envía bien."""
    cafile = None
    try:
        import certifi

        cafile = certifi.where()
    except Exception:
        cafile = None
    if cafile:
        ctx = ssl.create_default_context(cafile=cafile)
    else:
        ctx = ssl.create_default_context()
    ctx.load_verify_locations(cadata=_SECTIGO_PUBLIC_SERVER_AUTH_CA_DV_R36_PEM)
    return ctx


_MESES_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
_BLOQUE_RECUADRO = re.compile(
    r'class="[^"]*recuadro[^"]*"[\s\S]{0,1200}?<span[^>]*>([^<]+)</span>'
    r"[\s\S]{0,800}?<strong[^>]*>\s*([^<]+)\s*</strong>",
    re.IGNORECASE,
)
_USD_STRONG_RE = re.compile(
    r"(?:USD|Bs\s*/\s*USD)[\s\S]{0,500}?<strong[^>]*>\s*([\d.,]+)\s*</strong>",
    re.IGNORECASE,
)
_FECHA_CONTENT_RE = re.compile(
    r'class="[^"]*date-display-single[^"]*"[^>]*content="([^"]+)"',
    re.IGNORECASE,
)
_FECHA_VALOR_TXT_RE = re.compile(
    r"Fecha\s+Valor:\s*([^<\n]+)",
    re.IGNORECASE,
)


class BcvWidgetTasaError(RuntimeError):
    """No se pudo leer o interpretar el recuadro (bloqueo, HTML o parseo)."""


def _parse_numero_bcv(raw: str) -> Decimal:
    s = (raw or "").strip().replace("\xa0", "").replace(" ", "")
    if not s:
        raise BcvWidgetTasaError("Valor USD vacío en el recuadro BCV")
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        val = Decimal(s)
    except InvalidOperation as exc:
        raise BcvWidgetTasaError(f"Número BCV no interpretable: {raw!r}") from exc
    if val <= 0 or val >= Decimal("1000000"):
        raise BcvWidgetTasaError(f"USD BCV fuera de rango: {val}")
    return val


def _parse_fecha_valor(texto: str) -> Optional[date]:
    t = re.sub(r"\s+", " ", (texto or "").strip())
    if not t:
        return None
    iso = t.replace("Z", "+00:00")
    try:
        if "T" in iso:
            return datetime.fromisoformat(iso[:32]).date()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", iso[:10]):
            return date.fromisoformat(iso[:10])
    except ValueError:
        pass
    m = re.search(
        r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})",
        t,
        re.IGNORECASE,
    )
    if not m:
        m = re.search(
            r"(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})",
            t,
            re.IGNORECASE,
        )
    if not m:
        return None
    dia = int(m.group(1))
    mes_nom = (
        m.group(2)
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    mes = _MESES_ES.get(mes_nom)
    if not mes:
        return None
    return date(int(m.group(3)), mes, dia)


def extraer_usd_eur_y_fecha_valor(html: str) -> tuple[date, Decimal, Decimal]:
    """Parsea el recuadro: Fecha Valor + USD (BCV) + EUR (Euro), mismo día."""
    if not html or not html.strip():
        raise BcvWidgetTasaError("HTML BCV vacío")
    fecha: Optional[date] = None
    m_iso = _FECHA_CONTENT_RE.search(html)
    if m_iso:
        fecha = _parse_fecha_valor(m_iso.group(1))
    if fecha is None:
        m_txt = _FECHA_VALOR_TXT_RE.search(html)
        if m_txt:
            fecha = _parse_fecha_valor(m_txt.group(1))
    if fecha is None:
        raise BcvWidgetTasaError("No se encontró Fecha Valor en el recuadro BCV")

    usd: Optional[Decimal] = None
    eur: Optional[Decimal] = None
    for m in _BLOQUE_RECUADRO.finditer(html):
        etiqueta = re.sub(r"\s+", " ", m.group(1)).strip().upper()
        if usd is None and (
            "USD" in etiqueta or etiqueta.endswith("/USD") or "DOLAR" in etiqueta
        ):
            usd = _parse_numero_bcv(m.group(2))
        if eur is None and (
            etiqueta == "EUR"
            or "EUR" in etiqueta
            or "EURO" in etiqueta
            or etiqueta.endswith("/EUR")
        ):
            eur = _parse_numero_bcv(m.group(2))
        if usd is not None and eur is not None:
            break
    if usd is None:
        m_usd = _USD_STRONG_RE.search(html)
        if m_usd:
            usd = _parse_numero_bcv(m_usd.group(1))
    if usd is None:
        raise BcvWidgetTasaError("No se encontró USD en el recuadro BCV")
    if eur is None:
        raise BcvWidgetTasaError("No se encontró EUR en el recuadro BCV")
    return fecha, usd, eur


def extraer_usd_y_fecha_valor(html: str) -> tuple[date, Decimal]:
    """Compat: solo USD + fecha (preferir ``extraer_usd_eur_y_fecha_valor``)."""
    fecha, usd, _eur = extraer_usd_eur_y_fecha_valor(html)
    return fecha, usd


def descargar_html_portada_bcv() -> str:
    """Un GET a la portada. Falla limpio si el WAF o la red lo bloquean."""
    url = (getattr(settings, "BCV_WIDGET_URL", None) or "https://www.bcv.org.ve/").strip()
    req = Request(
        url,
        headers={
            "User-Agent": BCV_WIDGET_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-VE,es;q=0.9",
        },
        method="GET",
    )
    timeout = float(getattr(settings, "BCV_WIDGET_TIMEOUT_SECONDS", 25) or 25)
    ctx = _ssl_context_para_bcv()
    try:
        with urlopen(req, timeout=timeout, context=ctx) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            if int(status) >= 400:
                raise BcvWidgetTasaError(f"BCV HTTP {status}")
            raw = resp.read()
    except HTTPError as exc:
        raise BcvWidgetTasaError(f"BCV HTTP {exc.code}") from exc
    except URLError as exc:
        raise BcvWidgetTasaError(f"BCV no accesible: {exc.reason}") from exc
    except TimeoutError as exc:
        raise BcvWidgetTasaError("Timeout al leer portada BCV") from exc
    charset = "utf-8"
    return raw.decode(charset, errors="replace")


def sincronizar_tasa_bcv_desde_widget(db: Session) -> dict:
    """Descarga el recuadro y persiste Euro + BCV en la fecha de HOY (Caracas).

    El portada BCV puede mostrar otra «fecha valor»; igual se guarda bajo hoy
    (regla de producto: cada mañana la tasa del día).
    """
    from app.services.tasa_cambio_service import fecha_hoy_caracas

    html = descargar_html_portada_bcv()
    fecha_widget, usd, eur = extraer_usd_eur_y_fecha_valor(html)
    hoy = fecha_hoy_caracas()
    fila = aplicar_tasa_bcv_desde_widget(
        db, hoy, float(usd), valor_euro=float(eur)
    )
    logger.info(
        "[BCV_WIDGET] tasa_bcv=%s tasa_euro=%s fecha_guardada=%s "
        "fecha_valor_widget=%s fila_id=%s",
        usd,
        eur,
        hoy.isoformat(),
        fecha_widget.isoformat(),
        fila.id,
    )
    return {
        "ok": True,
        "omitido": False,
        "fecha_valor": hoy.isoformat(),
        "fecha_valor_widget": fecha_widget.isoformat(),
        "tasa_bcv": str(usd),
        "tasa_euro": str(eur),
        "fila_id": fila.id,
    }


def intentar_captura_bcv_desde_widget(
    db: Session,
    *,
    omitir_fin_de_semana: bool = True,
    omitir_si_ya_hay_bcv: bool = True,
) -> dict:
    """
    Job 05:00/05:30 Caracas: GET a bcv.org.ve y guarda Euro + BCV para HOY.
    Omite fin de semana o si hoy ya tiene ambas tasas.
    """
    from app.services.tasa_cambio_service import (
        es_fin_de_semana_caracas,
        fecha_hoy_caracas,
        fila_tasa_multifuente_completa_hoy,
        obtener_tasa_por_fecha_sin_fin_semana,
    )

    if omitir_fin_de_semana and es_fin_de_semana_caracas():
        return {
            "ok": True,
            "omitido": True,
            "razon": "fin_de_semana",
            "mensaje": "Fin de semana Caracas: el bot no consulta el BCV.",
        }

    hoy = fecha_hoy_caracas()
    if omitir_si_ya_hay_bcv:
        ya = obtener_tasa_por_fecha_sin_fin_semana(db, hoy)
        if ya is not None and fila_tasa_multifuente_completa_hoy(ya):
            return {
                "ok": True,
                "omitido": True,
                "razon": "bcv_ya_cargado",
                "fecha_valor": hoy.isoformat(),
                "mensaje": (
                    f"Ya hay Euro y BCV válidos para {hoy.isoformat()} "
                    "(tasa del día)."
                ),
            }

    return sincronizar_tasa_bcv_desde_widget(db)
