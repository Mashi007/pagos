# Corrección Cascada: pagos a cuotas más antiguas primero

## Problema

En `/pagos/prestamos` no se cumplía la regla de negocio: **con los pagos se cubren primero las cuotas más antiguas y luego se sigue**.

- **Síntoma**: Cuota 6 aparece "Conciliado" mientras la cuota 5 (anterior) está en "Mora (>90 d)" o con pago parcial. Los pagos se estaban aplicando a la **última** cuota pendiente primero (orden inverso).
- **Causa**: En `backend/app/api/v1/endpoints/pagos.py`, la función `_aplicar_pago_a_cuotas_interno` ordenaba las cuotas pendientes con `Cuota.numero_cuota.desc()`, es decir **primero la cuota de número más alto** (LIFO en lugar de Cascada).

## Solución en código (obligatoria)

**Archivo:** `backend/app/api/v1/endpoints/pagos.py`  
**Aproximadamente línea 2072.**

**Cambiar:**

```python
.order_by(Cuota.numero_cuota.desc())  # De atras hacia delante: ultima cuota no cubierta al 100% primero
```

**Por:**

```python
.order_by(Cuota.numero_cuota.asc())  # Cascada: primero las cuotas más antiguas (numero_cuota menor), luego las siguientes
```

Con esto, todos los **nuevos** pagos (crear pago, conciliar, carga masiva, aplicar-cuotas) se aplicarán en orden correcto: cuota 1, 2, 3, … hasta agotar el monto.

## Rearticular préstamos ya afectados

Los préstamos que ya tienen datos incorrectos (cuota posterior pagada y cuota anterior en mora) hay que **rearticular**: borrar la aplicación de pagos a cuotas y volver a aplicar todos los pagos del préstamo en orden cronológico, con la lógica Cascada ya corregida.

Opciones:

1. **Script de rearticulación** (recomendado): ejecutar un script que, para un `prestamo_id` dado:
   - Borre todos los `CuotaPago` de las cuotas de ese préstamo.
   - Ponga a 0 `total_pagado`, `pago_id`, `fecha_pago` y ajuste `estado`/`dias_mora` en las cuotas del préstamo.
   - Obtenga todos los pagos del préstamo ordenados por `fecha_pago`, `id`.
   - Para cada pago, llame a `_aplicar_pago_a_cuotas_interno(pago, db)` (sin commit entre pagos; un solo commit al final).
   - Así se respeta Cascada y se corrige el historial.

2. **Endpoint opcional**: `POST /api/v1/prestamos/{prestamo_id}/rearticular-cuotas` que haga lo anterior y devuelva resumen (cuotas actualizadas, errores si los hay).

## Verificación

- Después del cambio, crear un pago y aplicarlo a un préstamo con varias cuotas pendientes: debe llenar primero la cuota con `numero_cuota` menor.
- Para préstamos ya rearticulados: en el detalle del préstamo no debe haber ninguna cuota N+1 "Conciliado" con cuota N en mora o con pago parcial.

## Resumen

| Qué | Acción |
|-----|--------|
| Código | Cambiar `numero_cuota.desc()` → `numero_cuota.asc()` en `pagos.py` (línea ~2072). |
| Datos existentes | Rearticular préstamos afectados (script o endpoint) usando la misma lógica Cascada. |
| Futuro | No se requiere otra acción; la regla “primero cuotas primeras” queda aplicada en todos los flujos que usan `_aplicar_pago_a_cuotas_interno`. |
