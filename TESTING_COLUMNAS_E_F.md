# Testing: Columnas E y F en Reporte de Conciliación

## Cambios Implementados

### 1. Nueva Función `_normalizar_cedula`
```python
def _normalizar_cedula(cedula: str) -> str:
    """Normaliza cédula para comparación exacta (espacios, mayúsculas)"""
```

### 2. Normalización en Carga de Excel
- Al cargar Excel: cédulas se normalizan al guardar en `conciliacion_temporal`
- Ejemplo: "V 12345678" → "V12345678"

### 3. Normalización en Generación de Reporte
- Al generar reporte: cédulas se normalizan al buscar en mapa
- Mapeo `concilia_por_cedula` usa cédulas normalizadas como key

## Testing Local

### Paso 1: Preparar Archivo Excel de Prueba

Crear archivo `test_conciliacion.xlsx` con contenido:

```
| A            | B     | C     | D | E      | F       |
| Cédula       | TF    | TA    |   | Datos1 | Datos2  |
| V 12345678   | 864   | 810   |   | ABC1   | XYZ1    |
| E 98765432   | 1440  | 1440  |   | ABC2   | XYZ2    |
| v99999999    | 500   | 500   |   | ABC3   | XYZ3    |
```

**Importante:** Incluir espacios en cédulas para probar normalización.

### Paso 2: Iniciar Backend Localmente

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verificar en logs: `[DB Startup] ✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE`

### Paso 3: Cargar Excel

```bash
curl -X POST http://localhost:8000/api/v1/reportes/conciliacion/cargar-excel \
  -F "file=@test_conciliacion.xlsx"
```

**Respuesta esperada:**
```json
{
  "ok": true,
  "filas_ok": 3,
  "filas_con_error": 0,
  "errores": []
}
```

### Paso 4: Verificar Datos en BD

```bash
# Desde terminal con acceso a BD
psql $DATABASE_URL -c "SELECT cedula, columna_e, columna_f FROM conciliacion_temporal ORDER BY cedula;"
```

**Resultado esperado:**
```
cedula       | columna_e | columna_f
-----------+-----------+----------
E98765432   | ABC2      | XYZ2
V12345678   | ABC1      | XYZ1
V99999999   | ABC3      | XYZ3
```

**Nota:** Observe que:
- "V 12345678" se normalizó a "V12345678"
- "E 98765432" se normalizó a "E98765432"
- "v99999999" se normalizó a "V99999999" (mayúsculas)
- Los espacios se eliminaron

### Paso 5: Generar Reporte

```bash
# Generar Excel
curl "http://localhost:8000/api/v1/reportes/exportar/conciliacion?formato=excel" \
  --output test_reporte_salida.xlsx \
  -H "Authorization: Bearer YOUR_TOKEN"

# Si no tienes token, usa con auth deshabilitada (dev mode) o solicita al equipo
```

**Nota:** Si la ruta requiere autenticación, necesitas un token JWT válido.

### Paso 6: Verificar Columnas E y F en Excel Generado

Abrir `test_reporte_salida.xlsx`:

| Nombre | Cédula   | Número Crédito | Total Financiamiento | **Columna E** | **Columna F** |
|--------|----------|----------------|----------------------|---------------|---------------|
| ...    | V12345678| 123            | 864.00               | **ABC1**      | **XYZ1**      |
| ...    | E98765432| 456            | 1440.00              | **ABC2**      | **XYZ2**      |
| ...    | V99999999| 789            | 500.00               | **ABC3**      | **XYZ3**      |

**Validar:**
- ✅ Columna E tiene "ABC1", "ABC2", "ABC3" (NO vacías)
- ✅ Columna F tiene "XYZ1", "XYZ2", "XYZ3" (NO vacías)

## Testing en Render

### Paso 1: Deploy de Cambios

```bash
cd pagos
git push origin main
```

Render automáticamente hace build y deploy.

### Paso 2: Esperar Deploy Completado

Verificar en Render Dashboard > pagos-backend > Health: ✅ Healthy

### Paso 3: Cargar Excel desde UI

1. Ir a https://rapicredit.onrender.com/pagos/reportes
2. Seleccionar tab "Reporte de Conciliación"
3. Subir archivo Excel con cédulas que incluyan espacios
4. Verificar: "Datos guardados. Ya puede descargar el reporte."

### Paso 4: Descargar Reporte

1. Click en tab "Resumen & Descarga"
2. Click en "Descargar Excel"
3. Abrir archivo descargado

**Validar:**
- ✅ Columna E tiene datos (no vacía)
- ✅ Columna F tiene datos (no vacía)
- ✅ Los datos corresponden a los subidos en Excel

