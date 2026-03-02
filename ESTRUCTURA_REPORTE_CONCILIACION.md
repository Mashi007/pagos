# 📋 Estructura del Reporte de Conciliación

## ¿Por Qué las Columnas E y F Están Vacías?

### Flujo Actual de Datos

```
Usuario carga Excel con columnas:
A: Cédula
B: Total Financiamiento
C: Total Abonos
D: (ignorado)
E: Dato Extra 1 (opcional)
F: Dato Extra 2 (opcional)
        ↓
Almacena en conciliacion_temporal (BD)
        ↓
Genera reporte Excel con:
- Datos de prestamos (APROBADO)
- Busca coincidencia por CÉDULA
- Si coincide: llena columna E y F
- Si NO coincide: quedan vacías ""
```

### Problema: Coincidencia de Cédulas

```python
# Línea 304-306
concilia = concilia_por_cedula.get(cedula) if cedula and cedula != "no existe" else None
col_e = concilia.columna_e if concilia else ""  # ← Vacía si concilia es None
col_f = concilia.columna_f if concilia else ""  # ← Vacía si concilia es None
```

**Razones por las que concilia es None:**

1. **La cédula en prestamo NO coincide con la cédula en conciliacion_temporal**
   - Prestamo tiene: "V12345678"
   - Conciliacion tiene: "V 12345678" (espacios)
   - Resultado: NO coinciden → E y F vacías

2. **No hay datos en conciliacion_temporal**
   - Usuario no cargó Excel
   - O tabla está vacía
   - Resultado: concilia_por_cedula está vacío

3. **La cédula es "no existe"**
   - Prestamo no tiene cliente
   - Cédula asignada como "no existe"
   - Lógica: no busca en concilia_por_cedula
   - Resultado: E y F vacías

### Estructura Esperada del Excel Cargado

**Entrada (Lo que usuario carga):**
```
Columna A | Columna B              | Columna C      | Columna E    | Columna F
Cédula    | Total Financiamiento   | Total Abonos   | Dato Extra 1 | Dato Extra 2
----------|------------------------|----------------|--------------|--------------
V1234567  | 10000.00              | 5000.00        | Info1        | Info2
V7654321  | 20000.00              | 10000.00       | Extra        | Data
```

**Salida (Reporte descargado):**
```
Nombre    | Cédula    | # Crédito | Total fin | Col E  | Col F | Total pagos | ...
----------|-----------|-----------|-----------|--------|-------|-------------|----
Juan P.   | V1234567  | 1         | 10000     | Info1  | Info2 | 5000        | ...
Pedro G.  | V7654321  | 2         | 20000     | Extra  | Data  | 10000       | ...
```

---

## ¿Cómo Llenar las Columnas E y F?

### Opción 1: Asegurar Coincidencia Exacta de Cédulas

**Problema Común:** Espacios o caracteres especiales

```python
# Mejorar el parseo de cédula en dialogo de carga:
cedula_norm = str(cedula).strip().upper()  # Remover espacios

# En database también:
for f in filas_ok:
    f["cedula"] = str(f["cedula"]).strip().upper()
```

### Opción 2: Debug - Verificar Coincidencias

**SQL para verificar:**
```sql
-- Ver qué cédulas están en conciliacion_temporal
SELECT DISTINCT cedula FROM conciliacion_temporal;

-- Ver qué cédulas están en prestamos
SELECT DISTINCT cedula FROM prestamo WHERE estado = 'APROBADO' LIMIT 10;

-- Comparar:
SELECT p.cedula, ct.cedula 
FROM prestamo p 
LEFT JOIN conciliacion_temporal ct ON p.cedula = ct.cedula
WHERE p.estado = 'APROBADO'
LIMIT 10;
```

### Opción 3: Hacer Columnas E y F Requeridas (Obligatorias)

Si son datos importantes, modificar validación:

```python
# En DialogConciliacion.tsx (frontend)
if (!f.columna_e || !f.columna_e.trim()) {
  errores.push(`Fila ${i + 1}: Columna E es requerida`)
}
if (!f.columna_f || !f.columna_f.trim()) {
  errores.push(`Fila ${i + 1}: Columna F es requerida`)
}
```

