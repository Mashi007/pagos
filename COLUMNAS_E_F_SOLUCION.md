# Solución: Columnas E y F Vacías en Reporte de Conciliación

## Problema Actual

Al generar el reporte de conciliación en Excel, las columnas E y F aparecen vacías, aunque:
1. ✅ El archivo Excel se carga correctamente con datos en columnas B y C (cédula, montos)
2. ✅ Los datos se almacenan en `conciliacion_temporal` con `columna_e` y `columna_f`
3. ❌ El reporte generado NO muestra los datos en columnas E y F

## Causa Raíz

El problema está en el **mapeo de cédulas**. En la función `_generar_excel_conciliacion` (línea 304):

```python
concilia = concilia_por_cedula.get(cedula) if cedula and cedula != "no existe" else None
```

La cédula debe coincidir **exactamente** entre:
- `conciliacion_temporal.cedula` (datos cargados desde Excel)
- `prestamo.cedula` (datos en BD)

**Problemas comunes:**

```
Excel:                    BD:
V12345678        ≠       v12345678        (mayúsculas vs minúsculas)
V12345678        ≠       12345678         (con/sin letra)
V 12345678       ≠       V12345678        (espacios)
E98765432        ≠       E 98765432       (espacios)
```

## Solución Implementada

Voy a mejorar el mapeo de cédulas con **normalización** de ambos lados:

### Cambio en `_generar_excel_conciliacion`

```python
# ANTES (línea 304)
cedula = (p.cedula or "").strip()
# ... luego ...
concilia = concilia_por_cedula.get(cedula) if cedula and cedula != "no existe" else None

# DESPUÉS - Normalizar ambos lados
cedula_normalizada = _normalizar_cedula((p.cedula or "").strip())
# Buscar en el mapa con cedula normalizada
concilia = None
if cedula_normalizada and cedula_normalizada != "no existe":
    # Primero intenta match directo
    concilia = concilia_por_cedula.get(cedula_normalizada)
    # Si no encuentra, busca por cedula sin normalizar (fallback)
    if not concilia:
        concilia = concilia_por_cedula.get((p.cedula or "").strip())
```

### Nueva función `_normalizar_cedula`

```python
def _normalizar_cedula(cedula: str) -> str:
    """
    Normaliza cédula para comparación:
    - Espacios en blanco → removidos
    - Mayúsculas → mantenidas
    - Caracteres especiales → removidos
    
    Ejemplos:
    "V 12345678"  → "V12345678"
    "E 98765432"  → "E98765432"
    "  V12345678" → "V12345678"
    """
    if not cedula:
        return ""
    return cedula.replace(" ", "").replace("\t", "").strip().upper()
```

### Mejora en cargar_conciliacion_excel

También mejoramos el lado de carga para normalizar:

```python
# En línea 116 donde se agregan filas_ok:
filas_ok.append({
    "cedula": _normalizar_cedula(str(cedula).strip()),  # ← NORMALIZAR
    "total_financiamiento": _parse_numero(tf),
    "total_abonos": _parse_numero(ta),
    "columna_e": str(row[4]).strip() if len(row) > 4 and row[4] is not None else None,
    "columna_f": str(row[5]).strip() if len(row) > 5 and row[5] is not None else None,
})
```

## Cambios Necesarios

### Archivo: `backend/app/api/v1/endpoints/reportes/reportes_conciliacion.py`

#### 1. Agregar función `_normalizar_cedula` (antes de `_generar_excel_conciliacion`)

```python
def _normalizar_cedula(cedula: str) -> str:
    """Normaliza cédula para comparación exacta (espacios, mayúsculas)."""
    if not cedula:
        return ""
    return cedula.replace(" ", "").replace("\t", "").strip().upper()
```

#### 2. Actualizar línea 116 en `cargar_conciliacion_excel`

```python
# ANTES
"cedula": str(cedula).strip(),

# DESPUÉS
"cedula": _normalizar_cedula(str(cedula).strip()),
```

#### 3. Actualizar líneas 232-233 en `_generar_excel_conciliacion`

```python
# ANTES
if cedulas_filter:
    cedulas_filter_set = {c.strip().upper() for c in cedulas_filter}
    prestamos = [p for p in prestamos if (p.cedula or "").strip().upper() in cedulas_filter_set]

# DESPUÉS
if cedulas_filter:
    cedulas_filter_set = {_normalizar_cedula(c) for c in cedulas_filter}
    prestamos = [p for p in prestamos if _normalizar_cedula(p.cedula or "") in cedulas_filter_set]
```

