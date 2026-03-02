# Confirmación: Flujo de Carga de Excel - Articulación por Cédula

## Tu Caso de Uso

**Excel Input:**
```
Cédula      | Monto | Fecha      | Nº Documento
V18000758   | 96    | 31-10-2025 | VE/505363350
V18000758   | 96    | 12-11-2025 | VE/490978173
V18000758   | 96    | 12-11-2025 | VE/190978172
V18000758   | 20    | 28-01-2026 | VE/190978172
V20996698   | 96    | 28-08-2025 | 740087406734393
...
```

**Pregunta**: ¿Se articula por cédula y se copia las otras 2 columnas?

## ✅ CONFIRMACIÓN: SÍ, PERO CON PRECISIÓN

### Lo Que Sucede Exactamente

El sistema **NO articula/agrupa** por cédula en el sentido de consolidar. Cada fila se procesa **independientemente**:

#### Para la fila 2:
```python
cedula = "V18000758"
monto = 96
fecha = 31-10-2025
documento = "VE/505363350"

# Se inserta UN registro en tabla pagos:
INSERT INTO pagos (cedula, monto_pagado, fecha_pago, numero_documento, estado)
VALUES ('V18000758', 96, '2025-10-31', 'VE/505363350', 'PENDIENTE')
```

#### Para la fila 3:
```python
cedula = "V18000758"        # ← Misma cédula
monto = 96
fecha = 12-11-2025           # ← Diferente fecha
documento = "VE/490978173"   # ← Diferente documento

# Se inserta UN REGISTRO DISTINTO:
INSERT INTO pagos (cedula, monto_pagado, fecha_pago, numero_documento, estado)
VALUES ('V18000758', 96, '2025-11-12', 'VE/490978173', 'PENDIENTE')
```

**Resultado en BD:**
```
ID | Cédula    | Monto | Fecha      | Nº Documento    | Estado
1  | V18000758 | 96    | 2025-10-31 | VE/505363350   | PENDIENTE
2  | V18000758 | 96    | 2025-11-12 | VE/490978173   | PENDIENTE
3  | V18000758 | 96    | 2025-11-12 | VE/190978172   | PENDIENTE
4  | V18000758 | 20    | 2026-01-28 | VE/190978172   | PENDIENTE
5  | V20996698 | 96    | 2025-08-28 | 740087406... (error)
```

### No Hay Consolidación o Agrupación

```python
# Esto NO sucede:
# - No se suman montos de la misma cédula
# - No se combinan fechas
# - No se deduplicacidad por cédula
# - No se genera UN registro por cédula

# Lo que SÍ sucede:
# - Cada fila de Excel = 1 registro en tabla pagos
# - Se procesa independientemente
# - Se copia exactamente: cedula, monto, fecha, documento
```

## 🔍 Proceso Detallado: Línea por Línea

### FASE 1: Parseo de Filas

```python
for i, row in enumerate(rows):  # Para cada fila del Excel
    # Detectar formato (Formato D en tu caso):
    if _looks_like_cedula(row[0]) and row[1] is not None and _looks_like_date(row[2]):
        cedula = str(row[0]).strip()                    # Copia Col A
        monto = float(row[1])                           # Copia Col B
        fecha_val = row[2]                              # Copia Col C
        numero_doc = str(row[3])                        # Copia Col D
        
    # Validar
    if not cedula or monto <= 0:
        filas_omitidas += 1
        continue  # Salta esta fila
    
    # Guardar en lista para procesar después
    FilasParseadas.append({
        "cedula": cedula,
        "monto": monto,
        "fecha_val": fecha_val,
        "numero_doc": numero_doc
    })
```

### FASE 2: Validación de Documentos

```python
for item in FilasParseadas:
    cedula = item["cedula"]          # Usa la cédula de esta fila
    monto = item["monto"]            # Usa el monto de esta fila
    numero_doc = item["numero_doc"]  # Usa el documento de esta fila
    
    # Validar que el documento no esté duplicado
    if numero_doc in documentos_duplicados:
        errores.append(f"Documento {numero_doc} duplicado")
        continue
    
    # Crear registro en memoria (no en BD aún)
    p = Pago(
        cedula_cliente=cedula,
        monto_pagado=monto,
        fecha_pago=fecha_val,
        numero_documento=numero_doc,
        estado="PENDIENTE"
    )
    db.add(p)  # Agrega a sesión (transacción)
```

