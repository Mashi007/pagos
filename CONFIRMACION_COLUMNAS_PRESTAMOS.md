# Columnas Confirmadas de la Tabla PRESTAMOS

## Confirmación de columnas verificadas desde el modelo SQLAlchemy

```
Columna Real              Tipo           Uso en SQL
─────────────────────────────────────────────────────────────
id                        Integer         PRIMARY KEY
cliente_id                Integer         FOREIGN KEY
cedula                    String(20)
nombres                   String(255)
total_financiamiento      Numeric(14,2)   Monto principal
fecha_requerimiento       Date
modalidad_pago            String(50)      DIARIA, SEMANAL, etc.
numero_cuotas             Integer         Cuotas esperadas
cuota_periodo             Numeric(14,2)
tasa_interes              Numeric(10,4)
fecha_base_calculo        Date
producto                  String(255)     ← USAR ESTA (no referencia_interna)
estado                    String(50)      APROBADO, LIQUIDADO, DRAFT
usuario_proponente        String(255)
usuario_aprobador         String(255)
observaciones             Text
informacion_desplegable   Boolean
fecha_registro            DateTime        Fecha de creacion
fecha_aprobacion          DateTime        Fecha de aprobacion
fecha_actualizacion       DateTime
concesionario             String(255)
analista                  String(255)
modelo_vehiculo           String(255)
usuario_autoriza          String(255)
ml_impago_nivel_riesgo_manual      String(50)
ml_impago_probabilidad_manual      Numeric(10,4)
concesionario_id          Integer
analista_id               Integer
modelo_vehiculo_id        Integer
valor_activo              Numeric(14,2)
ml_impago_nivel_riesgo_calculado   String(50)
ml_impago_probabilidad_calculada   Numeric(10,4)
ml_impago_calculado_en    DateTime
ml_impago_modelo_id       Integer
requiere_revision         Boolean
```

## IMPORTANTE: Cambios en SQL de verificacion

❌ **NO EXISTE:** `p.referencia_interna`

✅ **USAR ESTA:** `p.producto`

```sql
-- ANTES (INCORRECTO):
SELECT p.referencia_interna FROM prestamos p;
-- ERROR: column p.referencia_interna does not exist

-- AHORA (CORRECTO):
SELECT p.producto FROM prestamos p;
-- OK: Devuelve el nombre del producto/prestamo
```

## Archivo corregido

El nuevo archivo con columnas correctas está en:

```
sql/verificacion_cuotas_CORREGIDO.sql
```

Cambios realizados:
- Línea 19: `p.referencia_interna` → `p.producto`
- Línea 30: GROUP BY actualizado con `p.producto`
- Línea 80: `p.referencia_interna` → `p.producto`
- Línea 81: GROUP BY actualizado con `p.producto`

Todas las consultas usan ahora SOLO columnas que existen en la tabla.

## Cómo usar el SQL corregido

```sql
-- Copiar del archivo y ejecutar en DBeaver o psql
-- O ejecutar directamente:

psql -U usuario -d base_datos < sql/verificacion_cuotas_CORREGIDO.sql
```

## Próximo paso

Ejecuta el SQL `verificacion_cuotas_CORREGIDO.sql` y comparte los resultados principales:

1. **Query #1 (Resumen General):**
   - Total prestamos: ?
   - Prestamos con cuotas: ?
   - Prestamos sin cuotas: ?

2. **Query #4 (Distribucion):**
   - Completa: ?
   - Parcial: ?
   - Sin cuotas: ?

3. **Query #8 (Ejecutivo):**
   - Metrics principales
