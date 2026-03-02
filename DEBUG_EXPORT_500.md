# 🔍 Debug: Error 500 en /exportar/conciliacion

## Problema Reportado
- ✅ Usuario carga Excel exitosamente
- ✅ Datos se guardan en `conciliacion_temporal`
- ❌ Al descargar Excel: **Error 500**

```
XHRGET /api/v1/reportes/exportar/conciliacion?formato=excel
[HTTP/2 500  2262ms]

Error 500 del servidor: Error interno del servidor
```

## Posibles Causas

### 1. **Query de Cliente** ❌ FIJO
```python
# Problema:
cliente = db.execute(select(Cliente).where(Cliente.id == p.cliente_id)).scalar().first()
# .scalar() ya devuelve None o un objeto, .first() es redundante

# Solución:
cliente = db.execute(select(Cliente).where(Cliente.id == p.cliente_id)).scalar()
```

### 2. **BytesIO Buffer Issues**
```python
# Ya fijo:
buf.seek(0)  # Ahora está DESPUÉS de doc.build()
doc.build(story)
return buf.getvalue()
```

### 3. **Posibles Problemas Restantes**

#### A) Empty ConciliacionTemporal Table
Si la tabla `conciliacion_temporal` está vacía:
- La query SELECT retorna []
- El Excel se genera pero con tabla vacía
- Posible: `openpyxl.Workbook().save()` falla?

**Solución:** Verificar que existen datos en tabla temporal

#### B) Missing Imports
```python
import openpyxl  # Está al inicio de función ✅
from reportlab import ...  # Está en función ✅
```

#### C) Openpyxl Version Issue
```python
wb = openpyxl.Workbook()
ws = wb.active  # Podría ser None si no hay sheets?
ws.title = "Conciliacion"  # ❌ AttributeError si ws is None
```

**Solución:** Agregar validación:
```python
ws = wb.active
if ws is None:
    ws = wb.create_sheet("Conciliacion")
ws.title = "Conciliacion"
```

#### D) Large Dataset Memory Issue
Si hay muchos registros:
- 10,000+ filas × 12 columnas
- BytesIO buffer podría agotarse

**Solución:** Usar streaming o split en sheets

## Debugging Steps

### 1. Agregar Logging Detallado
```python
@router.get("/exportar/conciliacion")
def exportar_conciliacion(...):
    try:
        logger.info(f"Exporting {formato} report")
        # ... código ...
        content = _generar_excel_conciliacion(db, fi, ff, cedulas_list)
        logger.info(f"Generated content size: {len(content)} bytes")
        return Response(content=content, ...)
    except Exception as e:
        logger.exception(f"Error in exportar_conciliacion: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. Verificar conciliacion_temporal
```sql
SELECT COUNT(*), SUM(total_financiamiento), SUM(total_abonos) 
FROM conciliacion_temporal;
```

### 3. Test Directo
```python
# En API test:
response = client.get("/api/v1/reportes/exportar/conciliacion?formato=excel")
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"Size: {len(response.content)}")
```

## Cambios Realizados Hasta Ahora

| Commit | Cambio |
|--------|--------|
| `5227321d` | Fix buf.seek() order en PDF |
| `424d24ec` | Fix .scalar().first() redundancia |

## Próximos Pasos Sugeridos

1. **Agregar Logging** en _generar_excel_conciliacion
2. **Test manual** con Postman/curl
3. **Verificar BD** - datos en conciliacion_temporal?
4. **Revisar logs de Render** para detalles del error
5. **Agregar try-except** en toda la función con logging

## Líneas Críticas a Revisar

- **Línea 220-240:** Queries de Prestamo y ConciliacionTemporal
- **Línea 283-292:** Creación de Workbook y headers
- **Línea 293-319:** Loop for p in prestamos
- **Línea 320-322:** BytesIO save and return

---

**Nota:** El error 500 sin detalles sugiere una excepción no capturada.  
Agregar logging y try-except será clave para identificar la causa real.
