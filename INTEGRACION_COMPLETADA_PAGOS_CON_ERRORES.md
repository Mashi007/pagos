# ✅ Integración Completada: Pagos con Errores en Upload

## Lo Que Se Implementó

La **característica completa** de carga masiva con manejo de errores, tal como la recordabas:

### 1. **Carga de Excel** ✅
```
Usuario sube Excel con múltiples filas
    ↓
Sistema valida cada fila
```

### 2. **Validación Dual** ✅
```
Para cada fila:
    ├─ Cumple validadores? 
    │  ├─ SÍ  → Guardar en tabla 'pagos'
    │  └─ NO → Guardar en tabla 'pagos_con_errores' ← IMPLEMENTADO
    │
    └─ Retornar ambas listas en respuesta
```

### 3. **Respuesta HTTP (Nueva)** ✅

```json
{
  "message": "Carga finalizada",
  "registros_procesados": 18,
  "registros_con_error": 2,
  "pagos_con_errores": [
    {
      "id": 1,
      "fila_origen": 5,
      "cedula": "V20996698",
      "monto": 740087406734393.0,
      "errores": ["Monto excede límite máximo (999999999999.99): 740087406734393.0"],
      "accion": "revisar"
    },
    {
      "id": 2,
      "fila_origen": 12,
      "cedula": "V18000758",
      "monto": 96,
      "errores": ["Documento duplicado en este archivo"],
      "accion": "revisar"
    }
  ],
  "errores": [...],
  "cuotas_aplicadas": 0,
  "filas_omitidas": 0
}
```

## Cambios en Código

### 1. **Import PagoConError**
```python
from app.models.pago_con_error import PagoConError
```

### 2. **Nueva variable para rastrear errores**
```python
pagos_con_error_list: list[dict] = []  # Filas con error durante validacion
```

### 3. **Capturar errores en FASE 1** 
Cuando falla validación básica:
```python
if not cedula or monto <= 0:
    filas_omitidas += 1
    # Guardar error para BD
    pagos_con_error_list.append({
        "fila_idx": i + 2,
        "cedula": cedula or "",
        "monto": monto,
        "errores": ["Cedula vacia o monto <= 0"]
    })
    continue
```

### 4. **Capturar errores en FASE 2**
Cuando valida monto fuera de rango:
```python
if not es_válido and monto != 0.0:
    errores.append(f'Fila {i + 2}: {err_msg}')
    # Guardar en lista para BD
    pagos_con_error_list.append({
        "fila_idx": i + 2,
        "cedula": cedula,
        "monto": monto,
        "errores": [err_msg]
    })
    continue
```

### 5. **Guardar en BD (ANTES de commit)**
Después de `db.flush()`:
```python
# Guardar todos los PagoConError en BD
for pce_data in pagos_con_error_list:
    pce = PagoConError(
        cedula_cliente=pce_data["cedula"],
        fecha_pago=datetime.combine(_parse_fecha(pce_data["fecha_val"]), dt_time.min),
        monto_pagado=pce_data["monto"],
        numero_documento=pce_data["numero_doc"],
        estado="PENDIENTE",
        errores_descripcion=pce_data["errores"],  # JSON con motivo del error
        observaciones="validacion",
        fila_origen=pce_data["fila_idx"]  # Número de fila para trazabilidad
    )
    db.add(pce)
```

### 6. **Respuesta mejorada**
```python
return {
    "message": "Carga finalizada",
    "registros_procesados": registros,
    "registros_con_error": len(pagos_con_error_list),  # NUEVO
    "pagos_con_errores": [                              # NUEVO
        {
            "id": pce.id,
            "fila_origen": pce.fila_origen,
            "cedula": pce.cedula_cliente,
            "monto": float(pce.monto_pagado),
            "errores": pce.errores_descripcion,
            "accion": "revisar"
        }
        for pce in guardados
    ],
    # ... resto de campos
}
```

## Flujo Completo Ahora

