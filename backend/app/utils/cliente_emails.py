# -*- coding: utf-8 -*-
"""
Política de dos correos por cliente.

Cada cliente puede tener:
  - correo_1  / email            (campo `email` en tabla clientes, NOT NULL, predeterminado)
  - correo_2  / email_secundario (campo `email_secundario` en tabla clientes, nullable)

Reglas de envío para notificaciones automáticas (mora, vencimientos, previas):
  - El correo que recibe el email es SIEMPRE correo_1 (el predeterminado).
  - correo_2 se expone en los ítems del listado / API para referencia del operador y el UI;
    no se usa como destino de envío salvo que la función de despacho lo incluya explícitamente.

Funciones de este módulo:
  - emails_destino_cliente / emails_destino_desde_objeto
      → devuelven [correo_1, correo_2] (hasta 2) para casos que requieren ambos destinos.
  - lista_correo_principal_para_notificaciones / lista_correo_principal_notificaciones_desde_objeto
      → devuelven [correo_1] solamente; usar para el campo `To:` en notificaciones automáticas.
  - secundario_distinto_del_principal
      → normaliza y verifica que correo_2 no sea idéntico a correo_1 antes de guardarlo o mostrarlo.
  - algun_email_coincide
      → útil al cruzar un remitente o lista con correo_1 y correo_2 en BD (mismo orden de prioridad).

Escaneo Gmail / digitalización de pagos (plantillas Mercantil, BNC, Binance, BDV, NR, etc.):
  En flujo normal la cédula del Excel **no** sale de la imagen; el backend resuelve el cliente comparando el **From** (De)
  con `clientes.email` (predeterminado); si no hay coincidencia, con `clientes.email_secundario` si no está vacío.
  Excepción: con **scan_filter=error_email_rescan**, plantillas **A/B** pueden llevar cédula leída de la imagen (Gemini); el resto igual por remitente.
  Si tampoco coincide: la columna **Cédula** del Excel queda **ERROR EMAIL** y en Gmail **únicamente** la etiqueta **ERROR EMAIL**
  en ese paso (no inventar cédula; no combinar con MANUAL, OTROS, etc.). Si coincide el remitente, aplican plantillas y demás reglas. Ver `app.services.pagos_gmail.pipeline`.
"""
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence


def _norm_email(s: Optional[str]) -> str:
    return (s or "").strip()


def emails_destino_cliente(
    email: Optional[str],
    email_secundario: Optional[str],
    *,
    max_destinos: int = 2,
) -> List[str]:
    """
    Lista ordenada de correos válidos y distintos (comparación sin distinguir mayúsculas),
    máximo `max_destinos` (por defecto 2). Orden: primero correo 1 (`email`), luego correo 2 (`email_secundario`).
    """
    out: List[str] = []
    seen_lower: set[str] = set()
    for raw in (email, email_secundario):
        e = _norm_email(raw)
        if not e or "@" not in e:
            continue
        key = e.lower()
        if key in seen_lower:
            continue
        seen_lower.add(key)
        out.append(e)
        if len(out) >= max_destinos:
            break
    return out


def emails_destino_desde_objeto(cliente: object, *, max_destinos: int = 2) -> List[str]:
    """Lee correo 1 y correo 2 (atributos `email` y `email_secundario`) de un ORM Cliente o dict-like."""
    em = getattr(cliente, "email", None)
    sec = getattr(cliente, "email_secundario", None)
    return emails_destino_cliente(
        em if isinstance(em, (str, type(None))) else str(em) if em is not None else None,
        sec if isinstance(sec, (str, type(None))) else str(sec) if sec is not None else None,
        max_destinos=max_destinos,
    )


def lista_correo_principal_para_notificaciones(email: Optional[str]) -> List[str]:
    """
    Lista con 0 o 1 dirección válida: solo la columna principal `email` del cliente.
    No usa `email_secundario` (envíos de notificaciones: un solo destino, sin confusiones).
    """
    e = _norm_email(email)
    if not e or "@" not in e:
        return []
    return [e]


def lista_correo_principal_notificaciones_desde_objeto(cliente: object) -> List[str]:
    """Igual que lista_correo_principal_para_notificaciones leyendo `email` del ORM o dict-like."""
    em = getattr(cliente, "email", None)
    s = em if isinstance(em, (str, type(None))) else str(em) if em is not None else None
    return lista_correo_principal_para_notificaciones(s)


def secundario_distinto_del_principal(
    email: Optional[str], email_secundario: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    """
    Devuelve (correo_1_norm, correo_2_norm_o_None).
    Si correo 2 está vacío o es igual a correo 1 (sin distinguir mayúsculas), correo 2 -> None.
    """
    p = _norm_email(email)
    s = _norm_email(email_secundario)
    if not s:
        return (p or None, None)
    if p and s.lower() == p.lower():
        return (p or None, None)
    return (p or None, s or None)


def unir_destinatarios_log(emails: Sequence[str], max_len: int = 255) -> str:
    """Cadena para auditoría (envios_notificacion.email, correo_enviado_a, etc.)."""
    parts = [e.strip() for e in emails if e and "@" in e.strip()]
    if not parts:
        return ""
    s = ";".join(parts)
    return s[:max_len] if len(s) > max_len else s


def algun_email_coincide(emails_buscar: Iterable[str], email_bd: Optional[str], email_sec_bd: Optional[str]) -> bool:
    """True si algún email de la lista coincide con correo 1 o correo 2 en BD (trim, lower)."""
    cand = {_norm_email(x).lower() for x in emails_buscar if _norm_email(x) and "@" in _norm_email(x)}
    if not cand:
        return False
    for stored in (email_bd, email_sec_bd):
        t = _norm_email(stored).lower()
        if t and t in cand:
            return True
    return False
