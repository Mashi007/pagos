# DIAGRAMA: PROBLEMA Y SOLUCIÓN

## ANTES (❌ Defectuoso)

```
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND: Tabla de Amortización (TablaAmortizacionPrestamo.tsx) │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ GET /prestamos/4601/cuotas
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND ENDPOINT (INCORRECTO)                                   │
│ GET /api/v1/prestamos/{id}/cuotas (líneas 507-547)             │
│                                                                   │
│ SELECT c.*, p.conciliado, p.monto_pagado                       │
│ FROM cuotas c                                                    │
│ LEFT JOIN pagos p ON c.pago_id = p.id  ❌ FK débil, puede NULL │
│ WHERE c.prestamo_id = ?                                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   ┌─────────────┐           ┌──────────────────┐
   │ CUOTAS      │           │ PAGOS            │
   │ ─────────── │           │ ──────────────── │
   │ id: 1       │           │ id: 501          │
   │ numero: 1   │           │ prestamo_id: 4601│
   │ fecha_venc: │           │ monto: $240      │
   │  15/04/2025 │           │ conciliado: ✅   │ ❌ NO VINCULADO
   │ pago_id: NULL ❌ ────X  │ fecha_pago:      │
   │ estado: PTE │           │  16/04/2025      │
   └─────────────┘           └──────────────────┘
        │
        │ JOIN FALLA: pago_id=NULL
        ▼
   ✗ Resultado: pago_conciliado=FALSE
   ✗ Resultado: pago_monto_conciliado=$0.00


TABLA MOSTRADA AL USUARIO:
┌──────┬────────────┬───────┬──────────────────┬────────┐
│ Cuota│ Vencimiento│ Total │ Pago conciliado  │ Estado │
├──────┼────────────┼───────┼──────────────────┼────────┤
│  1   │ 15/04/2025 │ $240  │ —  ❌            │ PENDIENTE
│  2   │ 15/05/2025 │ $240  │ —  ❌            │ PENDIENTE
└──────┴────────────┴───────┴──────────────────┴────────┘
```

---

## DESPUÉS (✅ Correcto)

```
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND: Tabla de Amortización (TablaAmortizacionPrestamo.tsx) │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ GET /prestamos/4601/cuotas
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND ENDPOINT (MEJORADO)                                     │
│ GET /api/v1/prestamos/{id}/cuotas (líneas 507-591)             │
│                                                                   │
│ PARA CADA CUOTA:                                                │
│                                                                   │
│ 1️⃣ Si c.pago_id EXISTS:                                         │
│    SELECT pago WHERE id = c.pago_id                             │
│                                                                   │
│ 2️⃣ Si c.pago_id IS NULL:                                        │
│    SELECT pagos WHERE prestamo_id = ?                           │
│    AND fecha_pago BETWEEN (venc-15d) AND (venc+15d)  ✅         │
│                                                                   │
│ 3️⃣ Consolidar: Si pago.conciliado OR pago.verificado='SI':     │
│    pago_conciliado = TRUE                                        │
│    pago_monto_conciliado += pago.monto_pagado                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   ┌─────────────┐           ┌──────────────────┐
   │ CUOTAS      │           │ PAGOS            │
   │ ─────────── │           │ ──────────────── │
   │ id: 1       │           │ id: 501          │
   │ numero: 1   │           │ prestamo_id: 4601│
   │ fecha_venc: │           │ monto: $240      │
   │  15/04/2025 │           │ conciliado: ✅   │ ✅ ENCONTRADO
   │ pago_id: NULL✅ ───────►│ fecha_pago:      │
   │ estado: PTE │           │  16/04/2025      │
   └─────────────┘           └──────────────────┘
        │
        │ BÚSQUEDA POR RANGO: 01/04 - 30/04
        ▼
   ✅ Resultado: pago_conciliado=TRUE
   ✅ Resultado: pago_monto_conciliado=$240.00


TABLA MOSTRADA AL USUARIO:
┌──────┬────────────┬───────┬──────────────────┬────────────┐
│ Cuota│ Vencimiento│ Total │ Pago conciliado  │ Estado     │
├──────┼────────────┼───────┼──────────────────┼────────────┤
│  1   │ 15/04/2025 │ $240  │ $240.00  ✅      │ CONCILIADO │
│  2   │ 15/05/2025 │ $240  │ $240.00  ✅      │ CONCILIADO │
│  3   │ 14/06/2025 │ $240  │ —                │ PENDIENTE  │
└──────┴────────────┴───────┴──────────────────┴────────────┘
```

