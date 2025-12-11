# 🚀 Instrucciones: Ejecutar Script Python de Importación

## 📋 Pasos Rápidos

### 1. Abrir Terminal/PowerShell

Abre PowerShell o CMD en tu sistema.

### 2. Navegar al directorio backend

```powershell
cd C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend
```

### 3. Ejecutar el script

```powershell
py scripts/python/importar_clientes_csv.py "ruta/completa/a/tu/archivo.csv"
```

**Ejemplo con ruta completa:**
```powershell
py scripts/python/importar_clientes_csv.py "C:\Users\PORTATIL\Documents\BD.clientes.csv"
```

**O si el CSV está en la carpeta del proyecto:**
```powershell
py scripts/python/importar_clientes_csv.py "..\scripts\data\clientes.csv"
```

### 4. Confirmar importación

El script te preguntará:
```
¿Importar X clientes? Esto reemplazará todos los datos actuales. (s/n):
```

Escribe `s` y presiona Enter.

### 5. Esperar a que termine

El script mostrará:
- ✅ Progreso cada 100 registros
- ✅ Errores si los hay
- ✅ Resumen final

## ✅ Lo Que Hace el Script

1. **Lee el CSV** (convierte fechas DD/MM/YYYY automáticamente)
2. **Crea backups** automáticamente
3. **Elimina datos existentes** (respetando Foreign Keys)
4. **Importa y normaliza** cada registro:
   - ✅ Cédula: V/J/E + 7-10 números
   - ✅ Nombres: Mayúsculas
   - ✅ Teléfono: +53 + 10 números
   - ✅ Email: Minúsculas + validación
   - ✅ Fechas: DD/MM/YYYY → YYYY-MM-DD
   - ✅ Valores por defecto en campos vacíos
5. **Muestra resultados** al final

## 📊 Verificar Resultado

Después de que termine, verifica:

```sql
SELECT COUNT(*) FROM clientes;
```

## ⚠️ Importante

- El script **reemplaza TODOS** los datos de `clientes`
- Crea **backups automáticamente** antes de eliminar
- Elimina **préstamos relacionados** (3,730 según viste antes)

## 🔄 Si Necesitas Revertir

```sql
-- Restaurar desde backup
DELETE FROM clientes;
INSERT INTO clientes 
SELECT * FROM clientes_backup_antes_importacion;
```

## 🎯 Listo para Ejecutar

**Solo necesitas:**
1. Tener el CSV preparado
2. Ejecutar el comando
3. Confirmar con `s`
4. Esperar

**¡El script hace todo automáticamente!** 🚀

