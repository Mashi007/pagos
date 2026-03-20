# Paso 3 — Regeneración de cuotas en DBeaver

## Prerrequisitos

1. **Backup opción A** (`scripts/backup_bd_opcion_a.py` o `pg_dump -Fc`) guardado y comprobado.
2. Ejecutar **`dbeaver_01_funciones_y_verificaciones.sql`** (crea `fn_add_months_keep_day` y `fn_monto_cuota_frances`).
3. Revisar que **`prestamos.numero_cuotas`** y **`total_financiamiento`** reflejen el negocio (especialmente casos con más filas en `cuotas` de las declaradas).

## Archivo a ejecutar

- **`dbeaver_02_regeneracion_DESTRUCTIVA.sql`**

## Configuración (elegir una)

En la sección **CONFIG** del script:

- **Piloto:** comentar el `INSERT` masivo, descomentar el `INSERT` con `unnest(ARRAY[...])` y poner **pocos** `prestamo_id`.
- **Masivo:** dejar activo solo el `INSERT` que llena desde `prestamos` (como está por defecto en el archivo).

Opcional: descomentar `SELECT COUNT(*) FROM _regen_scope` (sustituir el comentario por la consulta) para ver cuántos préstamos se afectan **antes** del `DELETE`.

## Tras el `COMMIT` exitoso

1. Volver a aplicar pagos a cuotas: **`POST /api/v1/prestamos/conciliar-amortizacion-masiva`**
   - Si fue **piloto**, enviar `prestamo_ids` con los mismos IDs.
   - Requiere autenticación según tu despliegue (token / sesión).

2. Post-chequeo en SQL: repetir las consultas §3–§4 de `dbeaver_01` (desalineación cuota 1 → idealmente 0 filas).

## Si algo falla

- Si la transacción aún no hizo `COMMIT`, usar **`ROLLBACK`**.
- Restaurar desde el backup si ya se confirmó un estado incorrecto en producción.