### FASE 3: Inserción en BD

```python
# Todos los Pago objetos se insertan en una transacción:
db.commit()  # Inserta TODOS a la vez

# Resultado: Múltiples registros, UNO POR FILA DEL EXCEL
```

## 📋 Tu Ejemplo Específico

### Input (Tu Excel)
```
Fila 2: V18000758 | 96 | 31-10-2025 | VE/505363350
Fila 3: V18000758 | 96 | 12-11-2025 | VE/490978173
Fila 4: V18000758 | 96 | 12-11-2025 | VE/190978172
Fila 5: V18000758 | 20 | 28-01-2026 | VE/190978172
Fila 6: V20996698 | 96 | 28-08-2025 | 740087406734393
```

### Procesamiento
```
Fila 2: ✅ cedula=V18000758, monto=96, fecha=31-10-2025 → Crea Pago 1
Fila 3: ✅ cedula=V18000758, monto=96, fecha=12-11-2025 → Crea Pago 2
Fila 4: ✅ cedula=V18000758, monto=96, fecha=12-11-2025 → Crea Pago 3
Fila 5: ✅ cedula=V18000758, monto=20, fecha=28-01-2026 → Crea Pago 4
Fila 6: ❌ cedula=V20996698, monto=740087406... → Error: Monto > límite
```

### Inserción en BD
```sql
INSERT INTO pagos (cedula, monto_pagado, fecha_pago, numero_documento, estado) VALUES
('V18000758', 96, '2025-10-31', 'VE/505363350', 'PENDIENTE'),
('V18000758', 96, '2025-11-12', 'VE/490978173', 'PENDIENTE'),
('V18000758', 96, '2025-11-12', 'VE/190978172', 'PENDIENTE'),
('V18000758', 20, '2026-01-28', 'VE/190978172', 'PENDIENTE');
-- Fila 6 falla y se reporta error
```

### Respuesta HTTP
```json
{
  "message": "Carga finalizada",
  "registros_procesados": 4,
  "cuotas_aplicadas": 0,
  "filas_omitidas": 0,
  "errores": [
    "Fila 6: Monto excede límite máximo (999999999999.99): 740087406734393.0"
  ],
  "errores_total": 1
}
```

## Confirmación de Comportamiento

### ✅ SÍ, hace esto:
- ✅ Lee cédula de cada fila (columna A)
- ✅ Lee monto de cada fila (columna B)
- ✅ Lee fecha de cada fila (columna C)
- ✅ Lee documento de cada fila (columna D)
- ✅ Procesa cada fila **independientemente**
- ✅ Copia exactamente los valores sin modificar
- ✅ Inserta UN registro por fila del Excel

### ❌ NO, hace esto:
- ❌ No agrupa/consolida por cédula
- ❌ No suma montos de la misma cédula
- ❌ No combina fechas
- ❌ No genera un registro por cédula
- ❌ No "copia" en el sentido de usar un registro como plantilla

## Validaciones Aplicadas

Cada fila debe cumplir:
1. **Cédula**: Formato válido (ej. V, E, J, Z + dígitos)
2. **Monto**: Entre 0.01 y 999,999,999,999.99
3. **Fecha**: Formato válido (DD-MM-YYYY, etc.)
4. **Documento**: No duplicado (en el archivo ni en BD anterior)

Si una fila falla **una validación**:
- Se reporta el error
- La fila **no se inserta**
- Las otras filas **sí se insertan** (transacción por lotes)

## Conclusión

**Tu pregunta**: "¿Se articula por la cédula y se copia las otras 2 columnas?"

**Respuesta**: 

Parcialmente sí, pero con precisión técnica:
- **Se articula por cédula**: Cada fila independiente, la cédula se extrae de columna A
- **Se copian TODAS las columnas**: Cédula, Monto, Fecha, Documento se copian exactamente
- **No se consolida**: Cada fila = 1 registro, no se agrupan por cédula
- **Formato D soportado**: Cédula | Monto | Fecha | Documento ✅

Si el comportamiento que necesitas es **diferente** (ej. consolidar por cédula), eso requeriría lógica adicional no implementada actualmente.
