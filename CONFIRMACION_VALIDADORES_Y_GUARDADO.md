# ✅ CONFIRMACIÓN: Si Cumple Validadores → Se Guardan

## Respuesta Directa

**SÍ, absolutamente.**

Si una fila cumple con TODOS los validadores → **Se guarda en BD**.

## Flujo de Decisión

```
┌─────────────────────────────────┐
│ Leer fila del Excel             │
│ (Cédula, Monto, Fecha, Doc)     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ ¿Formato correcto?              │
│ (Cédula | Monto | Fecha | Doc)  │
└────────┬────────────────────────┘
         │
    NO   │     SÍ
    ─────┼─────
        │      │
        │      ▼
        │  ┌─────────────────────────────────┐
        │  │ ¿Cédula válida?                 │
        │  │ (V, E, J, Z + dígitos)          │
        │  └────────┬────────────────────────┘
        │          │
        │     NO   │     SÍ
        │     ─────┼─────
        │        │      │
        │        │      ▼
        │        │  ┌─────────────────────────────────┐
        │        │  │ ¿Monto válido?                  │
        │        │  │ (0.01 a 999,999,999,999.99)    │
        │        │  └────────┬────────────────────────┘
        │        │          │
        │        │     NO   │     SÍ
        │        │     ─────┼─────
        │        │        │      │
        │        │        │      ▼
        │        │        │  ┌─────────────────────────────────┐
        │        │        │  │ ¿Fecha válida?                  │
        │        │        │  │ (DD-MM-YYYY, etc.)              │
        │        │        │  └────────┬────────────────────────┘
        │        │        │          │
        │        │        │     NO   │     SÍ
        │        │        │     ─────┼─────
        │        │        │        │      │
        │        │        │        │      ▼
        │        │        │        │  ┌─────────────────────────────────┐
        │        │        │        │  │ ¿Documento duplicado?           │
        │        │        │        │  │ (En archivo o BD)               │
        │        │        │        │  └────────┬────────────────────────┘
        │        │        │        │          │
        │        │        │        │     NO   │     SÍ
        │        │        │        │     ─────┼─────
        │        │        │        │        │      │
        │        │        │        │        │      │
        ▼        ▼        ▼        ▼        ▼      ▼
    ┌────────────────────────────────┐  ┌──────────────────┐
    │ ❌ RECHAZA FILA                │  │ ❌ RECHAZA FILA  │
    │ - Reporta error                │  │ - Documento dup  │
    │ - NO se inserta en BD           │  │ - NO se inserta  │
    │ - Aparece en sección errores    │  │ - Aparece error  │
    └────────────────────────────────┘  └──────────────────┘
                                                │
                                                │ TODAS PASAN
                                                ▼
                                    ┌──────────────────────┐
                                    │ ✅ ACEPTA FILA      │
                                    │ - Crea objeto Pago  │
                                    │ - db.add(pago)      │
                                    │ - Suma registros++  │
                                    └──────────────────────┘
```

## Proceso Paso a Paso

### FASE 1: Parseo + Validación Básica

```python
for i, row in enumerate(rows):
    
    # 1. Detectar formato
    if _looks_like_cedula(row[0]) and _looks_like_date(row[2]):
        cedula = row[0]
        monto = row[1]
        fecha = row[2]
        documento = row[3]
    else:
        rechazar("Formato no reconocido")
        continue
    
    # 2. Validar cédula y monto básicos
    if not cedula or monto <= 0:
        rechazar("Cédula vacía o monto <= 0")
        continue
    
    # 3. Validar monto dentro de rango
    es_válido, monto_parseado, error = _validar_monto(monto)
    if not es_válido:
        rechazar(f"Monto inválido: {error}")
        continue
    
    # ✅ Si llega aquí, se añade a lista para siguiente fase
    FilasParseadas.append({
        "cedula": cedula,
        "monto": monto_parseado,
        "fecha": fecha,
        "documento": documento
    })
```

### FASE 2: Validación de Documentos + Inserción

```python
# Verificar documentos duplicados en BD
documentos_en_bd = consultar_documentos_existentes()

for item in FilasParseadas:  # Solo filas que pasaron FASE 1
    
    # 4. Validar documento no duplicado
    if item["documento"] in documentos_en_bd:
        rechazar("Documento ya existe en BD")
        continue
    
    # ✅ TODOS LOS VALIDADORES PASARON
    # Crear objeto Pago
    pago = Pago(
        cedula_cliente=item["cedula"],
        monto_pagado=item["monto"],
        fecha_pago=item["fecha"],
        numero_documento=item["documento"],
        estado="PENDIENTE"
    )
    
    # Agregar a sesión (aún no en BD)
    db.add(pago)
    registros_a_guardar += 1
```

### FASE 3: Inserción Atómica en BD

```python
# Todas las filas válidas se guardan en UNA transacción
db.commit()  # ✅ AHORA se insertan en BD
```

## Validadores en Detalle

### Validador 1: Formato de Fila
```python
# Detecta: Cédula | Monto | Fecha | Documento
if _looks_like_cedula(row[0]) and row[1] is not None and _looks_like_date(row[2]):
    # ✅ PASA
else:
    # ❌ FALLA: Formato no reconocido
```

