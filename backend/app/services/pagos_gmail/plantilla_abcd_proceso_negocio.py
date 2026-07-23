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
PAGOS_GMAIL_MOTIVO_USUARIO_OPERACIONES = "usuario_operaciones"
EMAIL_BINANCE_USUARIO_OPERACIONES = "operaciones@rapicreditca.com"


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
