# 🔧 Solución: Error de Permisos al Importar CSV

**Error:** `permission denied to COPY from a file`

---

## ❌ Problema

PostgreSQL requiere privilegios especiales (`pg_read_server_files`) para usar `COPY FROM file`, que normalmente no están disponibles en DBeaver.

---

## ✅ Soluciones Disponibles

### Opción 1: Usar Script Python (RECOMENDADO)

**Archivo:** `scripts/python/importar_clientes_csv.py`

**Ventajas:**
- ✅ No requiere privilegios especiales
- ✅ Funciona en cualquier entorno
- ✅ Incluye validación y normalización
- ✅ Muestra progreso y errores

**Uso:**
```powershell
cd backend
py scripts/python/importar_clientes_csv.py ruta/al/archivo/clientes.csv
```

**Características:**
- Crea backups automáticamente
- Elimina datos existentes respetando Foreign Keys
- Normaliza datos (cédula, email, estado)
- Muestra comparación antes/después
- Maneja errores de forma segura

---

### Opción 2: Usar Herramienta de Importación de DBeaver

**Pasos:**

1. **Crear tabla temporal:**
```sql
DROP TABLE IF EXISTS clientes_temp;
CREATE TABLE clientes_temp (
    id INTEGER,
    cedula VARCHAR(20),
    nombres VARCHAR(100),
    telefono VARCHAR(15),
    email VARCHAR(100),
    direccion TEXT,
    fecha_nacimiento DATE,
    ocupacion VARCHAR(100),
    estado VARCHAR(20),
    activo BOOLEAN,
    fecha_registro TIMESTAMP,
    fecha_actualizacion TIMESTAMP,
    usuario_registro VARCHAR(100),
    notas TEXT
);
```

2. **Importar CSV en DBeaver:**
   - Click derecho en `clientes_temp` → **Import Data**
   - Seleccionar archivo CSV
   - Configurar mapeo de columnas
   - Ejecutar importación

3. **Usar script SQL** `importar_clientes_desde_csv_dbeaver.sql` para procesar los datos

---

### Opción 3: Usar Script SQL con INSERT Manual

**Archivo:** `scripts/sql/importar_clientes_desde_csv_dbeaver.sql`

Este script:
- ✅ No usa COPY (evita problema de permisos)
- ✅ Usa INSERT directo
- ✅ Puedes cargar datos manualmente o usar herramienta de DBeaver

**Pasos:**

1. Ejecutar PASO 1-4 del script (backups y eliminación)
2. Cargar datos en `clientes_temp` usando herramienta de DBeaver
3. Continuar con PASO 7-9 (validación e inserción)

---

## 📊 Comparar Bases (Si hay Problemas)

**Archivo:** `scripts/sql/comparar_bases_clientes.sql`

Este script te permite:
- ✅ Comparar totales antes/después
- ✅ Ver clientes eliminados
- ✅ Ver clientes nuevos
- ✅ Ver clientes modificados
- ✅ Resumen de cambios

**Uso:**
```sql
-- Ejecutar en DBeaver después de importar
-- Muestra comparación detallada
```

---

## 🔄 Si Necesitas Subir Otro CSV

### Proceso:

1. **Hacer rollback** (si ya ejecutaste el script):
```sql
ROLLBACK;
```

2. **O restaurar desde backup:**
```sql
DELETE FROM clientes;
INSERT INTO clientes 
SELECT * FROM clientes_backup_antes_importacion;
```

3. **Preparar nuevo CSV** con correcciones

4. **Validar nuevo CSV:**
```powershell
py scripts/python/validar_csv_clientes.py nuevo_archivo.csv
```

5. **Importar nuevo CSV** usando una de las opciones arriba

6. **Comparar resultados:**
```sql
-- Ejecutar scripts/sql/comparar_bases_clientes.sql
```

---

## 📁 Archivos Disponibles

- ✅ `scripts/python/importar_clientes_csv.py` - Script Python (RECOMENDADO)
- ✅ `scripts/sql/importar_clientes_desde_csv_dbeaver.sql` - Script SQL para DBeaver
- ✅ `scripts/sql/comparar_bases_clientes.sql` - Comparar bases
- ✅ `scripts/python/validar_csv_clientes.py` - Validar CSV antes de importar

---

## 🎯 Recomendación

**Usa el script Python** (`importar_clientes_csv.py`):
- ✅ Más fácil de usar
- ✅ No requiere privilegios especiales
- ✅ Incluye todas las validaciones
- ✅ Muestra progreso y errores
- ✅ Compara bases automáticamente

---

**¿Necesitas ayuda con alguna opción específica?** Puedo guiarte paso a paso.

