# Mejoras de coherencia: fecha de aprobación y fecha de requerimiento

## Regla

- **Fecha de aprobación** debe ser **igual o posterior** a la **fecha de requerimiento**.
- La **tabla de amortización** se calcula **únicamente con la fecha de aprobación** (no con `fecha_base_calculo` ni `fecha_requerimiento`).

## Cambios realizados

### 1. Revisión Manual (`revision_manual.py`)

- Tras aplicar los cambios de `update_data` (incluidos `fecha_requerimiento` y `fecha_aprobacion`), se valida la coherencia antes de hacer `commit`.
- Si `fecha_aprobacion < fecha_requerimiento` se devuelve **400** con mensaje claro.

### 2. PUT préstamo (`prestamos.py`)

- El endpoint `PUT /prestamos/{id}` aplica `payload.fecha_requerimiento` cuando viene en el body.
- Antes de `commit`, si el préstamo tiene `fecha_aprobacion` y `fecha_requerimiento`, se comprueba que la fecha de requerimiento no sea **posterior** a la fecha de aprobación.
- Si no se cumple, se devuelve **400**.

### 3. Modales de fecha de aprobación (frontend)

- **AsignarFechaAprobacionModal**: valor por defecto de la fecha de aprobación:
  - Si ya existe `fecha_aprobacion` → se usa.
  - Si no, y existe `fecha_requerimiento` → se usa (coherente por defecto).
  - Si no → hoy.
- **AprobarPrestamoManualModal**: valor por defecto = `fecha_requerimiento` si existe, si no hoy.

## Mejoras opcionales (futuras)

- **Script para datos legacy**: si en BD existieran préstamos con `fecha_aprobacion < fecha_requerimiento`, un script (o job) podría corregirlos (por ejemplo igualando `fecha_aprobacion` a `fecha_requerimiento` o avisando para corrección manual). En la verificación actual todos los préstamos tenían `fecha_aprobacion` coherente.
- **Tests**: añadir tests unitarios/integración para la validación de coherencia en Revisión Manual y en PUT préstamo.
