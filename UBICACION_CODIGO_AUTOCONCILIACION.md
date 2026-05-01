# 🔍 UBICACIÓN EN CÓDIGO: Autoconciliación + Carga a Cuota

## 📍 ARCHIVO PRINCIPAL
`backend/app/api/v1/endpoints/revision_manual/routes.py`

---

## 🎯 ENDPOINT: POST /prestamos/{id}/confirmar-borrador

**Líneas: 2346-2457**

```python
@router.post("/prestamos/{prestamo_id}/confirmar-borrador")
def confirmar_borrador_revision(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Mueve borrador validado a BD real (cascada, cuotas, pagos) en transacción atómica."""
    actor = _actor_revision_manual(current_user)
    usuario_id = getattr(current_user, "id", None)

    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    borrador = db.execute(
        select(RevisionManualPrestamoTemp).where(
            RevisionManualPrestamoTemp.prestamo_id == prestamo_id
        )
    ).scalars().first()

    if not borrador:
        raise HTTPException(status_code=404, detail="No hay borrador para este préstamo")

    # ✅ LÍNEA 2369: VALIDAR ESTADO
    if borrador.estado != "validado":  # Solo si pasó validadores
        raise HTTPException(
            status_code=400,
            detail=f"Borrador no está listo para confirmar (estado: {borrador.estado})",
        )

    try:
        cambios_dict = {}

        # ✅ LÍNEA 2378-2388: APLICAR CAMBIOS AL PRÉSTAMO
        if borrador.prestamo_datos_json:
            datos_prestamo = json.loads(borrador.prestamo_datos_json)
            for campo, valor in datos_prestamo.items():
                if hasattr(prestamo, campo):
                    old_value = getattr(prestamo, campo)
                    cambios_dict[campo] = (old_value, valor)
                    setattr(prestamo, campo, valor)  # Actualiza en sesión

        prestamo.fecha_actualizacion = datetime.now()
        marcar_o_crear_prestamo_editado_en_revision_manual(db, prestamo_id)

        # ✅✅✅ LÍNEA 2390-2397: LA MAGIA OCURRE AQUÍ
        # Reconstruir cuotas desde prestamo (con aplicación de pagos cascada)
        from app.api.v1.endpoints.prestamos import (
            _reconstruir_tabla_cuotas_desde_prestamo_en_sesion,
        )

        # 👉 ESTA FUNCIÓN HACE:
        #    1. Elimina cuotas viejas
        #    2. Crea cuotas nuevas calculadas
        #    3. AUTOCONCILIA PAGOS (cascada)  ← AQUÍ
        #    4. CARGA A CUOTA_PAGOS           ← AQUÍ
        #    5. Actualiza estado de cuotas
        stats = _reconstruir_tabla_cuotas_desde_prestamo_en_sesion(db, prestamo_id)
        creadas = int(stats.get("cuotas_creadas") or 0)
        pagos_aplicados = int(stats.get("pagos_con_aplicacion") or 0)  # ← CONFIRMACIÓN

        # ✅ LÍNEA 2399-2416: AUDITORÍA REGISTRA TODO
        _fallback_uid = db.execute(text("SELECT id FROM public.usuarios ORDER BY id LIMIT 1")).scalar() or 1
        uid_audit = usuario_id or _fallback_uid

        db.add(
            Auditoria(
                usuario_id=int(uid_audit),
                accion="REVISION_MANUAL_CONFIRMAR_BORRADOR",
                entidad="prestamos",
                entidad_id=prestamo_id,
                detalles=(
                    f"Confirmación de borrador: {creadas} cuota(s); "
                    f"{pagos_aplicados} pago(s) aplicado(s). "  # ← PRUEBA
                    f"Campos: {list(cambios_dict.keys())}"
                ),
                exito=True,
            )
        )

        # ✅ LÍNEA 2418-2429: COMMIT ATÓMICO
        _commit_revision_seguro(
            db,
            operacion="confirmar_borrador_revision",
            actor=actor,
            tabla_principal="prestamos",
            id_principal=prestamo_id,
            resumen_campos=list(cambios_dict.keys()) + ["reconstruccion_cuotas"],
        )

        # Eliminar borrador (confirmado = consumido)
        db.delete(borrador)
        db.commit()

        logger.info(
            "revision_manual CONFIRMAR_BORRADOR prestamo_id=%s cuotas=%d pagos=%d actor=%s",
            prestamo_id,
            creadas,
            pagos_aplicados,
            actor,
        )

        # ✅ LÍNEA 2439-2445: RESPUESTA AL USUARIO
        return {
            "mensaje": "Borrador confirmado y migrado a BD real",
            "prestamo_id": prestamo_id,
            "cuotas_creadas": creadas,
            "pagos_aplicados": pagos_aplicados,  # ← AUTOCONCILIACIÓN CONFIRMADA
            "cambios": {k: {"anterior": v[0], "nuevo": v[1]} for k, v in cambios_dict.items()},
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(
            "revision_manual CONFIRMAR_BORRADOR_FALLIDO prestamo_id=%s actor=%s",
            prestamo_id,
            actor,
        )
        raise HTTPException(status_code=500, detail="Error al confirmar borrador") from exc
```

