# Característica Faltante: Pagos con Errores en Carga Masiva

## Lo Que Recuerdas (Arquitectura Existente)

Existe una arquitectura completa para manejar pagos que no cumplen validadores:

### 1. **Tabla `pagos_con_errores`**
Existe en BD con campos:
```python
id
cedula_cliente
fecha_pago
monto_pagado
numero_documento
errores_descripcion (JSONB)  # Guarda los errores en JSON
observaciones                # Campos con problema
fila_origen                  # Número de fila del Excel
```

### 2. **Modelo `PagoConError`**
```python
# backend/app/models/pago_con_error.py
class PagoConError(Base):
    __tablename__ = "pagos_con_errores"
    # Campos igual a pagos, más:
    # - errores_descripcion: JSONB (JSON con lista de errores)
    # - observaciones: campos problemáticos
    # - fila_origen: número de fila
```

### 3. **Endpoint `/pagos_con_errores`**
Existe en:
```python
# backend/app/api/v1/endpoints/pagos_con_errores.py
GET    /pagos_con_errores              # Listar pagos con errores
POST   /pagos_con_errores              # Crear uno manualmente
PUT    /pagos_con_errores/{id}         # Actualizar/revisar
DELETE /pagos_con_errores/{id}         # Eliminar
```

### 4. **Endpoint para Mover a Revisar**
```python
# backend/app/api/v1/endpoints/pagos.py
@router.post("/revisar-pagos/mover")
def mover_a_revisar_pagos(pago_ids: list[int])
    # Mueve pagos de tabla 'pagos' a 'revisar_pago' para revisión manual
```

## Lo Que Falta: Integración en Upload

### ❌ Actualmente en `/pagos/upload`

El endpoint `upload_excel_pagos()` **solo hace esto**:
```python
1. Lee fila
2. Valida
3. Si PASA → db.add(Pago) → Se guarda en tabla 'pagos'
4. Si FALLA → Se reporta error en respuesta (no se guarda en BD)
5. Retorna respuesta con errores

# ❌ NO:
# - Guarda filas con error en BD
# - Ofrece interfaz para revisarlas
# - Permite enviar a revisión posterior
```

### ✅ Lo Que Debería Hacer (Arquitectura Completa)

```python
# FASE 1: Upload y Validación
for fila in excel:
    if cumple_validadores:
        db.add(Pago(...))              # Tabla 'pagos'
    else:
        db.add(PagoConError(...))      # Tabla 'pagos_con_errores' ← FALTA ESTO
        # Guardar errores_descripcion como JSON:
        # {
        #   "fila": 5,
        #   "errores": [
        #     "Monto exceede límite",
        #     "Documento duplicado"
        #   ]
        # }

# FASE 2: Respuesta al Frontend
{
  "registros_procesados": 18,
  "registros_con_error": 2,            # ← FALTA
  "pagos_con_errores": [               # ← FALTA (para mostrar en interfaz)
    {
      "fila": 5,
      "cedula": "V20996698",
      "monto": 740087406734393,
      "errores": ["Monto excede límite máximo"],
      "id_en_tabla_errores": 1         # Para poder revisar luego
    },
    {
      "fila": 12,
      "cedula": "V18000758",
      "monto": 96,
      "errores": ["Documento duplicado"],
      "id_en_tabla_errores": 2
    }
  ]
}

# FASE 3: Frontend muestra interfaz
# - Tabla con filas rechazadas
# - Botones: "Revisar", "Corregir", "Descartar"
# - Si usuario click "Revisar": POST /pagos_con_errores/{id}?action=revisar
# - Se guarda en tabla 'revisar_pago' para análisis manual
```

## Comparativa: Actual vs Propuesto

### Flujo Actual (Sin integración)

```
Excel Upload
    ↓
┌───────────────────────────┐
│ Validar filas              │
├───────────────────────────┤
│ PASAN      → tabla pagos   │
│ FALLAN     → Error JSON    │
└───────────────────────────┘
    ↓
Respuesta HTTP
{
  "registros_procesados": 18,
  "errores": [lista de textos]
}
    ↓
Usuario ve errores en consola/JSON
Usuario NO puede guardarlos
Usuario NO puede revisarlos luego
```

### Flujo Propuesto (Con integración completa)

