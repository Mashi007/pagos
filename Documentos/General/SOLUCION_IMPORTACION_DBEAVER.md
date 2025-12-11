# ✅ Solución: Importación en DBeaver

## ✅ Confirmación: Tabla Funciona

La inserción manual funcionó (COUNT = 1), lo que confirma que:
- ✅ La tabla `clientes_temp` está correcta
- ✅ La estructura es válida
- ✅ El problema está en el **CSV o en el mapeo de DBeaver**

## 🔧 Soluciones

### Opción 1: Corregir Mapeo en DBeaver

**Problemas comunes en el mapeo:**

1. **Nombres de columnas no coinciden:**
   - Verificar que los encabezados del CSV coincidan EXACTAMENTE
   - Sin espacios al final
   - Sin diferencias de mayúsculas/minúsculas

2. **Columnas no mapeadas:**
   - Todas las columnas del CSV deben tener un target
   - Verificar que no haya columnas sin mapear

3. **Tipos de datos incorrectos:**
   - `fecha_nacimiento` puede ser texto (se convertirá después)
   - `activo` puede ser texto (se convertirá después)

### Opción 2: Cambiar Configuración de Importación

**En DBeaver, antes de importar:**

1. **Desmarcar "Use multi-row value insert"**
   - Importa fila por fila
   - Muestra errores específicos

2. **Cambiar "Do Commit after row insert" a 1**
   - Hace commit después de cada fila
   - Muestra errores inmediatamente

3. **Marcar "Ignore duplicate rows errors"**

4. **Marcar "Skip bind values during insert"**

### Opción 3: Usar Script Python (RECOMENDADO)

Si DBeaver sigue fallando, usa el script Python:

```powershell
cd backend
py scripts/python/importar_clientes_csv.py ruta/al/archivo.csv
```

**Ventajas:**
- ✅ Maneja errores mejor
- ✅ Muestra qué filas fallan
- ✅ Convierte fechas automáticamente (DD/MM/YYYY → YYYY-MM-DD)
- ✅ Aplica valores por defecto automáticamente
- ✅ Continúa importando aunque algunas filas fallen
- ✅ No requiere mapeo manual

## 📝 Proceso Recomendado

### Si usas DBeaver:

1. **Limpiar la tabla:**
```sql
DELETE FROM clientes_temp;
```

2. **Verificar CSV:**
   - Encabezados correctos
   - Formato UTF-8
   - Primera fila: encabezados

3. **Ajustar configuración** (ver Opción 2)

4. **Reintentar importación**

5. **Verificar resultado:**
```sql
SELECT COUNT(*) FROM clientes_temp;
```

### Si usas Script Python:

1. **Ejecutar script:**
```powershell
cd backend
py scripts/python/importar_clientes_csv.py ruta/al/archivo.csv
```

2. **El script:**
   - Crea backups automáticamente
   - Elimina datos existentes
   - Importa desde CSV
   - Aplica valores por defecto
   - Convierte fechas
   - Normaliza formatos
   - Muestra progreso

3. **Verificar resultado:**
```sql
SELECT COUNT(*) FROM clientes;
```

## 🎯 Recomendación Final

**Usa el script Python** (`importar_clientes_csv.py`):
- ✅ Más confiable
- ✅ Maneja todos los casos automáticamente
- ✅ No requiere configuración manual
- ✅ Muestra errores claros

## 📋 Después de Importar

Una vez que tengas datos en `clientes_temp`:

1. **Aplicar correcciones** (si usaste DBeaver):
```sql
-- Ejecutar: scripts/sql/corregir_fechas_clientes_temp.sql
```

2. **Insertar en tabla clientes:**
```sql
-- Continuar con PASO 8 del script principal
-- O ejecutar: scripts/sql/importar_clientes_desde_csv_dbeaver.sql (desde PASO 8)
```

3. **Verificar resultado final:**
```sql
SELECT COUNT(*) FROM clientes;
```