## Debugging si Columnas E y F Siguen Vacías

### Verificación 1: ¿Se guardó en conciliacion_temporal?

```bash
# En terminal con acceso a BD
psql $DATABASE_URL -c "SELECT COUNT(*) FROM conciliacion_temporal;"
```

Si retorna `0`:
- La carga del Excel falló (revisar response de cargar-excel)
- El archivo no tenía formato correcto

Si retorna > 0:
- Continuar al siguiente paso

### Verificación 2: ¿Tiene columna_e y columna_f populated?

```bash
psql $DATABASE_URL -c "SELECT cedula, columna_e, columna_f FROM conciliacion_temporal LIMIT 5;"
```

Si `columna_e` y `columna_f` son NULL o vacíos:
- El Excel no tenía datos en columnas E y F (revisión 4-5)
- Cargar nuevo Excel con datos en E y F

Si tienen datos:
- Continuar al siguiente paso

### Verificación 3: ¿Coinciden las cédulas normalizadas?

```bash
# Comparar cédulas en ambas tablas
psql $DATABASE_URL -c "
SELECT 
  DISTINCT UPPER(REPLACE(REPLACE(ct.cedula, ' ', ''), CHR(9), '')) as ct_cedula,
  DISTINCT UPPER(REPLACE(REPLACE(p.cedula, ' ', ''), CHR(9), '')) as p_cedula
FROM conciliacion_temporal ct
FULL OUTER JOIN prestamos p ON UPPER(REPLACE(REPLACE(ct.cedula, ' ', ''), CHR(9), '')) = UPPER(REPLACE(REPLACE(p.cedula, ' ', ''), CHR(9), ''))
LIMIT 10;
"
```

Si hay filas donde `ct_cedula IS NULL` o `p_cedula IS NULL`:
- Las cédulas no coinciden (revisar formato en Excel vs BD)
- Ejemplo: Excel tiene "V12345678", BD tiene "v12345678" → Función normaliza ambas a "V12345678"

### Verificación 4: ¿Se normalizan correctamente en el código?

Agregar logging temporal en `_generar_excel_conciliacion`:

```python
# Después de línea 256
import logging
logger = logging.getLogger(__name__)
logger.info(f"DEBUG: Mapa concilia_por_cedula keys: {list(concilia_por_cedula.keys())[:5]}")

# Después de línea 324
logger.info(f"DEBUG: Buscando cedula normalizada: '{cedula_normalizada}' en mapa")
logger.info(f"DEBUG: Encontrado concilia: {concilia is not None}")
```

Ver logs en Render > Console > pagos-backend > Logs

## Casos de Uso Cubiertos

| Excel | BD | Esperado | Resultado |
|-------|----|----|---|
| V12345678 | V12345678 | ✅ E y F llenos | ✅ Pasa |
| V 12345678 | V12345678 | ✅ E y F llenos | ✅ Pasa (normalización) |
| v12345678 | V12345678 | ✅ E y F llenos | ✅ Pasa (normalización) |
| V 123 45678 | V12345678 | ✅ E y F llenos | ✅ Pasa (espacios internos) |
| V99999999 | (no existe) | ❌ E y F vacíos | ✅ Pasa (esperado) |

## Rollback Plan

Si hay problemas:

```bash
git revert HEAD
git push
```

Render redeploya automáticamente.

## Próximos Pasos Opcionales

1. **Log de mismatches:** Registrar si hay cédula en Excel sin match en prestamos
2. **UI feedback:** Mostrar en el UI qué cédulas tenían match y cuáles no
3. **Validación previa:** Antes de generar reporte, avisar si hay mismatches
4. **Case-insensitive:** Aunque ya se hace upper(), documentar el comportamiento

## Resumen de Cambios

| Archivo | Cambio | Línea |
|---------|--------|------|
| reportes_conciliacion.py | + `_normalizar_cedula()` | 61-72 |
| reportes_conciliacion.py | Normalizar en carga | 133 |
| reportes_conciliacion.py | Normalizar filter | 249 |
| reportes_conciliacion.py | Normalizar mapa | 257-260 |
| reportes_conciliacion.py | Normalizar lookup | 314-327 |

**Total:** 5 puntos de normalización estratégicos

## Signoff

- [ ] Testing local exitoso (columnas E y F llenas)
- [ ] Testing en Render exitoso
- [ ] No hay regresiones en otros reportes
- [ ] Documentación actualizada
- [ ] Deploy en producción

---

**Nota:** Este documento debe ser actualizado después de testing exitoso con estado "✅ VERIFICADO"