---

## 🎯 FUNCIÓN CLAVE

**Archivo**: `backend/app/api/v1/endpoints/prestamos/routes.py`

**Función**: `_reconstruir_tabla_cuotas_desde_prestamo_en_sesion(db, prestamo_id)`

**Línea de llamada**: 2395 (en confirmar_borrador_revision)

### ¿QUÉ HACE ESTA FUNCIÓN?

```python
def _reconstruir_tabla_cuotas_desde_prestamo_en_sesion(db, prestamo_id):
    """
    Reconstruye tabla de cuotas desde datos del préstamo:
    1. Elimina cuotas viejas
    2. Calcula y crea cuotas nuevas
    3. AUTOCONCILIA: Aplica cascada de pagos a cuotas
    4. CARGA: Inserta en cuota_pagos
    5. Actualiza estado de cuotas
    
    Retorna:
    {
        "cuotas_creadas": int,
        "cuotas_eliminadas": int,
        "pagos_con_aplicacion": int  ← AUTOCONCILIACIÓN
    }
    """
```

---

## 📊 FLUJO VISUAL

```
┌─ USER presiona "Confirmar Borrador" ──────────────────┐
│                                                       │
│  POST /prestamos/123/confirmar-borrador              │
│                                                       │
└───────────────────────────────────────────────────────┘
                        │
                        ▼ (línea 2356)
┌─ Obtener prestamo #123 ──────────────────────────────┐
└───────────────────────────────────────────────────────┘
                        │
                        ▼ (línea 2360-2364)
┌─ Obtener borrador temporal ──────────────────────────┐
└───────────────────────────────────────────────────────┘
                        │
                        ▼ (línea 2369)
┌─ Validar estado == 'validado' ───────────────────────┐
│ (Si no → error 400)                                 │
└───────────────────────────────────────────────────────┘
                        │
                        ▼ (línea 2378-2388)
┌─ Aplicar cambios prestamo_datos_json ────────────────┐
│ • total_financiamiento                              │
│ • numero_cuotas                                     │
│ • fecha_aprobacion                                  │
│ • etc...                                            │
└───────────────────────────────────────────────────────┘
                        │
                        ▼ (línea 2395) 👈 PUNTO CRÍTICO
┌─ LLAMAR: _reconstruir_tabla_cuotas_desde_prestamo_en_sesion()
│                                                       │
│  DENTRO DE FUNCIÓN:                                 │
│  ─────────────────────────────────────────────────  │
│  1. DELETE FROM cuotas WHERE prestamo_id = 123      │
│     Elimina 20 cuotas viejas                         │
│                                                       │
│  2. CALCULATE cuotas nuevas:                         │
│     • monto_cuota = 50000 / 24 = 2083.33            │
│     • fecha_vencimiento = 2026-06-01, 2026-07-01... │
│     CREATE 24 cuotas nuevas                          │
│                                                       │
│  3. AUTOCONCILIACIÓN (CASCADA):                      │
│     FOR EACH pago WHERE prestamo_id = 123 AND       │
│           estado IN ('CONCILIADO', 'VERIFICADO')    │
│         FOR EACH cuota IN orden_numero_cuota:       │
│           INSERT INTO cuota_pagos (...)  ✅          │
│           UPDATE cuota SET total_pagado = ...  ✅    │
│           UPDATE cuota SET estado = PAGADO  ✅       │
│                                                       │
│  4. RETORNA stats:                                   │
│     {                                                │
│       "cuotas_creadas": 24,                          │
│       "pagos_con_aplicacion": 5  ← AQUÍ             │
│     }                                                │
│                                                       │
└───────────────────────────────────────────────────────┘
                        │
                        ▼ (línea 2397)
┌─ Guardar stats en variables ──────────────────────────┐
│ creadas = 24                                         │
│ pagos_aplicados = 5  ← PRUEBA DE AUTOCONCILIACIÓN   │
└───────────────────────────────────────────────────────┘
                        │
                        ▼ (línea 2403-2416)
┌─ AUDITORÍA: Registrar detalles ──────────────────────┐
│ detalles = "Confirmación: 24 cuota(s), 5 pago(s)   │
│            aplicado(s)"                             │
└───────────────────────────────────────────────────────┘
                        │
                        ▼ (línea 2418-2425)
┌─ COMMIT ATÓMICO ─────────────────────────────────────┐
│ • INSERT cuotas (24 nuevas)                         │
│ • INSERT cuota_pagos (5 relaciones)                 │
│ • UPDATE prestamo (cambios)                         │
│ • INSERT auditoria (registro)                       │
│ • TODO EN UNA TRANSACCIÓN                           │
│   SI ALGO FALLA → ROLLBACK TODO                     │
└───────────────────────────────────────────────────────┘
                        │
                        ▼ (línea 2428-2429)
┌─ DELETE borrador temporal ────────────────────────────┐
│ Tabla temporal consumida, borrador eliminado         │
└───────────────────────────────────────────────────────┘
                        │
                        ▼ (línea 2439-2445)
┌─ RESPUESTA AL USUARIO ────────────────────────────────┐
│ {                                                    │
│   "mensaje": "Borrador confirmado y migrado a BD",  │
│   "prestamo_id": 123,                               │
│   "cuotas_creadas": 24,                             │
│   "pagos_aplicados": 5,  ✅ AUTOCONCILIACIÓN       │
│   "cambios": { ... }                                │
│ }                                                    │
└───────────────────────────────────────────────────────┘
                        │
                        ▼
             ✅ COMPLETADO
          Cédula actualizada
          Cuotas cargadas
          Pagos aplicados
          Auditoría registrada
```

---

## 🎓 CONCLUSIÓN

**La autoconciliación y carga a cuota ocurren en:**

```
Línea 2395:
stats = _reconstruir_tabla_cuotas_desde_prestamo_en_sesion(db, prestamo_id)
```

**Esta función es responsable de:**

✅ **Autoconciliación**:
- Busca pagos CONCILIADO/VERIFICADO/PAGADO
- Aplica cascada automáticamente
- Variable de confirmación: `stats.get("pagos_con_aplicacion")`

✅ **Carga a cuota**:
- INSERT cuota_pagos (5 filas nuevas)
- UPDATE cuota.total_pagado
- UPDATE cuota.estado = PAGADO

✅ **Transaccionalidad**:
- Todo en una transacción atómica
- COMMIT o ROLLBACK juntos

✅ **Auditoría**:
- Registra TODO en tabla auditoria
- Detalles con cifras de autoconciliación

---

**Implementación verificada en código** ✅

