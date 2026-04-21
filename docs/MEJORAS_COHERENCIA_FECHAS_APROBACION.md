# Mejoras de coherencia: fechas en préstamos

## Regla única vigente

- `fecha_aprobacion` es la fecha fuente para aprobación/desembolso.
- `fecha_base_calculo` se copia automáticamente desde `date(fecha_aprobacion)`.
- `fecha_requerimiento` se calcula automáticamente como `date(fecha_aprobacion) - 1 día`.
- No se permite edición manual aislada de `fecha_base_calculo` ni de `fecha_requerimiento`.

## Aplicación en backend

- `PUT /prestamos/{id}`:
  - bloquea `fecha_base_calculo` sin `fecha_aprobacion` (400).
  - bloquea edición manual de `fecha_requerimiento` (400).
  - al recibir `fecha_aprobacion`, deriva `fecha_base_calculo` y `fecha_requerimiento`.
- `revision_manual`:
  - ignora `fecha_requerimiento` manual.
  - al cambiar `fecha_aprobacion`, recalcula `fecha_base_calculo` y `fecha_requerimiento`.
- Carga masiva (Drive/Excel):
  - usa `fecha_aprobacion` como dato clave.
  - deriva automáticamente `fecha_requerimiento`.

## Aplicación en frontend

- Formularios y servicios de préstamos no dependen de validaciones `aprobación >= requerimiento`.
- `fecha_requerimiento` se muestra como derivada y no como dato manual en los flujos principales.
- Validación de Excel prioriza `fecha_aprobacion`; `fecha_requerimiento` se autocompleta desde esa fecha.

## Nota operativa de verificación

- Consulta de control recomendada:
  - `date(fecha_aprobacion) = fecha_base_calculo`
  - `fecha_requerimiento = date(fecha_aprobacion) - 1 día`