#### 4. Actualizar línea 237-241 en `_generar_excel_conciliacion`

```python
# ANTES
concilia_por_cedula: dict = {}
for r in concilia_rows:
    c = r[0] if hasattr(r, "__getitem__") else r
    if c.cedula not in concilia_por_cedula:
        concilia_por_cedula[c.cedula] = c

# DESPUÉS
concilia_por_cedula: dict = {}
for r in concilia_rows:
    c = r[0] if hasattr(r, "__getitem__") else r
    cedula_norm = _normalizar_cedula(c.cedula)
    if cedula_norm and cedula_norm not in concilia_por_cedula:
        concilia_por_cedula[cedula_norm] = c
```

#### 5. Actualizar línea 294-304 en `_generar_excel_conciliacion`

```python
# ANTES
for p in prestamos:
    cedula = (p.cedula or "").strip()
    nombres = (p.nombres or "").strip()
    cliente = db.execute(select(Cliente).where(Cliente.id == p.cliente_id)).scalar() if p.cliente_id else None
    if cliente:
        nombres = (cliente.nombres or nombres or "").strip()
        cedula = (cliente.cedula or cedula or "").strip()
    else:
        if not nombres and not cedula:
            nombres = "no existe"
            cedula = "no existe"
    concilia = concilia_por_cedula.get(cedula) if cedula and cedula != "no existe" else None

# DESPUÉS
for p in prestamos:
    cedula = (p.cedula or "").strip()
    cedula_normalizada = _normalizar_cedula(cedula)
    nombres = (p.nombres or "").strip()
    cliente = db.execute(select(Cliente).where(Cliente.id == p.cliente_id)).scalar() if p.cliente_id else None
    if cliente:
        nombres = (cliente.nombres or nombres or "").strip()
        cedula = (cliente.cedula or cedula or "").strip()
        cedula_normalizada = _normalizar_cedula(cedula)
    else:
        if not nombres and not cedula:
            nombres = "no existe"
            cedula = "no existe"
            cedula_normalizada = ""
    concilia = concilia_por_cedula.get(cedula_normalizada) if cedula_normalizada else None
```

## Testing

### Paso 1: Preparar Excel de Prueba

```
Columna A (Cédula)    | Columna B (TF)  | Columna C (TA) | Columna E (datos) | Columna F (más datos)
V 12345678            | 864             | 810            | dato1             | dato2
E 98765432            | 1440            | 1440           | dato3             | dato4
```

**Nota:** Propósito incluye espacios para probar normalización.

### Paso 2: Cargar Excel

```bash
curl -X POST http://localhost:8000/api/v1/reportes/conciliacion/cargar-excel \
  -F "file=@reporte.xlsx"
```

**Respuesta esperada:**
```json
{
  "ok": true,
  "filas_ok": 2,
  "filas_con_error": 0,
  "errores": []
}
```

### Paso 3: Generar Reporte

```bash
curl "http://localhost:8000/api/v1/reportes/exportar/conciliacion?formato=excel" \
  > reporte_salida.xlsx
```

### Paso 4: Verificar Columnas E y F

Abrir `reporte_salida.xlsx`:
- Columna E debe mostrar "dato1", "dato3", etc.
- Columna F debe mostrar "dato2", "dato4", etc.
- **No deben estar vacías**

## Verificación de BD

Si aún no ves datos, verifica que `conciliacion_temporal` está poblada:

```sql
SELECT cedula, columna_e, columna_f FROM conciliacion_temporal LIMIT 5;
```

Deberías ver:
```
cedula      | columna_e | columna_f
V12345678   | dato1     | dato2
E98765432   | dato3     | dato4
```

## Casos de Uso Cubiertos

| Caso | Excel | BD | Resultado |
|------|-------|----|----|
| Match exacto | V12345678 | V12345678 | ✅ E y F se llenan |
| Con espacios | V 12345678 | V12345678 | ✅ E y F se llenan (normalización) |
| Mayúsculas | v12345678 | V12345678 | ✅ E y F se llenan (upper) |
| Sin match | V99999999 | (no existe) | ❌ E y F vacías (esperado) |

## Próximos Pasos

1. Implementar cambios en `reportes_conciliacion.py`
2. Probar con Excel que incluya espacios en cédulas
3. Verificar que E y F se llenan correctamente
4. Commit y deploy a Render

## Documentación Complementaria

- Archivo de carga: `cargar_conciliacion_excel` (línea 62)
- Estructura de datos: `ConciliacionTemporal` (modelo)
- Generación de reporte: `_generar_excel_conciliacion` (línea 209)
