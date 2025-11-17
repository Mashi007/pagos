# ✅ Confirmación: Campos en Tabla `pagos` Afectados por Conciliación

## 📋 Pregunta

**¿Qué campo en la tabla `pagos` se afecta cuando un pago está conciliado y se actualizan las cuotas?**

---

## ✅ Respuesta Directa

**NINGÚN campo en la tabla `pagos` se actualiza basado en el estado de las cuotas cuando se concilia un pago.**

---

## 📊 Campos Actualizados en `pagos` al Conciliar

Cuando se concilia un pago (`conciliado = True`), **SOLO** se actualizan estos campos:

| Campo | Valor Anterior | Valor Nuevo | Se Actualiza |
|-------|----------------|-------------|--------------|
| `conciliado` | `False` | `True` | ✅ SÍ |
| `fecha_conciliacion` | `NULL` | `datetime.now()` | ✅ SÍ |
| `verificado_concordancia` | `"NO"` | `"SI"` | ✅ SÍ |
| `monto_pagado` | (valor original) | (sin cambios) | ❌ NO |
| `estado` | (valor original) | (sin cambios) | ❌ NO |
| `prestamo_id` | (valor original) | (sin cambios) | ❌ NO |
| `numero_cuota` | (valor original) | (sin cambios) | ❌ NO |

---

## 🔄 Flujo de Conciliación

```
1. Se concilia un pago
   └─> _conciliar_pago() es llamado

2. Se actualizan campos en tabla `pagos`:
   ├─> pago.conciliado = True ✅
   ├─> pago.fecha_conciliacion = datetime.now() ✅
   └─> pago.verificado_concordancia = "SI" ✅

3. Se actualizan campos en tabla `cuotas`:
   ├─> cuota.estado (de PENDIENTE a PAGADO si corresponde) ✅
   ├─> cuota.dias_morosidad ✅
   └─> cuota.monto_morosidad ✅

4. ❌ NO se actualiza ningún campo en tabla `pagos` basado en cuotas
```

---

## 📝 Código Relevante

### Función `_conciliar_pago()` en `pagos_conciliacion.py`

```python
def _conciliar_pago(pago: Pago, db: Session, numero_documento: str) -> bool:
    # ✅ ACTUALIZA campos de conciliación en pagos
    pago.conciliado = True
    pago.fecha_conciliacion = datetime.now()
    pago.verificado_concordancia = "SI"
    db.commit()  # ✅ Commit del pago

    # ✅ ACTUALIZA cuotas (NO actualiza campos en pagos)
    if pago.prestamo_id:
        cuotas = db.query(Cuota).filter(...).all()
        for cuota in cuotas:
            _actualizar_estado_cuota(cuota, fecha_hoy, db)
            # ✅ Actualiza cuota.estado, cuota.dias_morosidad, cuota.monto_morosidad
            # ❌ NO actualiza pago.estado ni ningún otro campo en pagos
        db.commit()  # ✅ Commit de cuotas

    return True
```

---

## ⚠️ Importante: `pago.estado` NO se Actualiza en Conciliación

El campo `pago.estado` **SOLO** se actualiza cuando se **CREA** el pago (en `crear_pago()`), **NO** cuando se concilia.

### Cuándo se Actualiza `pago.estado`

```python
# En crear_pago() (línea 650-658)
if nuevo_pago.prestamo_id and cuotas_completadas == 0:
    nuevo_pago.estado = "PARCIAL"  # ✅ Se actualiza al CREAR
elif nuevo_pago.prestamo_id and cuotas_completadas > 0:
    nuevo_pago.estado = "PAGADO"  # ✅ Se actualiza al CREAR
```

### Cuándo NO se Actualiza `pago.estado`

```python
# En _conciliar_pago() (pagos_conciliacion.py)
# ❌ NO se actualiza pago.estado cuando se concilia
```

---

## ✅ Confirmación Final

| Campo en `pagos` | Se Actualiza al Conciliar | Se Actualiza Basado en Cuotas |
|------------------|---------------------------|-------------------------------|
| `conciliado` | ✅ SÍ | ❌ NO |
| `fecha_conciliacion` | ✅ SÍ | ❌ NO |
| `verificado_concordancia` | ✅ SÍ | ❌ NO |
| `monto_pagado` | ❌ NO | ❌ NO |
| `estado` | ❌ NO | ❌ NO |
| `prestamo_id` | ❌ NO | ❌ NO |
| `numero_cuota` | ❌ NO | ❌ NO |

---

## 🎯 Conclusión

**✅ CONFIRMADO:** Cuando un pago está conciliado y se actualizan las cuotas:

1. ✅ Se actualizan campos de conciliación en `pagos` (`conciliado`, `fecha_conciliacion`, `verificado_concordancia`)
2. ✅ Se actualizan campos en `cuotas` (`estado`, `dias_morosidad`, `monto_morosidad`)
3. ❌ **NO se actualiza ningún campo en `pagos` basado en el estado de las cuotas**

**El campo `pago.estado` NO se afecta por la conciliación ni por el estado de las cuotas.**