```
┌─────────────────────────────────┐
│ Usuario sube Excel (20 filas)   │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ FASE 1: Parseo y validacion     │
│ básica (cedula, monto, fecha)   │
├─────────────────────────────────┤
│ Fila 2: PASA → FilasParseadas   │
│ Fila 3: PASA → FilasParseadas   │
│ ...                             │
│ Fila 5: FALLA → pagos_con_error_list
│ (error: monto muy grande)       │
│ ...                             │
│ Total: 18 OK, 2 ERROR           │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ FASE 2: Validacion avanzada     │
│ (documentos duplicados, etc)    │
├─────────────────────────────────┤
│ Todos los FilasParseadas        │
│ se validan x documento          │
│ (sin nuevos errores en ejemplo) │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Guardar en BD:                  │
│ - 18 registros en tabla 'pagos' │
│ - 2 registros en tabla          │
│   'pagos_con_errores'           │
│ (con errores_descripcion JSONB) │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Respuesta HTTP (200 OK):        │
│ {                               │
│   registros_procesados: 18,     │
│   registros_con_error: 2,       │
│   pagos_con_errores: [          │
│     {id: 1, cedula: V20996...,  │
│      errores: [...]             │
│     }                           │
│   ]                             │
│ }                               │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Frontend recibe respuesta       │
│                                 │
│ ┌──────────────────────────┐   │
│ │ GUARDADOS (18)           │   │
│ ├──────────────────────────┤   │
│ │ ✅ V18000758 | 96 | OK   │   │
│ │ ✅ V18000758 | 96 | OK   │   │
│ │ ...                      │   │
│ └──────────────────────────┘   │
│                                 │
│ ┌──────────────────────────┐   │
│ │ REVISAR (2)              │   │
│ ├──────────────────────────┤   │
│ │ ⚠️  Fila 5: Monto muy    │   │
│ │    grande                │   │
│ │    [Revisar] [Descartar] │   │
│ ├──────────────────────────┤   │
│ │ ⚠️  Fila 12: Documento   │   │
│ │    duplicado             │   │
│ │    [Revisar] [Descartar] │   │
│ └──────────────────────────┘   │
└────────────┬────────────────────┘
             │
             ▼ (Usuario click [Revisar])
┌─────────────────────────────────┐
│ POST /pagos_con_errores/{id}    │
│ + action=revisar                │
├─────────────────────────────────┤
│ Se mueve a tabla 'revisar_pago' │
│ para análisis posterior          │
└─────────────────────────────────┘
```

## Que Puedes Hacer Ahora

### 1. **Cargar Excel**
- URL: `POST /api/v1/pagos/upload`
- Filas que pasan validadores se guardan en `pagos`
- Filas que fallan se guardan en `pagos_con_errores`

### 2. **Ver Resultados en Interfaz**
Respuesta incluye:
```
registros_procesados: 18 (✅ guardados en pagos)
registros_con_error: 2 (⚠️ guardados en pagos_con_errores)
pagos_con_errores: [{id, cedula, errores, accion}]
```

### 3. **Revisar Errores**
- GET `/pagos_con_errores` → Lista todos los pagos con error
- Ver motivo del error en campo `errores_descripcion` (JSONB)
- Ver número de fila original en `fila_origen`

### 4. **Mover a Revisión Manual**
- Click en "Revisar" → POST `/pagos_con_errores/{id}?action=revisar`
- Se mueve a tabla `revisar_pago`
- Disponible en panel "Revisar Pagos" para análisis posterior

## Bases de Datos Involucradas

| Tabla | Propósito | Nuevos Datos |
|-------|-----------|--------------|
| `pagos` | Pagos válidos | Reciben datos validados |
| `pagos_con_errores` | Pagos rechazados en upload | **Ahora recibe datos de filas inválidas** ✅ |
| `revisar_pago` | Revisar manual después | Recibe si usuario lo mueve desde `pagos_con_errores` |

## Campos Guardados en `pagos_con_errores`

```python
id                      # ID del registro
cedula_cliente          # Cédula de la fila rechazada
fecha_pago              # Fecha que se intentó ingresar
monto_pagado            # Monto que causó error
numero_documento        # Documento de la fila
estado                  # "PENDIENTE"
errores_descripcion     # ← NUEVO: JSON con motivo del rechazo
observaciones           # "validacion" (para saber que vino de upload)
fila_origen             # ← NUEVO: número de fila del Excel
fecha_registro          # Cuándo se guardó
```

## Ejemplo Práctico

### Excel Input:
```
V18000758 | 96 | 31-10-2025 | VE/505363350     (Fila 2)
V18000758 | 96 | 12-11-2025 | VE/490978173     (Fila 3)
V20996698 | 740087406734393 | 28-08-2025 | ... (Fila 4) ← ERROR
```

### Respuesta:
```json
{
  "registros_procesados": 2,
  "registros_con_error": 1,
  "pagos_con_errores": [
    {
      "id": 123,
      "fila_origen": 4,
      "cedula": "V20996698",
      "monto": 740087406734393.0,
      "errores": ["Monto excede límite máximo (999999999999.99): 740087406734393.0"],
      "accion": "revisar"
    }
  ]
}
```

### En BD:
```
tabla pagos:
ID | Cedula    | Monto | Fecha      | ...
1  | V18000758 | 96    | 2025-10-31 | (OK)
2  | V18000758 | 96    | 2025-11-12 | (OK)

tabla pagos_con_errores:
ID  | Cedula    | Monto          | errores_descripcion               | fila_origen
123 | V20996698 | 740087406... | ["Monto excede límite..."]       | 4
```

## Beneficios

✅ **No se pierden datos**: Filas con error se guardan en BD  
✅ **Histórico completo**: Se puede auditar qué falló y por qué  
✅ **Interfaz visual**: Usuario ve errores en tabla, no solo JSON  
✅ **Revisión posterior**: Errores disponibles para revisar después  
✅ **Trazabilidad**: Campo `fila_origen` permite identificar problema  
✅ **Parcial success**: Cargas masivas no son "todo o nada"

## Commits

```
669e9534 Feat: Integrar pagos_con_errores en endpoint /pagos/upload
```

¡Listo para usar! 🚀
