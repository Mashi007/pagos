# Auditoría integral: fecha de aprobación y tabla de amortización

**Objetivo:** Verificar bajo una misma lógica que (1) todos los préstamos que deben tener fecha de aprobación la tienen, (2) la tabla de amortización se genera con esa fecha como base, y (3) no hay incoherencias ni roturas de integridad.

**SQL:** `sql/auditoria_integral_fecha_aprobacion_amortizacion.sql`

---

## 1. Alcance de la auditoría

| Área | Qué se verifica |
|------|------------------|
| **Préstamos y fecha_aprobacion** | Que todo préstamo APROBADO tenga `fecha_aprobacion`; conteo por estado. |
| **Coherencia de fechas** | Que no exista aprobación anterior a requerimiento; opcional: `fecha_base_calculo` vs `fecha_aprobacion`. |
| **Tabla de amortización** | Préstamos APROBADOS sin cuotas; discrepancia entre `numero_cuotas` y cantidad real de cuotas; primera cuota coherente con fecha base. |
| **Integridad referencial** | Préstamos con cliente inexistente o sin cédula; cuotas huérfanas o con `prestamo_id` inválido; pagos con `prestamo_id` inválido. |
| **Resumen ejecutivo** | Una sola consulta que devuelva indicadores clave para monitoreo. |

---

## 2. Reglas de negocio asumidas

- **Fecha base de la tabla de amortización:** `fecha_base_calculo` > `fecha_aprobacion` > `fecha_requerimiento` > hoy. En la práctica, para préstamos APROBADOS se espera `fecha_aprobacion` (o `fecha_base_calculo` si se fijó).
- **APROBADO sin fecha_aprobacion:** inconsistencia; debería corregirse (Revisión Manual / asignar fecha).
- **APROBADO sin cuotas:** permitido temporalmente; se pueden generar con “Generar cuotas” o “Asignar fecha aprobación”.
- **Aprobación antes que requerimiento:** incoherencia lógica; solo informativa para revisión.

---

## 3. Cómo ejecutar el SQL

```bash
psql "DATABASE_URL" -f sql/auditoria_integral_fecha_aprobacion_amortizacion.sql
```

O abrir el archivo en un cliente PostgreSQL y ejecutar cada bloque. Las consultas están numeradas y pueden ejecutarse por partes.

---

## 4. Interpretación rápida

- **Resumen ejecutivo (primera consulta):** si `aprobados_sin_fecha_aprobacion = 0`, `cuotas_huérfanas = 0`, `pagos_prestamo_invalido = 0` y `prestamos_sin_cliente_cedula = 0`, la integridad y la regla de fecha de aprobación se cumplen a nivel global.
- **Listados detallados:** sirven para corregir registros concretos (IDs de préstamos, cuotas o pagos a revisar).

---

## 5. Relación con el código

- La generación de cuotas en backend usa la prioridad de fechas indicada (ver `prestamos.py`: `generar_amortizacion`, `create_prestamo`, `aplicar_condiciones_aprobacion`, `asignar_fecha_aprobacion`, etc.).
- El endpoint `GET /api/v1/health/integrity` comprueba parte de esta lógica (préstamos sin cliente/cédula, cuotas/pagos con referencias inválidas, préstamos APROBADOS sin cuotas). Este SQL amplía esa verificación e incluye explícitamente la existencia de `fecha_aprobacion` y la coherencia con la primera cuota.

---

## 6. Diagnóstico final (ejecución 2025)

### 6.1 Resultados verificados

| Consulta | Resultado | Estado |
|----------|-----------|--------|
| Resumen ejecutivo | 5150 préstamos, 5150 aprobados; 0 sin fecha_aprobacion; 0 aprobados sin cuotas; 0 cuotas huérfanas; 0 pagos con prestamo inválido; 0 préstamos sin cliente/cédula | OK salvo 1280 con aprobación &lt; requerimiento |
| A1 (con/sin fecha_aprobacion) | 5150 con, 0 sin | OK |
| A2 (APROBADOS sin fecha) | 0 filas | OK |
| A3 (por estado) | 5150 APROBADO, todos con fecha_aprobacion | OK |
| B1 (aprobación &lt; requerimiento) | 1280 préstamos | Revisar / corregir |
| C3 (numero_cuotas vs real) | 3 préstamos (ids 2, 7, 8): más cuotas en tabla que numero_cuotas | Revisar |
| C4/D3 (cuotas huérfanas) | 0 filas | OK |
| D1 (préstamos sin cliente/cédula) | 0 filas | OK |
| D4 (pagos prestamo inválido) | 0 filas | OK |
| E (totales) | 5150 prestamos, 62599 cuotas, 24911 pagos, 5031 clientes | Coherente |

### 6.2 Pendiente opcional por ejecutar

- **B2:** Préstamos con `fecha_base_calculo` distinta de `fecha_aprobacion` (informativo; no bloquea).
- **C1:** Aprobados sin cuotas (ya 0 en resumen).
- **C2:** Con cuotas pero sin fecha_aprobacion (ya 0).
- **C5:** Coherencia primera cuota vs fecha_aprobacion (muestra masiva; útil para muestreo de vencimientos).
- **D2:** Cuotas con `prestamo_id` NULL (ya cubierto por C4/D3 si da 0).

### 6.3 Hallazgos que requieren acción

1. **1 280 préstamos con aprobación anterior a requerimiento**  
   Patrón: `fecha_aprobacion` = 2025-10-31, `fecha_requerimiento` en nov/dic 2025. Script de corrección: `sql/corregir_aprobacion_antes_requerimiento.sql` (Opción A: igualar requerimiento a aprobación; Opción B: igualar aprobación a requerimiento — ver comentarios en el archivo).

2. **3 préstamos con discrepancia de cuotas (ids 2, 7, 8)**  
   Tienen más filas en `cuotas` que `prestamos.numero_cuotas`. Revisar si hay duplicados por `(prestamo_id, numero_cuota)` o si `numero_cuotas` debe actualizarse al valor real (54, 45, 36). Ver comentarios en sección C3 del SQL.

### 6.4 Conclusión

- **Integridad referencial:** Correcta (préstamos → clientes, cuotas → prestamos, pagos → prestamos).
- **Fecha de aprobación:** Todos los préstamos tienen `fecha_aprobacion`; la tabla de amortización puede basarse en ella según el código.
- **Ajustes recomendados:** (1) Corregir los 1 280 casos de aprobación &lt; requerimiento con el script opcional; (2) Revisar los 3 préstamos con discrepancia en número de cuotas y alinear `numero_cuotas` o eliminar cuotas duplicadas con criterio de negocio.
