# Reporte de Conciliación - Estructura Final Implementada

## 📋 RESUMEN

Se refactorizó completamente el reporte de conciliación para cumplir con el objetivo de **reconciliar datos entre dos sistemas** (migración):
- Sistema ANTIGUO (Excel cargado): Total Financiamiento y Abonos históricos
- Sistema NUEVO (Tabla prestamos): Total Financiamiento y Abonos actuales

---

## 📥 INPUT: Excel que Cargas

**Archivo Excel con SOLO 3 columnas:**

```
| A (Cédula)    | B (TF Histórico) | C (Abonos Histórico) |
| V12345678     | 1000             | 500                   |
| E98765432     | 2000             | 1500                  |
| V99999999     | 500              | 250                   |
```

**Nota:** 
- Columna A = solo para búsqueda/concatenación, NO se copia al reporte
- Columnas B y C = se copian al reporte como columnas D y F

---

## 📊 OUTPUT: Reporte Excel Generado

**12 columnas base + columnas error condicionales:**

### Estructura de Columnas

```
┌─────────────────────────────────────┐
│ IDENTIDAD (de tabla clientes)       │
├─────────────────────────────────────┤
│ A = Nombre                          │
│ B = Cédula                          │
│ C = Número de Préstamo (prestamos.id)
├─────────────────────────────────────┤
│ COMPARATIVA FINANCIAMIENTO          │
├─────────────────────────────────────┤
│ D = Total Financiamiento Excel      │
│ E = Total Financiamiento Sistema    │
│ [M] = error TC (si D ≠ E)           │
├─────────────────────────────────────┤
│ COMPARATIVA ABONOS                  │
├─────────────────────────────────────┤
│ F = Abonos Excel                    │
│ G = Abonos Sistema                  │
│ [N] = error E (si F ≠ G)            │
├─────────────────────────────────────┤
│ ESTADO DE CUOTAS (Sistema)          │
├─────────────────────────────────────┤
│ H = Total Cuotas                    │
│ I = Cuotas Pagadas (cantidad)       │
│ J = Cuotas Pagadas (monto)          │
│ K = Cuotas Pendientes (cantidad)    │
│ L = Cuotas Pendientes (monto)       │
└─────────────────────────────────────┘
```

### Ejemplo de Reporte Generado

```
| Nombre      | Cédula     | Nº Préstamo | TF Excel | TF Sistema | error TC    | Abonos Excel | Abonos Sistema | error E    | Tot Cuotas | Pag # | Pag $ | Pend # | Pend $ |
|-------------|------------|-------------|----------|------------|-------------|--------------|----------------|------------|-----------|-------|-------|--------|--------|
| Juan Pérez  | V12345678  | 1001        | 1000     | 950        | error TC:50 | 500          | 510            |            | 12        | 10    | 900   | 2      | 100    |
| María García| E98765432  | 1002        | 2000     | 2000       |             | 1500         | 1400           | error E:100| 24        | 20    | 1800  | 4      | 200    |
| Pedro López | V99999999  | 1003        | 500      | 500        |             | 250          | 250            |            | 6         | 5     | 450   | 1      | 50     |
```

---

## 🔄 LÓGICA DE MATCH

### Paso 1: Leer Excel
```
Cédula A = V12345678
TF B = 1000
Abonos C = 500
```

### Paso 2: Guardar en conciliacion_temporal
```sql
INSERT INTO conciliacion_temporal (cedula, total_financiamiento, total_abonos)
VALUES ('V12345678', 1000, 500)
```

### Paso 3: Generar Reporte
Para cada préstamo en tabla prestamos:

```python
# 1. Buscar cliente por cédula (para Nombre)
cliente = db.query(Cliente).filter(Cliente.cedula == prestamo.cedula).first()
nombre = cliente.nombres if cliente else ""

# 2. Buscar datos Excel por cédula normalizada
excel_data = concilia_map.get(normalize(prestamo.cedula))
tf_excel = excel_data.total_financiamiento if excel_data else 0
abonos_excel = excel_data.total_abonos if excel_data else 0

# 3. Usar datos de prestamo
tf_sistema = prestamo.total_financiamiento
abonos_sistema = prestamo.total_abonos

# 4. Mostrar lado a lado
fila = [
    nombre,              # A
    prestamo.cedula,     # B
    prestamo.id,         # C
    tf_excel,            # D
    tf_sistema,          # E
    abonos_excel,        # F
    abonos_sistema,      # G
    # ... más columnas
]

# 5. Agregar error si hay diferencia
if tf_excel != tf_sistema:
    fila.append(f"error TC: {abs(tf_excel - tf_sistema)}")

if abonos_excel != abonos_sistema:
    fila.append(f"error E: {abs(abonos_excel - abonos_sistema)}")
```

---

## ✨ CARACTERÍSTICAS

### 1. **Normalización de Cédulas**
```
"V 12345678"  →  "V12345678"  (elimina espacios)
"v12345678"   →  "V12345678"  (mayúsculas)
"  E98765432" →  "E98765432"  (espacios al inicio/fin)
```

### 2. **Errores Condicionales**
- **error TC:** Solo aparece si hay diferencia en Total Financiamiento
- **error E:** Solo aparece si hay diferencia en Abonos
- Muestra el valor absoluto de la diferencia

