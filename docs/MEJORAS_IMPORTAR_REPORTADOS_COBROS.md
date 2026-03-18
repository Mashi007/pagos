# Mejoras posibles: Importar reportados aprobados (Cobros)

## Implementadas (reciente)

1. **Duplicados por documento en BD**  
   Los registros cuyo Nº documento ya existe en la tabla `pagos` ahora se insertan en `datos_importados_conerrores` y se incluyen en el conteo de "con error", de modo que aparecen en el Excel de errores y el total es coherente.

2. **Docstring del endpoint**  
   Corregido: se indica que los fallos van a `datos_importados_conerrores` (y descargar Excel desde el frontend), no a "Revisar Pagos".

3. **Cuotas aplicadas en la UI**  
   El frontend muestra `cuotas_aplicadas` en el toast de éxito y en la tarjeta de resumen cuando hay registros con error (ej.: "X importados (Y cuotas aplicadas); Z con error...").

---

## Recomendaciones futuras

### Créditos activos: APROBADO y otros estados

- Hoy solo se consideran préstamos con `estado == "APROBADO"`. Si el negocio usa otro estado para créditos activos (ej. `DESEMBOLSADO`), conviene:
  - Definir una constante o lista de estados “activos” (ej. `("APROBADO", "DESEMBOLSADO")`).
  - Usarla en importación desde Cobros y en carga masiva Excel para mantener el mismo criterio.

### Varios préstamos por cédula

- Si el cliente tiene más de un préstamo APROBADO, el registro va a error: "Cédula con N préstamos; indique ID del crédito".
- Mejora posible:
  - Añadir campo opcional `prestamo_id` en `pagos_reportados` (y en la UI de Cobros al aprobar).
  - En la importación, si viene `prestamo_id` y pertenece al cliente, usarlo aunque haya varios préstamos; si no viene o no es válido, mantener el comportamiento actual (error y a datos con error).

### Transacción y rollback

- Si `_aplicar_pago_a_cuotas_interno` falla para un pago concreto, se registra un warning y se sigue con el resto; el `commit` incluye todos los pagos creados. Algunos podrían quedar en `PENDIENTE` sin aplicación a cuotas.
- Opción: en caso de excepción al aplicar, dar de baja ese pago (rollback de ese insert) y llevarlo a `datos_importados_conerrores` con mensaje "Error al aplicar a cuotas", para que el usuario lo vea en el Excel y pueda reintentar o corregir.

### Diálogo opcional “¿Descargar Excel?”

- Según `docs/IMPORTAR_REPORTADOS_DIALOGO_EXCEL.md`, cuando `total_datos_revisar > 0` se podría mostrar un diálogo: "Hay datos que revisar, ¿quieres descargar Excel?" con botones Descargar / Cerrar.
- Actualmente la tarjeta amarilla ya ofrece el botón "Descargar Excel (errores de esta importación)"; el diálogo sería una variante de UX para destacar la opción justo después de importar.

### Endpoint GET datos-revisar

- Existe `GET /api/v1/pagos/importar-desde-cobros/datos-revisar` (`tiene_datos`, `total`). Se puede usar al cargar la página de Pagos para mostrar un aviso si quedaron datos pendientes de revisar de una importación anterior (ej. banner: "Tienes N registros con error de una importación anterior; descargar Excel").
