# 📋 Guía para Actualizar la Base de Datos Reemplazando Datos

**Fecha:** 2025-01-27  
**Objetivo:** Guía completa para actualizar/reemplazar datos en la base de datos PostgreSQL

---

## ⚠️ IMPORTANTE: HACER BACKUP PRIMERO

**ANTES de hacer cualquier cambio, crear un backup completo de la base de datos:**

### Opción 1: Usando pg_dump (Recomendado)

```powershell
# En PowerShell, desde el directorio del proyecto
pg_dump -h [HOST] -U [USER] -d [DATABASE_NAME] -F c -f backup_$(Get-Date -Format "yyyyMMdd_HHmmss").dump

# Ejemplo:
# pg_dump -h localhost -U postgres -d pagos_db -F c -f backup_20250127_120000.dump
```

### Opción 2: Usando DBeaver

1. Click derecho en la base de datos → **Tools** → **Backup Database**
2. Seleccionar formato: **Custom**
3. Guardar el archivo con nombre descriptivo

---

## 🔄 OPCIONES PARA REEMPLAZAR DATOS

### OPCIÓN 1: Reemplazar Datos Específicos con SQL Directo

**Cuándo usar:** Cuando necesitas reemplazar datos específicos en tablas concretas.

**Pasos:**

1. **Conectarse a la base de datos** (DBeaver, pgAdmin, o psql)

2. **Verificar los datos actuales:**
```sql
-- Ejemplo: Ver datos que se van a reemplazar
SELECT * FROM [TABLA] WHERE [CONDICION];
```

3. **Crear una transacción para poder hacer rollback si algo sale mal:**
```sql
BEGIN;

-- Reemplazar datos
UPDATE [TABLA] 
SET [COLUMNA] = '[NUEVO_VALOR]'
WHERE [CONDICION];

-- Verificar los cambios
SELECT * FROM [TABLA] WHERE [CONDICION];

-- Si todo está bien:
COMMIT;

-- Si algo salió mal:
-- ROLLBACK;
```

**Ejemplo práctico:**
```sql
BEGIN;

-- Reemplazar todos los concesionarios "NO DEFINIDO" por un valor específico
UPDATE prestamos 
SET concesionario = 'SIN ASIGNAR'
WHERE concesionario = 'NO DEFINIDO';

-- Verificar
SELECT concesionario, COUNT(*) 
FROM prestamos 
GROUP BY concesionario;

-- Si está bien, hacer commit
COMMIT;
```

---

### OPCIÓN 2: Reemplazar Datos Usando Scripts SQL Existentes

**Cuándo usar:** Cuando necesitas corregir datos inválidos o normalizar datos.

**Scripts disponibles:**

1. **`scripts/sql/02_corregir_datos_invalidos.sql`**
   - Corrige datos inválidos en relaciones (Foreign Keys)
   - Crea registros faltantes en catálogos
   - Limpia datos huérfanos

2. **`scripts/sql/03_corregir_datos_especificos.sql`**
   - Corrige casos específicos encontrados en validaciones
   - Crea clientes temporales para cédulas inválidas
   - Crea concesionarios, analistas y modelos faltantes

**Pasos:**

1. Abrir DBeaver
2. Conectarse a la base de datos
3. Abrir el script SQL correspondiente
4. **Revisar el script** antes de ejecutar
5. Ejecutar el script completo
6. Verificar los cambios

---

### OPCIÓN 3: Reemplazar Datos con Migración de Alembic

**Cuándo usar:** Cuando necesitas reemplazar datos como parte de un cambio de esquema o cuando quieres versionar los cambios.

**Pasos:**

1. **Crear una nueva migración:**
```powershell
cd backend
py -m alembic revision -m "reemplazar_datos_especificos"
```

2. **Editar el archivo de migración generado** en `backend/alembic/versions/`:
```python
def upgrade():
    # Reemplazar datos
    op.execute("""
        UPDATE prestamos 
        SET concesionario = 'SIN ASIGNAR'
        WHERE concesionario = 'NO DEFINIDO';
    """)

def downgrade():
    # Revertir cambios si es necesario
    op.execute("""
        UPDATE prestamos 
        SET concesionario = 'NO DEFINIDO'
        WHERE concesionario = 'SIN ASIGNAR';
    """)
```

3. **Aplicar la migración:**
```powershell
cd backend
py -m alembic upgrade head
```

4. **Verificar los cambios:**
```sql
SELECT concesionario, COUNT(*) 
FROM prestamos 
GROUP BY concesionario;
```

---

### OPCIÓN 4: Reemplazar Datos con Script Python

**Cuándo usar:** Cuando necesitas lógica compleja o procesamiento de datos antes de reemplazar.

**Pasos:**

1. **Crear un script Python** en `backend/scripts/`:
```python
# backend/scripts/reemplazar_datos.py
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from sqlalchemy import text

def reemplazar_datos():
    db = SessionLocal()
    try:
        # Reemplazar datos
        db.execute(text("""
            UPDATE prestamos 
            SET concesionario = 'SIN ASIGNAR'
            WHERE concesionario = 'NO DEFINIDO';
        """))
        
        db.commit()
        print("✅ Datos reemplazados correctamente")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    reemplazar_datos()
```

