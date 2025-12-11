# 🐍 Guía: Usar Script Python para Importar Clientes

## ✅ Script Actualizado

El script Python ahora aplica **TODOS** los formatos y valores por defecto especificados:

### Formatos Aplicados:
- ✅ **Cédula**: V/J/E + 7-10 números (sin guiones)
- ✅ **Nombres**: Todas mayúsculas
- ✅ **Teléfono**: +53 + quitar 0 + exactamente 10 números
- ✅ **Email**: Minúsculas + validación formato internacional
- ✅ **Fechas**: Convierte DD/MM/YYYY a YYYY-MM-DD automáticamente

### Valores por Defecto:
- ✅ Cédula vacía → `Z999999999`
- ✅ Nombres vacío → `Nombre Apellido`
- ✅ Teléfono vacío → `+539999999999`
- ✅ Email vacío → `no-email@rapicredit.com`
- ✅ Dirección vacía → `Venezuela`
- ✅ Fecha nacimiento vacía → `2020-01-01`
- ✅ Ocupación vacía → `Sin ocupacion`
- ✅ Estado vacío → `ACTIVO`
- ✅ Fecha registro vacía → `2025-10-01`
- ✅ Fecha actualización vacía → `2025-12-10`
- ✅ Notas vacía → `nn`

## 🚀 Cómo Usar

### Paso 1: Navegar al directorio backend

```powershell
cd backend
```

### Paso 2: Ejecutar el script

```powershell
py scripts/python/importar_clientes_csv.py ruta/completa/al/archivo.csv
```

**Ejemplo:**
```powershell
py scripts/python/importar_clientes_csv.py C:\Users\PORTATIL\Documents\BD.clientes.csv
```

### Paso 3: Confirmar importación

El script te preguntará:
```
¿Importar X clientes? Esto reemplazará todos los datos actuales. (s/n):
```

Escribe `s` y presiona Enter para continuar.

## 📋 Lo Que Hace el Script

1. **Lee el CSV** y muestra cuántos registros encontró
2. **Crea backups** automáticamente:
   - `clientes_backup_antes_importacion`
   - `prestamos_backup_antes_importacion`
3. **Elimina datos existentes** (respetando Foreign Keys)
4. **Importa y normaliza** cada registro:
   - Aplica formatos
   - Convierte fechas
   - Aplica valores por defecto
5. **Muestra progreso** cada 100 registros
6. **Verifica resultados** al final
7. **Compara bases** (antes vs después)

## ✅ Ventajas del Script Python

- ✅ **No requiere privilegios especiales** (no usa COPY)
- ✅ **Maneja errores mejor** (muestra qué filas fallan)
- ✅ **Convierte fechas automáticamente** (DD/MM/YYYY → YYYY-MM-DD)
- ✅ **Aplica valores por defecto** automáticamente
- ✅ **Normaliza formatos** (cédula, teléfono, email, nombres)
- ✅ **Continúa importando** aunque algunas filas fallen
- ✅ **Muestra progreso** en tiempo real
- ✅ **Crea backups** automáticamente

## 📊 Ejemplo de Salida

```
============================================================
📥 IMPORTACIÓN DE CLIENTES DESDE CSV
============================================================

Archivo: C:\Users\PORTATIL\Documents\BD.clientes.csv

✅ Leídos 3708 registros del CSV
¿Importar 3708 clientes? Esto reemplazará todos los datos actuales. (s/n): s

📦 Creando backups...
✅ Backups creados

🗑️  Eliminando datos existentes...
   Eliminados 3730 préstamos
   Eliminados 0 registros de tickets
   Eliminados 0 registros de notificaciones
   Eliminados 3708 clientes
✅ Datos existentes eliminados

📥 Importando 3708 clientes...
   Procesados 100/3708 registros...
   Procesados 200/3708 registros...
   ...
✅ Importados 3708 clientes

🔍 Verificando importación...
   Total de clientes: 3708
   Cédulas sin guiones: 3708
   Emails normalizados: 3708
   Estados válidos: 3708

📊 Comparando bases...
   Base anterior: 3708 clientes
   Base nueva: 3708 clientes
   Diferencia: 0 clientes

============================================================
✅ IMPORTACIÓN COMPLETA
============================================================
   Importados: 3708 clientes
```

## ⚠️ Notas Importantes

1. **El script reemplaza TODOS los datos** de `clientes`
2. **Crea backups automáticamente** antes de eliminar
3. **Elimina préstamos relacionados** (3,730 según viste antes)
4. **Si hay errores**, los muestra pero continúa con las filas válidas

## 🔄 Si Necesitas Revertir

```sql
-- Restaurar desde backup
DELETE FROM clientes;
INSERT INTO clientes 
SELECT * FROM clientes_backup_antes_importacion;

-- Restaurar préstamos
DELETE FROM prestamos;
INSERT INTO prestamos 
SELECT * FROM prestamos_backup_antes_importacion;
```

## 🎯 Listo para Usar

El script está actualizado y listo. Solo necesitas:

1. Tener el CSV preparado
2. Ejecutar el comando
3. Confirmar con `s`
4. Esperar a que termine

**¡El script hace todo automáticamente!** 🚀