```
Excel Upload
    ↓
┌───────────────────────────────────────────┐
│ Validar filas                              │
├───────────────────────────────────────────┤
│ PASAN      → tabla 'pagos'                │
│ FALLAN     → tabla 'pagos_con_errores' ← │
└───────────────────────────────────────────┘
    ↓
Respuesta HTTP
{
  "registros_procesados": 18,
  "registros_con_error": 2,
  "pagos_con_errores": [
    {"id": 1, "fila": 5, "cedula": "V20996698", "errores": [...]}
  ]
}
    ↓
Frontend: Interfaz de Revisión
┌──────────────────────────────────────┐
│ Pagos con Errores (2)                │
├──────────────────────────────────────┤
│ Fila 5: V20996698 | Monto excede     │
│ [Revisar] [Descartar] [Corregir]     │
├──────────────────────────────────────┤
│ Fila 12: V18000758 | Documento dup   │
│ [Revisar] [Descartar] [Corregir]     │
└──────────────────────────────────────┘
    ↓
Usuario click [Revisar]
    ↓
Se guarda en tabla 'revisar_pago'
    ↓
Panel "Revisar Pagos" muestra para análisis posterior
```

## Código Que Falta Agregar

### En `upload_excel_pagos()` - Cuando falla validación

```python
# Línea ~640 (en FASE 2, cuando se valida documento):
if key_doc and key_doc in documentos_ya_en_bd:
    # ❌ ACTUALMENTE:
    datos_fila = {...}
    errores.append(f"Fila {i}: Ya existe un pago con ese Nº de documento")
    errores_detalle.append({...})
    continue  # ← Solo reporta error, no guarda

    # ✅ DEBERÍA:
    # Crear PagoConError con los datos
    pago_error = PagoConError(
        cedula_cliente=cedula,
        prestamo_id=prestamo_id,
        fecha_pago=datetime.combine(_parse_fecha(fecha_val), dt_time.min),
        monto_pagado=monto,
        numero_documento=numero_doc_norm,
        estado="PENDIENTE",
        errores_descripcion=[
            {
                "campo": "numero_documento",
                "error": "Ya existe un pago con ese Nº de documento"
            }
        ],
        observaciones="numero_documento",
        fila_origen=i
    )
    db.add(pago_error)
    
    # Seguir reportando error también
    errores.append(f"Fila {i}: Ya existe un pago con ese Nº de documento")
    continue
```

### En respuesta HTTP

```python
# Línea ~690 (al retornar):
return {
    "message": "Carga finalizada",
    "registros_procesados": registros,
    "cuotas_aplicadas": cuotas_aplicadas,
    "filas_omitidas": filas_omitidas,
    
    # ✅ AGREGAR:
    "registros_con_error": len(pagos_con_error),  # Número guardados en tabla errores
    "pagos_con_errores": [                         # Lista para mostrar en frontend
        {
            "id": pce.id,
            "fila_origen": pce.fila_origen,
            "cedula": pce.cedula_cliente,
            "monto": float(pce.monto_pagado),
            "errores": pce.errores_descripcion,
            "observaciones": pce.observaciones
        }
        for pce in pagos_con_error_insertados
    ],
    
    # Existentes:
    "errores": errores[:50],
    "errores_total": total_errores,
}
```

## Beneficios de Integrar

| Actual | Con Integración |
|--------|-----------------|
| ❌ Errores solo en respuesta JSON | ✅ Errores guardados en BD |
| ❌ Usuario ve errores una vez | ✅ Usuario puede revisarlos después |
| ❌ No hay histórico | ✅ Histórico en tabla `pagos_con_errores` |
| ❌ Usuario debe corregir y reintentar | ✅ Usuario puede revisar en interfaz |
| ❌ Filas perdidas | ✅ Filas disponibles en "Revisar Pagos" |

## Tablas Involucradas

### Ya Existen

1. **pagos**: Pagos que sí pasaron validación
2. **pagos_con_errores**: Pagos que fallaron (TABLA VACÍA, no se usa)
3. **revisar_pago**: Pagos pendientes de revisión manual

### Flujo Actual

```
Excel → Upload → VALIDA
                  ├─ PASA → pagos ✅
                  └─ FALLA → Error (reportado, no guardado) ❌
```

### Flujo Propuesto

```
Excel → Upload → VALIDA
                  ├─ PASA → pagos ✅
                  └─ FALLA → pagos_con_errores ✅
                            (guardado, visible en interfaz)
                            ↓
                        Usuario revisa en interfaz
                            ↓
                        Mueve a revisar_pago (si necesario)
```

## Recomendación

**La arquitectura está 80% lista. Falta:**

1. ✅ Tabla `pagos_con_errores` - YA EXISTE
2. ✅ Modelo `PagoConError` - YA EXISTE  
3. ✅ Endpoint `/pagos_con_errores` - YA EXISTE
4. ❌ **Integración en `/pagos/upload`** - FALTA (10-15 líneas de código)
5. ❌ **Frontend para mostrar errores** - FALTA (UI)

¿Quieres que **integre esta característica** en el endpoint `upload`?