---

## CAMBIO DE CÓDIGO

### Función Mejorada: `get_cuotas_prestamo`

```python
# ANTES: 40 líneas, lógica incompleta
@router.get("/{prestamo_id}/cuotas", response_model=list)
def get_cuotas_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    # ... solo JOIN simple ...
    return [
        {
            # ❌ pago_conciliado nunca es True si pago_id=NULL
            "pago_conciliado": bool(pago_conciliado) or ...,
            # ❌ monto incorrecto (usa total_pagado de cuota, no de pago)
            "pago_monto_conciliado": float(c.total_pagado) or 0,
        }
        for c, pago_conciliado, ... in rows
    ]


# DESPUÉS: 85 líneas, lógica completa
@router.get("/{prestamo_id}/cuotas", response_model=list)
def get_cuotas_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    """
    ESTRATEGIA MEJORADA:
    1. Obtiene todas las cuotas
    2. Para cada cuota, busca pagos en 2 niveles
    3. Consolida información de múltiples pagos
    4. Retorna datos correctos de conciliación
    """
    
    resultado = []
    for c in cuotas:
        pago_conciliado_flag = False
        pago_monto_conciliado = 0.0
        
        # NIVEL 1: Búsqueda directa por FK
        if c.pago_id:
            pago = db.get(Pago, c.pago_id)
            if pago and (pago.conciliado or verificado_SI):
                pago_conciliado_flag = True
                pago_monto_conciliado = pago.monto_pagado
        
        # NIVEL 2: Búsqueda por rango de fechas (si FK vacío)
        else:
            fecha_inicio = c.fecha_vencimiento - 15 días
            fecha_fin = c.fecha_vencimiento + 15 días
            
            pagos_en_rango = db.query(Pago).filter(
                Pago.prestamo_id == prestamo_id,
                fecha_pago BETWEEN fecha_inicio AND fecha_fin
            ).all()
            
            # Consolidar pagos conciliados
            for pago in pagos_en_rango:
                if pago.conciliado or verificado_SI:
                    pago_conciliado_flag = True
                    pago_monto_conciliado += pago.monto_pagado
        
        resultado.append({
            # ✅ Ahora siempre correcto
            "pago_conciliado": pago_conciliado_flag,
            # ✅ Suma de montos conciliados
            "pago_monto_conciliado": pago_monto_conciliado,
        })
    
    return resultado
```

---

## FLUJO DE DATOS COMPLETO

### ANTES ❌
```
Usuario
   │
   ▼ Click en Préstamo #4601
   
Tabla de Amortización (Frontend)
   │
   ├─► API: GET /prestamos/4601/cuotas
   │
   ├─► Endpoint ejecuta JOIN simple
   │
   ├─► pago_id = NULL → JOIN devuelve NULL
   │
   ├─► pago_conciliado = FALSE siempre ❌
   │
   ▼ Columna "Pago conciliado" = "—"
```

### DESPUÉS ✅
```
Usuario
   │
   ▼ Click en Préstamo #4601
   
Tabla de Amortización (Frontend)
   │
   ├─► API: GET /prestamos/4601/cuotas
   │
   ├─► Endpoint itera cuotas
   │
   ├─► Para cada cuota:
   │   - Si pago_id: buscar directo
   │   - Si pago_id=NULL: buscar por rango ✅
   │
   ├─► Consolida pagos conciliados ✅
   │
   ├─► pago_conciliado = TRUE
   │
   ▼ Columna "Pago conciliado" = "$240.00" ✅
```

---

## PRUEBAS RECOMENDADAS

| Caso | Escenario | Resultado Esperado |
|------|-----------|-------------------|
| 1 | Cuota con pago_id vinculado | ✅ Mostrar pago conciliado |
| 2 | Cuota sin pago_id pero pago en BD | ✅ Mostrar pago conciliado |
| 3 | Cuota sin pago | ✅ Mostrar "—" |
| 4 | Múltiples pagos en rango | ✅ Sumar todos los montos |
| 5 | Pago verificado_concordancia='SI' | ✅ Mostrar como conciliado |