2. **Ejecutar el script:**
```powershell
cd backend
py scripts/reemplazar_datos.py
```

---

### OPCIÓN 5: Reemplazar Datos Masivos desde Archivo (CSV/Excel)

**Cuándo usar:** Cuando tienes un archivo con los nuevos datos que quieres importar.

**Pasos:**

1. **Preparar el archivo** (CSV o Excel) con los datos nuevos

2. **Usar el script SQL existente** `scripts/sql/importar_datos_csv.sql` como referencia

3. **O crear un script Python** para importar:
```python
# backend/scripts/importar_y_reemplazar_datos.py
import pandas as pd
from app.db.session import SessionLocal
from sqlalchemy import text

def importar_y_reemplazar():
    # Leer el archivo
    df = pd.read_csv('datos_nuevos.csv')
    
    db = SessionLocal()
    try:
        for _, row in df.iterrows():
            db.execute(text("""
                UPDATE prestamos 
                SET concesionario = :nuevo_valor
                WHERE id = :id
            """), {
                'nuevo_valor': row['concesionario'],
                'id': row['id']
            })
        
        db.commit()
        print("✅ Datos importados y reemplazados correctamente")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()
```

---

## 📝 CHECKLIST ANTES DE REEMPLAZAR DATOS

- [ ] ✅ **Backup creado** de la base de datos
- [ ] ✅ **Datos actuales verificados** (saber qué se va a cambiar)
- [ ] ✅ **Condiciones WHERE revisadas** (asegurarse de que solo se cambian los datos correctos)
- [ ] ✅ **Transacción iniciada** (BEGIN) para poder hacer rollback
- [ ] ✅ **Cambios verificados** antes de hacer COMMIT
- [ ] ✅ **Documentación actualizada** sobre los cambios realizados

---

## 🔍 VERIFICAR CAMBIOS DESPUÉS DE REEMPLAZAR

### Verificar datos reemplazados:
```sql
-- Ver conteo de valores
SELECT concesionario, COUNT(*) 
FROM prestamos 
GROUP BY concesionario;

-- Ver registros específicos
SELECT * FROM prestamos 
WHERE concesionario = 'SIN ASIGNAR'
LIMIT 10;
```

### Verificar integridad referencial:
```sql
-- Verificar que no hay datos huérfanos
SELECT COUNT(*) 
FROM prestamos p
LEFT JOIN concesionarios c ON p.concesionario = c.nombre
WHERE p.concesionario IS NOT NULL 
  AND c.nombre IS NULL;
```

---

## ⚠️ CASOS ESPECIALES

### Reemplazar Datos en Tablas con Foreign Keys

Si estás reemplazando datos que tienen relaciones con otras tablas:

1. **Verificar las relaciones primero:**
```sql
SELECT 
    tc.table_name, 
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name = '[TU_TABLA]';
```

2. **Actualizar en el orden correcto:**
   - Primero actualizar las tablas padre (referenciadas)
   - Luego actualizar las tablas hijas (que referencian)

### Reemplazar Datos en Producción

**⚠️ EXTRA PRECAUCIÓN:**

1. Hacer backup completo
2. Probar en ambiente de desarrollo/staging primero
3. Ejecutar en horario de bajo tráfico
4. Tener plan de rollback listo
5. Monitorear la aplicación después del cambio

---

## 🆘 ROLLBACK (Revertir Cambios)

Si necesitas revertir los cambios:

### Si usaste transacción (BEGIN/COMMIT):
```sql
-- Si aún no hiciste COMMIT:
ROLLBACK;

-- Si ya hiciste COMMIT, necesitas revertir manualmente:
BEGIN;
UPDATE prestamos 
SET concesionario = 'NO DEFINIDO'
WHERE concesionario = 'SIN ASIGNAR';
COMMIT;
```

### Si usaste migración de Alembic:
```powershell
cd backend
py -m alembic downgrade -1  # Revertir última migración
```

### Si usaste backup:
```powershell
# Restaurar desde backup
pg_restore -h [HOST] -U [USER] -d [DATABASE_NAME] -c backup_20250127_120000.dump
```

---

## 📚 RECURSOS ADICIONALES

- **Scripts SQL disponibles:** `scripts/sql/`
- **Migraciones Alembic:** `backend/alembic/versions/`
- **Scripts Python:** `backend/scripts/`
- **Documentación de migraciones:** `Documentos/General/Comandos/EJECUTAR_MIGRACIONES.md`

---

## ❓ ¿QUÉ MÉTODO ELEGIR?

| Método | Cuándo Usar | Ventajas | Desventajas |
|--------|-------------|----------|-------------|
| **SQL Directo** | Cambios simples y rápidos | Rápido, directo | No versionado |
| **Script SQL** | Correcciones estándar | Reutilizable | Requiere DBeaver |
| **Migración Alembic** | Cambios que deben versionarse | Versionado, reversible | Más pasos |
| **Script Python** | Lógica compleja | Flexible, potente | Requiere código |
| **Importar CSV/Excel** | Datos masivos desde archivo | Ideal para importaciones | Requiere preparación |

---

**¿Necesitas ayuda con un caso específico?** Revisa los scripts existentes en `scripts/sql/` o crea una nueva migración siguiendo los ejemplos en `backend/alembic/versions/`.

