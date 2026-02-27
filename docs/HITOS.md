# Hitos del proyecto

Registro de hitos y logros relevantes del proyecto Rapicredit / Pagos.

---

## 2026-02-27 — Asignación automática de crédito en carga masiva

**Estado:** ✅ Completado

### Descripción

Se resolvió el problema por el cual **no se asignaba automáticamente el número de crédito** al subir un Excel de pagos en la carga masiva. Las filas con cédula válida y un único préstamo activo (APROBADO/DESEMBOLSADO) ahora reciben el `prestamo_id` correcto sin intervención manual.

### Cambios realizados

- **Normalización de cédula** (`frontend/src/utils/pagoExcelValidation.ts`):
  - `cedulaParaLookup`: si el valor son solo **8 dígitos** (Excel guarda cédula como número y se pierde la "V"), se normaliza a `"V" + dígitos` para que la cédula entre en el batch y en el lookup.
  - Eliminación de espacios en la cédula antes de validar (`replace(/\s+/g, '')`).
- **Lookup unificado**: `cedulaLookupParaFila` usa únicamente `cedulaParaLookup(cedula)` y `cedulaParaLookup(numero_documento)`, de modo que la clave de búsqueda coincide con las claves del mapa `prestamosPorCedula` (evita desajustes por formato).
- **Columna Crédito vs número de documento** (trabajo previo): si en la columna Crédito del Excel viene un número de documento (ej. > 2 147 483 647), no se usa como `prestamo_id` y se deja vacío para que la auto-asignación por cédula pueda rellenar.

### Documentación asociada

- **Auditoría completa:** [AUDITORIA_ASIGNACION_AUTOMATICA_CREDITO.md](./AUDITORIA_ASIGNACION_AUTOMATICA_CREDITO.md) — flujo técnico, matriz de causas por las que no se asigna, recomendaciones y checklist.

### Criterios de éxito

- Usuario sube Excel con columna Cédula (ej. `V23107415` o `23107415`).
- En BD existe un único préstamo activo (APROBADO/DESEMBOLSADO) para esa cédula.
- La columna Crédito en la tabla de previsualización se rellena automáticamente con ese préstamo.
- No se requieren toasts de "crédito inválido" ni selección manual cuando hay un solo crédito por cédula.

---

*Se irán añadiendo nuevos hitos debajo de este bloque.*