---

## Comparación: Excel Cargado vs Excel Descargado

```
ARCHIVO CARGADO:              ARCHIVO DESCARGADO:
┌─────────────────────────┐   ┌──────────────────────────────────────────┐
│ A  | B      | C    | E | F │ │ Nombre | Ced | # Cred | Tot | E | F | ... │
├─────────────────────────┤   ├──────────────────────────────────────────┤
│ V12 │ 10000 │ 5000 │ ? │ ? │ │ Juan   │ V12 │ 1     │ 10000│ ? │ ? │ ... │
│ V34 │ 20000 │ 10000│ ? │ ? │ │ Pedro  │ V34 │ 2     │ 20000│ ? │ ? │ ... │
└─────────────────────────┘   └──────────────────────────────────────────┘
        ↓                               ↑
    Datos cargados              Datos del reporte
```

**Problema:** Si cédulas no coinciden exactamente, E y F quedan vacías

---

## Estructura Actual del Backend

### Tabla: conciliacion_temporal
```sql
CREATE TABLE conciliacion_temporal (
  id INTEGER PRIMARY KEY,
  cedula VARCHAR(20) NOT NULL,          -- Clave para buscar coincidencia
  total_financiamiento NUMERIC(14,2),   -- Info adicional
  total_abonos NUMERIC(14,2),           -- Info adicional
  columna_e VARCHAR(255) OPTIONAL,      -- ← Aparece en Col E si hay coincidencia
  columna_f VARCHAR(255) OPTIONAL,      -- ← Aparece en Col F si hay coincidencia
  creado_en TIMESTAMP
);
```

### Lógica en _generar_excel_conciliacion():
```python
# 1. Cargar conciliacion_temporal a diccionario
concilia_por_cedula = {}
for row in db.execute(select(ConciliacionTemporal)).fetchall():
    concilia_por_cedula[row.cedula] = row

# 2. Para cada prestamo, buscar coincidencia
for prestamo in prestamos:
    cedula = prestamo.cedula
    concilia = concilia_por_cedula.get(cedula)  # ← Búsqueda por cédula
    
    # 3. Si hay coincidencia, usar columna_e y columna_f
    col_e = concilia.columna_e if concilia else ""
    col_f = concilia.columna_f if concilia else ""
```

---

## Solución Recomendada

### 1. **Validar Coincidencias Antes de Descargar**

En frontend, agregar un "Preview" que muestre coincidencias:

```typescript
// En DialogConciliacion.tsx - agregar preview
async function verificarCoincidencias() {
  const resumen = await reporteService.obtenerResumenConciliacion()
  // Mostrar: "150 cédulas loaded, 145 con coincidencias (96.7%)"
}
```

### 2. **Normalizar Cédulas**

Agregar normalization en ambos lados:

```python
# Backend - normalization function
def _normalizar_cedula(cedula: str) -> str:
    return str(cedula).strip().upper()
```

### 3. **Logs para Debugging**

Agregar logging para ver qué cédulas coinciden:

```python
# En _generar_excel_conciliacion
logger.info(f"Loaded {len(concilia_por_cedula)} cédulas from conciliacion_temporal")
logger.info(f"Processing {len(prestamos)} prestamos")

matches = 0
for prestamo in prestamos:
    if prestamo.cedula in concilia_por_cedula:
        matches += 1

logger.info(f"Coincidences found: {matches}/{len(prestamos)}")
```

---

## Respuesta Corta

**Las columnas E y F están vacías porque:**

1. ✅ Sistema funciona correctamente
2. ❌ **Pero no hay coincidencias de cédulas** entre:
   - Prestamos (de Prestamos table)
   - Datos cargados (de conciliacion_temporal table)

**Opciones:**

1. **Cargar datos que coincidan** con cédulas de prestamos existentes
2. **Hacer coincidencias exactas** - validar formato de cédula
3. **Hacer E y F opcionales** - dejar vacías si no hay datos
4. **Hacer E y F requeridos** - validar en upload

Recomendación: Opción 1 o 2 (asegurar coincidencias exactas)
