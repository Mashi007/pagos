# 📋 Pasos para Importar CSV en DBeaver

## ✅ Verificación: Tabla Existe pero Está Vacía

Tu tabla `clientes_temp` existe pero tiene 0 registros. Esto significa que la importación no funcionó.

## 🔍 Diagnóstico

### Paso 1: Probar Inserción Manual

Ejecuta este script para verificar que la tabla funciona:

```sql
-- Ejecutar: scripts/sql/probar_insercion_manual.sql
```

O ejecuta directamente:

```sql
INSERT INTO clientes_temp (
    cedula, nombres, telefono, email, direccion,
    fecha_nacimiento, ocupacion, estado, activo,
    fecha_registro, fecha_actualizacion, usuario_registro, notas
) VALUES (
    'V12345678', 'JUAN PEREZ', '+53555123456', 'test@email.com', 'Venezuela',
    '1990-01-01', 'Ingeniero', 'ACTIVO', true,
    '2025-01-27', '2025-01-27', 'SISTEMA', 'nn'
);

SELECT COUNT(*) FROM clientes_temp; -- Debe ser 1
```

**Si esto funciona:** El problema está en el CSV o en el mapeo de DBeaver.

**Si esto falla:** Hay un problema con la tabla. Comparte el error.

## 🔧 Soluciones

### Solución 1: Verificar CSV y Mapeo

**Problemas comunes:**

1. **Encabezados no coinciden:**
   - El CSV debe tener: `cedula, nombres, telefono, email, direccion, fecha_nacimiento, ocupacion, estado, activo, fecha_registro, fecha_actualizacion, usuario_registro, notas`
   - Deben coincidir EXACTAMENTE (sin espacios, sin diferencias de mayúsculas)

2. **Formato del CSV:**
   - Debe ser CSV UTF-8
   - Delimitador: coma (`,`)
   - Primera fila: encabezados
   - Segunda fila en adelante: datos

3. **Mapeo en DBeaver:**
   - Verificar que cada columna del CSV esté mapeada
   - Verificar que los nombres coincidan exactamente

### Solución 2: Cambiar Configuración de Importación

**En DBeaver, antes de importar:**

1. **Desmarcar "Use multi-row value insert"**
   - Esto importa fila por fila
   - Muestra errores específicos de cada fila

2. **Cambiar "Do Commit after row insert" a 1**
   - Hace commit después de cada fila
   - Muestra errores inmediatamente

3. **Marcar "Ignore duplicate rows errors"**

4. **Marcar "Skip bind values during insert"**

### Solución 3: Usar Script Python (Recomendado si DBeaver sigue fallando)

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

## 📝 Checklist Antes de Reintentar

- [ ] Tabla `clientes_temp` existe (✅ Ya verificaste)
- [ ] CSV tiene encabezados en la primera fila
- [ ] Encabezados coinciden exactamente con nombres de columnas
- [ ] CSV guardado como UTF-8
- [ ] Delimitador es coma (`,`)
- [ ] Configuración de importación ajustada
- [ ] Probar inserción manual funciona

## 🎯 Próximos Pasos

1. **Ejecutar inserción manual** (Paso 1 arriba)
2. **Si funciona:** Revisar CSV y mapeo
3. **Si no funciona:** Compartir el error
4. **Si DBeaver sigue fallando:** Usar script Python

