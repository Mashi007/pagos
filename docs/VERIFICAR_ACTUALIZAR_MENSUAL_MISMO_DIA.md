# Verificar y actualizar tablas de amortización MENSUAL (mismo día cada mes)

## 1. Verificación con SQL

**Detalle:** préstamos MENSUAL con cuotas cuyo vencimiento no coincide con la regla "mismo día cada mes" (fecha_base + N meses):

```bash
# Desde DBeaver/pgAdmin o psql, ejecutar:
sql/verificar_mensual_mismo_dia.sql
```

Devuelve filas: `prestamo_id`, `cuota_id`, `numero_cuota`, `actual_vencimiento`, `esperado_vencimiento`.

**Resumen:** total de préstamos MENSUAL y cuántos tienen al menos una cuota desactualizada:

```bash
sql/resumen_mensual_desactualizados.sql
```

- `fecha_base` = `fecha_aprobacion` (cast a date) o `fecha_base_calculo`.
- Solo se consideran préstamos con `modalidad_pago = 'MENSUAL'` y con `fecha_aprobacion` o `fecha_base_calculo` no nulos.

## 2. Actualizar cuotas desactualizadas (script)

El script **borra** las cuotas del préstamo y las **regenera** con la lógica actual (mismo día cada mes para MENSUAL).

**Desde la carpeta `backend`** (con el venv activo):

```bash
# Solo listar préstamos a actualizar, sin modificar la BD
python actualizar_amortizacion_mensual.py --dry-run

# Actualizar todos los que tengan cuotas desactualizadas
python actualizar_amortizacion_mensual.py

# Limitar a los primeros N préstamos (por ejemplo 10)
python actualizar_amortizacion_mensual.py --limit 10
```

Requisitos: que la app pueda importar `app.api.v1.endpoints.prestamos` (misma lógica que el endpoint de aprobación manual que borra y regenera cuotas).

## 3. Resumen

| Paso | Acción |
|------|--------|
| Verificar | Ejecutar `verificar_mensual_mismo_dia.sql` y/o `resumen_mensual_desactualizados.sql` |
| Actualizar | Ejecutar `actualizar_amortizacion_mensual.py` (opcional `--dry-run` y `--limit N`) |

Tras la actualización, volver a ejecutar el SQL de verificación; no deberían quedar filas desactualizadas para MENSUAL.
