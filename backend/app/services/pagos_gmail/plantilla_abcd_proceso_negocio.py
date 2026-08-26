# -*- coding: utf-8 -*-
"""
Reglas de negocio **innegociables** para comprobantes Gmail plantilla **A / B / C / D**
(mapeo fijo: **A → MERCANTIL**, **B → BNC**, **C → BINANCE**, **D → BNV**).

Alcance principal **A–D** en este documento. **NR** (no RapiCredit) comparte duplicado por documento;
el alta automática NR está en `pago_nr_auto_service` (requiere `monto_operacion` desde Gemini).

---

### 1) Autoconciliados (regla fundamental)

Un pago originado por estas plantillas debe registrarse en el sistema como **conciliado**
(`pagos.conciliado = true`) en el momento en que se acepta como pago operativo válido,
**antes** o **junto** con la aplicación a cuotas, según la misma política que el resto de
pagos conciliados del módulo (ver listados y elegibilidad en `pagos.py`).

*Implementación técnica:* crear el registro en `pagos` con los mismos validadores que la
carga manual / API (`PagoCreate`, huella funcional, `numero_documento`, moneda USD, etc.)
y marcar `conciliado` acorde a las reglas existentes del CHECK de estado.

---

### 2) Carga automática a cuotas

Tras existir el `Pago` válido y asociado a `prestamo_id`, la aplicación a cuotas sigue la
**cascada por `numero_cuota` ascendente** (cuotas más antiguas primero), reutilizando la
misma mecánica que `POST /pagos/{id}/aplicar-cuotas` → `_aplicar_pago_a_cuotas_interno`
y `aplicar_pagos_pendientes_prestamo` en `pagos.py` / `pagos_cuotas_reaplicacion.py`.

No FIFO en el sentido de “primer pago global”; la política es **cascada por préstamo**.

---

### 3) Mismo número de documento (sistema vs nuevos pagos)

Si el **número de documento / referencia** del comprobante Gmail (normalizado igual que
`pagos.numero_documento`) **ya existe** en `pagos` o `pagos_con_errores`, el ítem **no**
debe seguir el flujo automático de alta + cuotas: permanece en `gmail_temporal` y, tras
el pipeline, pasa a **revisión manual** en `pagos_con_errores` (migración automática o
`POST /pagos/gmail/migrar-pendientes-a-con-errores`).

*Este módulo expone* `referencia_ya_registrada_como_numero_documento` *para detectar ese caso.*

Los ítems que **no** están duplicados y pasan validadores siguen el proceso normal
(conciliación + cuotas cuando la integración Gmail→`pagos` esté cableada).

---

### Integración Gmail → `pagos` (plantilla A–D)

Tras `commit` de sync/temporal + comprobante, si el serial **no** está duplicado, el pipeline
invoca `pago_abcd_auto_service.crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd`
(reutiliza `resolver_monto_registro_pago`, `conflicto_huella_para_creacion`,
`_aplicar_pago_a_cuotas_interno` y `_estado_conciliacion_post_cascada` de `pagos.py`).
Para **NR** con `monto_operacion` numérico (Gemini), invoca `pago_nr_auto_service.crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_nr`
(mismas validaciones de préstamo único, documento, huella y cuotas).
Requisito de préstamo: **un solo** crédito `APROBADO` por cédula (igual que carga masiva Excel);
si hay 0 o varios, no se inserta `Pago` (revisión manual / `pagos_con_errores`).

---

### 4) Monto alto (>= 1000)

Si el valor numérico del comprobante (columna `monto` / `monto_operacion`, sin importar
moneda en el texto: USD, Bs, USDT, etc.) es **igual o mayor a 1000**, el ítem **no** sigue
alta automática ni el botón **Guardar** del módulo Actualizaciones > Gmail: permanece para
**revisión manual** (vía **Editar** → `pagos_con_errores` → modal de revisión).

*Implementación:* `monto_gmail_sync_requiere_revision_manual_usd` en este módulo; usada en
pipeline, `pago_abcd_auto_service`, `pago_nr_auto_service` y `guardar_sync_item`.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session

from app.services.pago_numero_documento import numero_documento_ya_registrado
from app.services.pagos_gmail.helpers import format_monto_excel_pagos_gmail
from app.services.pagos_gmail.parse_campos_comprobante import (
    MONTO_UMBRAL_REVISION_MANUAL,
    monto_requiere_revision_manual,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Umbral numerico: pagos >= este valor van a revision manual (sin distinguir moneda).
PAGOS_GMAIL_UMBRAL_REVISION_MANUAL_USD = Decimal(str(MONTO_UMBRAL_REVISION_MANUAL))

# Binance Pay (C): correo beneficiario operaciones@ debe verse arriba del ID de orden.
PAGOS_GMAIL_OBS_USUARIO_OPERACIONES = "Usuario operaciones"
# Texto de cola / listado: misma marca + discrepancia exacta legible.
PAGOS_GMAIL_OBS_USUARIO_OPERACIONES_DETALLE = (
    "Usuario operaciones: no se ve operaciones@rapicreditca.com "
    "arriba del ID de orden"
)
PAGOS_GMAIL_OBS_FECHA_IMAGEN = "Fecha: no legible/ambigua en imagen (no inventar hoy ni asunto); revision manual"
PAGOS_GMAIL_MOTIVO_USUARIO_OPERACIONES = "usuario_operaciones"
EMAIL_BINANCE_USUARIO_OPERACIONES = "operaciones@rapicreditca.com"


def _fmt_val_obs_binance(val: object, *, max_len: int = 48) -> str:
    s = " ".join(str(val if val is not None else "").split()).strip()
    if not s or s.upper() in ("NA", "N/A", "NONE", "NULL"):
        return "(vacío)"
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def construir_comentario_discrepancia_binance(
    form_compare: dict | None,
    *,
    comentario: str | None,
    extraccion: dict | None = None,
    control_usuario_operaciones: object = None,
) -> str:
    """
    Observación Binance con discrepancia exacta (formulario vs imagen).

    Conserva la marca «Usuario operaciones» para matching de cola; añade
    detalle form=… / imagen=… cuando hay extracción.
    """
    form = form_compare if isinstance(form_compare, dict) else {}
    ext = extraccion if isinstance(extraccion, dict) else {}
    raw = (comentario or "").strip()
    partes: list[str] = []

    if binance_requiere_revision_usuario_operaciones(control_usuario_operaciones) or (
        raw.lower().startswith("usuario operaciones")
    ):
        partes.append(PAGOS_GMAIL_OBS_USUARIO_OPERACIONES_DETALLE)

    # Columnas cortas de Gemini → detalle form vs imagen.
    chunks: list[str] = []
    for chunk in raw.replace(",", " / ").split(" / "):
        c = chunk.strip()
        if not c:
            continue
        if c.lower().startswith("usuario operaciones"):
            continue
        chunks.append(c)

    def _add_col(label: str, form_v: object, ext_v: object) -> None:
        partes.append(
            f"{label}: form={_fmt_val_obs_binance(form_v)} / "
            f"imagen={_fmt_val_obs_binance(ext_v)}"
        )

    seen: set[str] = set()
    for chunk in chunks:
        # Ya enriquecido (re-análisis / listado).
        if "form=" in chunk.lower() and "imagen=" in chunk.lower():
            if chunk not in partes:
                partes.append(chunk)
            continue
        t = " ".join(chunk.lower().split())
        t = t.replace("ó", "o").replace("º", "o")
        t = t.replace("n o operacion", "n operacion").replace(
            "no operacion", "n operacion"
        )
        if t in seen:
            continue
        seen.add(t)
        if t in ("monto",):
            _add_col("Monto", form.get("monto"), ext.get("monto"))
        elif t in (
            "n operacion",
            "numero operacion",
            "número operacion",
            "nº operacion",
            "id de orden",
            "id. de orden",
            "id orden",
        ):
            _add_col(
                "Nº operación (Id. orden)",
                form.get("numero_operacion"),
                ext.get("numero_operacion"),
            )
        elif t in ("moneda",):
            _add_col("Moneda", form.get("moneda"), ext.get("moneda"))
        elif t in ("banco",):
            _add_col(
                "Banco",
                form.get("institucion_financiera"),
                ext.get("institucion_financiera"),
            )
        elif t in ("cedula", "cédula"):
            tipo = str(form.get("tipo_cedula") or "").strip()
            num = str(form.get("numero_cedula") or "").strip()
            form_ced = f"{tipo}{num}".strip() or form.get("cedula")
            _add_col("Cédula", form_ced, ext.get("cedula_pagador"))
        elif t in ("fecha pago", "fecha de pago"):
            # Binance no trae fecha en imagen; no tratar como falla de negocio.
            continue
        else:
            partes.append(chunk)

    if not partes:
        if raw:
            return raw[:500]
        return ""
    # Evitar duplicar si ya venía el detalle largo.
    out: list[str] = []
    for p in partes:
        if p not in out:
            out.append(p)
    return " / ".join(out)[:500]


def expandir_observacion_corta_binance(texto: str | None) -> str | None:
    """Expande marcas cortas ya guardadas a discrepancia legible en listado."""
    raw = (texto or "").strip()
    if not raw:
        return None
    if raw.lower() in (
        "en_revision: requiere decisión manual",
        "en_revision: requiere decision manual",
    ):
        return None
    parts_in = [p.strip() for p in raw.replace(",", " / ").split(" / ") if p.strip()]
    parts_out: list[str] = []
    for p in parts_in:
        pl = p.lower().strip()
        if pl == "usuario operaciones" or pl.startswith("usuario operaciones:"):
            if pl == "usuario operaciones":
                parts_out.append(PAGOS_GMAIL_OBS_USUARIO_OPERACIONES_DETALLE)
            else:
                parts_out.append(p)
        elif pl == "monto":
            parts_out.append("Monto: discrepancia formulario vs comprobante")
        elif pl in (
            "nº operación",
            "nº operacion",
            "n operacion",
            "numero operacion",
            "número operacion",
            "no operacion",
            "n o operacion",
        ) or "operacion" in pl or "operación" in pl:
            parts_out.append(
                "Nº operación (Id. orden): discrepancia formulario vs comprobante"
            )
        elif pl == "moneda":
            parts_out.append(
                "Moneda: discrepancia formulario vs comprobante (p.ej. USD/USDT)"
            )
        elif pl == "banco":
            parts_out.append("Banco: discrepancia formulario vs comprobante")
        elif pl in ("cédula", "cedula"):
            parts_out.append("Cédula: discrepancia formulario vs comprobante")
        elif pl in ("fecha pago", "fecha de pago"):
            continue
        else:
            parts_out.append(p)
    if not parts_out:
        return None
    return " / ".join(parts_out)


def _coerce_bool_control_usuario_operaciones(val: object) -> Optional[bool]:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("true", "1", "si", "sí", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def binance_control_usuario_operaciones_cumple(val: object) -> bool:
    """True solo si Gemini devolvió control_usuario_operaciones=true explícitamente."""
    return _coerce_bool_control_usuario_operaciones(val) is True


def binance_requiere_revision_usuario_operaciones(val: object) -> bool:
    """True si falta el control o Gemini marcó false (revisión manual / pagos reportados)."""
    return not binance_control_usuario_operaciones_cumple(val)


_FECHA_GMAIL_VACIA = frozenset({"", "NA", "N/A", "-", "NONE", "NULL"})


def es_gmail_plantilla_binance(*, fmt: str | None = None, banco: str | None = None) -> bool:
    """True si el ítem Gmail es plantilla C / columna BINANCE."""
    if (fmt or "").strip().upper() == "C":
        return True
    return (banco or "").strip().upper() == "BINANCE"


def _fecha_gmail_texto_vacia(fecha_str: str | None) -> bool:
    return (fecha_str or "").strip().upper() in _FECHA_GMAIL_VACIA


def fecha_hoy_gmail_binance_str() -> str:
    """DD/MM/YYYY hoy Caracas — fecha operativa cuando Binance Pay no trae fecha en imagen."""
    from app.utils.dias_laborales_caracas import fecha_hoy_caracas

    return fecha_hoy_caracas().strftime("%d/%m/%Y")


def completar_fecha_gmail_binance_si_ausente(fecha_str: str | None) -> str:
    """Plantilla C: NA/vacía → hoy Caracas; otros bancos no aplican aquí."""
    if _fecha_gmail_texto_vacia(fecha_str):
        return fecha_hoy_gmail_binance_str()
    return (fecha_str or "").strip()


def fecha_pago_date_gmail_plantilla_c(fecha_str: str | None):
    """
    Fecha para alta ABCD plantilla C.

    Binance Pay no incluye fecha en la captura: si Gemini devolvió NA/vacío, usa hoy Caracas.
    Si trae fecha legible, se respeta.
    """
    from datetime import datetime

    from app.services.pagos_gmail.helpers import normalizar_fecha_pago
    from app.utils.dias_laborales_caracas import fecha_hoy_caracas

    raw = (fecha_str or "").strip()
    if _fecha_gmail_texto_vacia(raw):
        return fecha_hoy_caracas()
    norm = normalizar_fecha_pago(raw)
    for cand in (norm, raw):
        if _fecha_gmail_texto_vacia(cand):
            continue
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(cand[:10], fmt).date()
            except ValueError:
                continue
    return fecha_hoy_caracas()


# Plantillas de comprobante bancario (Gemini) cubiertas por este proceso.
PLANTILLAS_BANCO_ABCD = frozenset({"A", "B", "C", "D"})

# Valores de columna `banco` / Excel alineados con el pipeline (`resolve_banco_para_excel_pagos_gmail`).
BANCOS_PLANTILLA_ABCD = frozenset(
    {
        "Mercantil",
        "BNC",
        "BINANCE",
        "BDV",
        "BNV",
    }
)


def monto_gmail_sync_requiere_revision_manual_usd(monto_str: Optional[str]) -> bool:
    """
    True si el valor numerico parseado del comprobante es >= umbral
    (cualquier moneda en el texto: USD, Bs, USDT, etc.; sin convertir).
    """
    raw = (monto_str or "").strip()
    if not raw or raw.upper() in ("NA", "NR"):
        return False
    txt = format_monto_excel_pagos_gmail(monto_str)
    if txt:
        return monto_requiere_revision_manual(txt)
    return monto_requiere_revision_manual(monto_str)


def es_plantilla_banco_abcd(fmt: str) -> bool:
    return (fmt or "").strip().upper() in PLANTILLAS_BANCO_ABCD


def es_banco_columna_plantilla_abcd(banco: str | None) -> bool:
    """True si la columna banco del ítem Gmail corresponde a plantilla A/B/C/D."""
    b = (banco or "").strip()
    if not b:
        return False
    # BNV vs BDV: ambos cubren plantilla D en distintos despliegues.
    if b.upper() == "BNV" or b.upper() == "BDV":
        return True
    return b in BANCOS_PLANTILLA_ABCD


def referencia_ya_registrada_como_numero_documento(db: Session, referencia: str | None) -> bool:
    """
    True si la referencia del comprobante coincide (tras normalización interna)
    con un `pagos.numero_documento` o `pagos_con_errores` ya almacenado.
    """
    return numero_documento_ya_registrado(db, referencia)


def item_sync_nr_candidato_revision_duplicado(
    *,
    referencia: str | None,
    db: Session,
) -> bool:
    """Plantilla NR: mismo criterio de duplicado por serial/referencia que A–D."""
    return referencia_ya_registrada_como_numero_documento(db, referencia)


def resumen_log_linea_plantilla_abcd(
    *,
    duplicado_documento: bool = False,
    revision_manual_monto: bool = False,
    revision_manual_usuario_operaciones: bool = False,
) -> str:
    """Texto de log por fila (no describe la ruta de filas ya conciliadas en CUOTAS_OK)."""
    partes = ["ABCD: autoconciliado + cascada cuotas (mismo código /pagos)"]
    if duplicado_documento:
        partes.append("duplicado por documento → revisión manual (pagos_con_errores)")
    if revision_manual_usuario_operaciones:
        partes.append(
            f"Binance sin {EMAIL_BINANCE_USUARIO_OPERACIONES} arriba del ID → revisión manual"
        )
    if revision_manual_monto:
        partes.append(
            f"monto >= {PAGOS_GMAIL_UMBRAL_REVISION_MANUAL_USD} → revisión manual (pagos_con_errores)"
        )
    if len(partes) == 1:
        partes.append("sin bloqueo duplicado ni umbral de monto")
    return "; ".join(partes)


def item_sync_abcd_candidato_revision_duplicado(
    *,
    banco_excel: str | None,
    referencia: str | None,
    db: Session,
    fmt: str | None = None,
) -> bool:
    """
    True si la fila corresponde a banco plantilla A/B/C/D (columna `banco` en sync/temporal)
    y el serial/referencia ya existe como `pagos.numero_documento` (o en pagos_con_errores).

    `fmt` es opcional: en ítems persistidos solo existe la columna `banco`; si se pasa `fmt`
    (p. ej. desde el pipeline), debe ser A/B/C/D o no cuenta como candidato ABCD.
    """
    if fmt is not None and not es_plantilla_banco_abcd(fmt):
        return False
    if not es_banco_columna_plantilla_abcd(banco_excel):
        return False
    if referencia_ya_registrada_como_numero_documento(db, referencia):
        return True
    from app.services.cobros.pago_reportado_documento import (
        numero_operacion_colisiona_reportado_activo,
    )

    return numero_operacion_colisiona_reportado_activo(db, referencia)
