# Reglas de negocio: no duplicados

Reglas obligatorias en todo el sistema (crear, actualizar, carga masiva).

---

## 1. Pagos: documento no duplicado

**Regla:** No puede existir más de un pago con el mismo **número de documento** (referencia de pago). Cualquier formato (BNC/, ZELLE/, numérico, etc.) se normaliza; la clave canónica no puede repetirse.

**Dónde se cumple:**

| Lugar | Cómo |
|-------|------|
| **Modelo** | `app/models/pago.py`: columna `numero_documento` con `unique=True`. |
| **Crear pago** | `backend/app/api/v1/endpoints/pagos.py`: `_numero_documento_ya_existe()` antes de insertar → **409** si ya existe. |
| **Actualizar pago** | Mismo endpoint: al cambiar `numero_documento` se comprueba contra otros pagos (excluyendo el actual) → **409** si duplicado. |
| **Carga masiva Excel** | `upload_excel_pagos`: documentos del archivo se validan contra BD y contra el propio archivo; filas con documento duplicado van a `pagos_con_errores`. |
| **Frontend** | `pagoExcelValidation`: validación de documento duplicado en archivo; al guardar, 409 se muestra como "documento ya existe". |

**Mensaje al usuario:** *"Ya existe un pago con ese Nº de documento. Regla general: no se aceptan duplicados en documentos."*

---

## 2. Clientes: cédula no duplicada

**Regla:** No puede existir más de un cliente con la misma **cédula**.  
**Excepción:** La cédula `Z999999999` puede repetirse (clientes sin cédula / placeholder).

**Dónde se cumple:**

| Lugar | Cómo |
|-------|------|
| **Crear cliente** | `backend/app/api/v1/endpoints/clientes.py` en `create_cliente`: si `cedula != "Z999999999"` y ya existe en BD → **409**. |
| **Actualizar cliente** | `_perform_update_cliente`: si se cambia cédula y coincide con otro cliente (otro id) → **409**. |
| **Carga masiva Excel** | `upload_clientes_excel`: se cargan `cedulas_existentes` (BD) y `cedulas_en_lote` (archivo); si la cédula está en alguno → error *"Cédula duplicada (existe en BD o en este lote)"* y la fila va a `clientes_con_errores`. |
| **Frontend (carga masiva)** | `useExcelUpload`: detección de cédulas duplicadas en archivo; `checkCedulas` antes de guardar; 409 al crear. |

**Mensaje al usuario:** *"Ya existe un cliente con la misma cédula"* / *"Cédula duplicada (existe en BD o en este lote)"*.

---

## Resumen

| Módulo   | Campo único        | Excepción     | 409 / rechazo |
|----------|--------------------|---------------|----------------|
| **Pagos**    | `numero_documento` | —             | Sí en create, update y carga masiva |
| **Clientes** | `cedula`           | `Z999999999`  | Sí en create, update y carga masiva |

Al añadir nuevos endpoints o flujos (p. ej. importaciones, APIs externas), hay que aplicar las mismas validaciones para mantener estas reglas.
