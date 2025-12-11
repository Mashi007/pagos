# 🚀 Preparar Importación Final

## ✅ Estado Actual

- ✅ Tabla `clientes_temp` existe y funciona
- ✅ Configuración de DBeaver correcta
- ✅ Mapeo de columnas correcto
- ⚠️ Solo hay 1 registro (el de prueba)

## 🧹 Paso 1: Limpiar Tabla

Antes de importar, elimina el registro de prueba:

```sql
-- Eliminar registro de prueba
DELETE FROM clientes_temp;

-- Verificar que está vacía
SELECT COUNT(*) FROM clientes_temp; -- Debe ser 0
```

O ejecuta el script completo:
```sql
-- Ejecutar: scripts/sql/limpiar_y_preparar_importacion.sql
```

## 📥 Paso 2: Importar CSV en DBeaver

Con la configuración que ya tienes:
- ✅ Mapeo correcto
- ✅ "Use multi-row value insert" desmarcado (fila por fila)
- ✅ "Use transactions" marcado (seguro)

**Procede con la importación.**

## ✅ Paso 3: Verificar Importación

Después de importar:

```sql
-- Verificar cuántos registros se importaron
SELECT COUNT(*) FROM clientes_temp;
```

**Si el COUNT > 0:** ✅ Importación exitosa
**Si el COUNT = 0:** ❌ Revisar errores en DBeaver

## 🔧 Paso 4: Aplicar Correcciones

Si se importaron registros, aplicar correcciones:

```sql
-- Ejecutar: scripts/sql/corregir_fechas_clientes_temp.sql
```

Este script:
- ✅ Convierte fechas de DD/MM/YYYY a YYYY-MM-DD
- ✅ Aplica valores por defecto en campos vacíos
- ✅ Normaliza formatos (cédula, teléfono, email, nombres)

## 📤 Paso 5: Insertar en Tabla Clientes

Después de corregir:

```sql
-- Continuar con PASO 8 del script principal
-- O ejecutar: scripts/sql/importar_clientes_desde_csv_dbeaver.sql (desde PASO 8)
```

## 🎯 Alternativa: Script Python

Si DBeaver sigue fallando, usa el script Python:

```powershell
cd backend
py scripts/python/importar_clientes_csv.py ruta/al/archivo.csv
```

**Ventajas:**
- ✅ Más confiable
- ✅ Maneja errores automáticamente
- ✅ Convierte fechas automáticamente
- ✅ Aplica valores por defecto
- ✅ Muestra progreso

## 📋 Checklist Final

- [ ] Limpiar tabla (eliminar registro de prueba)
- [ ] Verificar que COUNT = 0
- [ ] Importar CSV en DBeaver
- [ ] Verificar COUNT después de importar
- [ ] Aplicar correcciones si es necesario
- [ ] Insertar en tabla clientes

**¡Listo para importar!** 🚀