### Validador 2: Cédula no Vacía
```python
if not cedula:
    # ❌ FALLA: Cédula vacía
else:
    # ✅ PASA
```

### Validador 3: Monto > 0
```python
if monto <= 0:
    # ❌ FALLA: Monto no positivo
else:
    # ✅ PASA
```

### Validador 4: Monto en Rango Válido (0.01 a 999,999,999,999.99)
```python
def _validar_monto(monto_raw):
    try:
        monto = float(monto_raw)
    except:
        return (False, 0.0, "No se puede parsear")  # ❌ FALLA
    
    if monto < 0.01:
        return (False, monto, "Menor a mínimo")  # ❌ FALLA
    
    if monto > 999_999_999_999.99:
        return (False, monto, "Mayor a máximo")  # ❌ FALLA
    
    return (True, monto, "")  # ✅ PASA
```

### Validador 5: Documento no Duplicado
```python
# En archivo (durante FASE 2)
if documento in numeros_doc_en_lote:
    # ❌ FALLA: Ya existe en este lote
else:
    numeros_doc_en_lote.add(documento)  # ✅ PASA

# En BD (durante FASE 2)
if documento in documentos_ya_en_bd:
    # ❌ FALLA: Ya existe en BD
else:
    # ✅ PASA
```

## Confirmación: Flujo Completo

### ✅ SI CUMPLE TODOS LOS VALIDADORES

```
Fila 2 del Excel:
  Cédula:    V18000758     ✅ Formato válido
  Monto:     96            ✅ Entre 0.01 y 999M
  Fecha:     31-10-2025    ✅ Formato válido
  Documento: VE/505363350  ✅ No duplicado

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RESULTADO: ✅ SE GUARDA EN BD
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  INSERT INTO pagos (cedula, monto, fecha, documento) VALUES
  ('V18000758', 96, '2025-10-31', 'VE/505363350')
```

### ❌ SI FALLA ALGÚN VALIDADOR

```
Fila 6 del Excel:
  Cédula:    V20996698             ✅ Formato válido
  Monto:     740087406734393.0     ❌ Mayor a 999,999,999,999.99
  Fecha:     28-08-2025            ✅ Formato válido
  Documento: 740087406734393       ✅ No duplicado

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RESULTADO: ❌ NO SE GUARDA EN BD
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Se reporta error:
  "Fila 6: Monto excede límite máximo (999999999999.99): 740087406734393.0"
```

## Resumen de Código

```python
# Línea 659: db.add(p)
# Se ejecuta SOLO si la fila pasó TODOS los validadores

# Línea 667: db.flush()
# Asigna IDs a los pagos (aún en transacción, no confirmado)

# Línea 680: db.commit()
# ✅ CONFIRMA TODOS LOS CAMBIOS EN BD
# Si llega aquí, todos los registros se guardan permanentemente
```

## Garantías

### 🔒 Si la respuesta HTTP dice:

```json
{
  "registros_procesados": 20,
  "errores_total": 0
}
```

**Garantías:**
- ✅ **20 registros están en BD** (confirmados, permanentes)
- ✅ **0 filas fueron rechazadas** por validadores
- ✅ **0 errores** ocurrieron durante la carga
- ✅ **Transacción completada** con db.commit()

### 🚨 Si la respuesta dice:

```json
{
  "registros_procesados": 18,
  "errores_total": 2,
  "errores": [
    "Fila 5: Monto excede límite máximo (999999999999.99): 740087406734393.0",
    "Fila 12: Documento duplicado en este archivo"
  ]
}
```

**Garantías:**
- ✅ **18 registros están en BD** (pasaron todos los validadores)
- ✅ **2 filas no se guardaron** (fila 5 y 12 rechazadas)
- ❌ **No se insertaron filas inválidas** (protección de validadores)

## Transacción Atómica

```python
try:
    # FASE 1: Parseo
    for fila in excel:
        if cumple_validadores(fila):
            db.add(Pago(...))
    
    # FASE 2: Flush (asigna IDs)
    db.flush()
    
    # FASE 3: Commit (guarda permanentemente)
    db.commit()  # ✅ Aquí se guardan todos
    
except Exception as e:
    db.rollback()  # ❌ Si algo falla, se revierte TODO
    raise
```

## Conclusión

```
╔════════════════════════════════════════════════════════════╗
║  PREGUNTA: ¿Si cumple con validadores, se guardan?       ║
║                                                            ║
║  RESPUESTA: ✅ SÍ, DEFINITIVAMENTE                        ║
║                                                            ║
║  Flujo:                                                    ║
║  1. Validar (FASE 1 + FASE 2)                             ║
║  2. db.add(pago)     ← Se agrega a sesión                 ║
║  3. db.flush()       ← Prepara para guardar               ║
║  4. db.commit()      ← ✅ SE GUARDAN EN BD PERMANENTEMENTE║
║                                                            ║
║  Si falla un validador:                                   ║
║  → Se rechaza la fila                                     ║
║  → Se reporta error                                       ║
║  → NO se ejecuta db.add()                                 ║
║  → NO se guarda en BD                                     ║
╚════════════════════════════════════════════════════════════╝
```