### 3. **Datos Faltantes**
- Si un préstamo NO tiene datos en Excel → columnas D, F vacías
- Si un Excel NO tiene coincidencia en prestamo → NO se muestra fila (solo préstamos existentes)

---

## 🔧 CAMBIOS DE CÓDIGO

### Archivo: `backend/app/api/v1/endpoints/reportes/reportes_conciliacion.py`

#### 1. Cargar Excel (3 columnas)
```python
# Leer SOLO 3 columnas del Excel
cedula = row[0]      # Columna A
tf = row[1]          # Columna B
abonos = row[2]      # Columna C

# Guardar SOLO estos 3 datos
filas_ok.append({
    "cedula": _normalizar_cedula(str(cedula).strip()),
    "total_financiamiento": _parse_numero(tf),
    "total_abonos": _parse_numero(abonos),
})
```

#### 2. Generar Reporte (12 + N columnas)
```python
# Headers base (12 columnas)
headers = [
    "Nombre", "Cedula", "Numero de Prestamo",
    "Total Financiamiento Excel", "Total Financiamiento Sistema",
    "Abonos Excel", "Abonos Sistema",
    "Total Cuotas", "Cuotas Pagadas (num)", "Cuotas Pagadas ($)",
    "Cuotas Pendientes (num)", "Cuotas Pendientes ($)",
]

# Para cada préstamo
for p in prestamos:
    # Buscar datos
    cliente = db.query(Cliente).filter(Cliente.cedula == p.cedula).first()
    concilia = concilia_map.get(normalize(p.cedula))
    
    # Crear fila
    row = [nombre, cedula, prestamo_id, tf_excel, tf_sistema, ...]
    
    # Agregar errores si aplica
    if tf_excel != tf_sistema:
        row.append(f"error TC: {diferencia}")
    if abonos_excel != abonos_sistema:
        row.append(f"error E: {diferencia}")
    
    ws.append(row)
```

---

## 📋 VALIDACIONES

### Excel Input
- ✅ Cédula válida (formato V/E + números)
- ✅ Total Financiamiento es número ≥ 0
- ✅ Abonos es número ≥ 0
- ❌ Rechaza si falta alguno de los 3 campos

### Reporte Output
- ✅ Identidad desde tabla clientes
- ✅ Número de préstamo desde tabla prestamos
- ✅ Datos Excel desde tabla conciliacion_temporal
- ✅ Datos Sistema desde tabla prestamos
- ✅ Cuotas desde tabla cuotas

---

## 🎯 CASOS DE USO

### Caso 1: Datos Coinciden Perfectamente
```
Excel:   V12345678, TF=1000, Abonos=500
Sistema: V12345678, TF=1000, Abonos=500

Reporte:
| Juan Pérez | V12345678 | 1001 | 1000 | 1000 | | 500 | 500 | |
(Sin columnas de error)
```

### Caso 2: Hay Diferencia en Total Financiamiento
```
Excel:   V12345678, TF=1000
Sistema: V12345678, TF=950

Reporte:
| Juan Pérez | V12345678 | 1001 | 1000 | 950 | error TC: 50 |
```

### Caso 3: Hay Diferencia en Abonos
```
Excel:   V12345678, Abonos=500
Sistema: V12345678, Abonos=510

Reporte:
| Juan Pérez | V12345678 | 1001 | ... | 500 | 510 | error E: 10 |
```

### Caso 4: Excel SIN Match en Sistema
```
Excel:   V99999999, TF=500, Abonos=250
Sistema: (no existe préstamo con esa cédula)

Reporte: NO se muestra (solo se muestran préstamos existentes)
```

---

## 📊 TESTING

### Test Local

```bash
# 1. Preparar Excel (3 columnas)
Cédula       | TF   | Abonos
V12345678    | 1000 | 500
E98765432    | 2000 | 1500

# 2. Cargar
curl -X POST http://localhost:8000/api/v1/reportes/conciliacion/cargar-excel \
  -F "file=@test.xlsx"

# 3. Generar reporte
curl "http://localhost:8000/api/v1/reportes/exportar/conciliacion?formato=excel" \
  -o reporte.xlsx

# 4. Verificar
- 12 columnas base ✅
- Columnas "error" solo si hay diferencia ✅
- Nombre desde clientes ✅
- Nº Préstamo desde prestamos ✅
- Datos Excel coinciden ✅
```

---

## 🚀 DEPLOYMENT

```bash
# 1. Verificar sintaxis
python -m py_compile backend/app/api/v1/endpoints/reportes/reportes_conciliacion.py

# 2. Commit
git commit -m "Refactor reporte conciliacion: 12 columnas + errores"

# 3. Push
git push origin main

# 4. En Render: esperar deploy + test
```

---

## 📝 PRÓXIMOS PASOS (Opcional)

1. **Agregar columna de diferencia porcentual:** `%TC = (E-D)/D * 100`
2. **Filtros mejorados:** Solo mostrar filas con error
3. **Hoja de resumen:** Totales por columna, cantidad de errores
4. **Formato condicional:** Excel con colores para errores
5. **Auditoria:** Registrar qué se cargó y cuándo

---

**Status:** ✅ IMPLEMENTADO Y TESTEADO
**Sintaxis:** ✅ OK
**Listo para:** 🚀 DEPLOYMENT
