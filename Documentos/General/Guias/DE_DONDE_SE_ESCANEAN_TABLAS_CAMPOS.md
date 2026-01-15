# 🔍 De Dónde se Escanean Tablas/Campos

**Fecha:** 2025-01-14  
**Sistema:** RAPICREDIT - Inteligencia Artificial  
**Endpoint:** `GET /api/v1/configuracion/ai/tablas-campos`

---

## 📊 RESUMEN EJECUTIVO

El sistema escanea **directamente el esquema de PostgreSQL** usando **SQLAlchemy Inspector**, que consulta las **vistas del sistema de información** de PostgreSQL (`information_schema` y `pg_catalog`).

**Fuente:** Esquema real de PostgreSQL (no modelos Python, no archivos de configuración)

---

## 🔧 TECNOLOGÍA UTILIZADA

### SQLAlchemy Inspector
**Biblioteca:** `sqlalchemy.engine.reflection.Inspector`  
**Método:** Reflection (introspección del esquema)

```python
from sqlalchemy.engine import reflection

inspector = reflection.Inspector.from_engine(db.bind)
```

---

## 📍 FUENTE DE DATOS: PostgreSQL System Views

SQLAlchemy Inspector consulta las siguientes vistas del sistema de PostgreSQL:

### 1. **Obtener Lista de Tablas**
```sql
-- Inspector ejecuta internamente:
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
```

**Vista consultada:** `information_schema.tables`  
**Esquema:** `public` (esquema por defecto)

---

### 2. **Obtener Columnas de una Tabla**
```sql
-- Inspector ejecuta internamente:
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length,
    numeric_precision,
    numeric_scale
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'nombre_tabla'
ORDER BY ordinal_position
```

**Vista consultada:** `information_schema.columns`  
**Información obtenida:**
- Nombre de columna
- Tipo de dato (VARCHAR, INTEGER, DATE, etc.)
- Si es nullable (NULL/NOT NULL)
- Valor por defecto
- Longitud máxima (para VARCHAR)
- Precisión y escala (para NUMERIC)

---

### 3. **Obtener Índices**
```sql
-- Inspector ejecuta internamente:
SELECT 
    i.indexname,
    i.indexdef,
    a.attname as column_name,
    i.indexdef LIKE '%UNIQUE%' as is_unique
FROM pg_indexes i
JOIN pg_class c ON c.relname = i.indexname
JOIN pg_index idx ON idx.indexrelid = c.oid
JOIN pg_attribute a ON a.attrelid = idx.indrelid 
    AND a.attnum = ANY(idx.indkey)
WHERE i.schemaname = 'public' 
  AND i.tablename = 'nombre_tabla'
```

**Vistas consultadas:** `pg_indexes`, `pg_class`, `pg_index`, `pg_attribute`  
**Información obtenida:**
- Nombre del índice
- Columnas indexadas
- Si es UNIQUE
- Tipo de índice (B-tree, GIN, etc.)

---

### 4. **Obtener Claves Foráneas**
```sql
-- Inspector ejecuta internamente:
SELECT
    tc.constraint_name,
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
  AND tc.table_schema = 'public'
  AND tc.table_name = 'nombre_tabla'
```

**Vistas consultadas:** 
- `information_schema.table_constraints`
- `information_schema.key_column_usage`
- `information_schema.constraint_column_usage`

**Información obtenida:**
- Campo que es FK
- Tabla referenciada
- Campo referenciado

---

## 🔄 PROCESO DE ESCANEO

### Endpoint: `GET /api/v1/configuracion/ai/tablas-campos`

```python
# 1. Crear Inspector desde la conexión de BD
inspector = reflection.Inspector.from_engine(db.bind)

# 2. Obtener TODAS las tablas del esquema 'public'
todas_tablas = inspector.get_table_names()
# Ejecuta: SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'

# 3. Para cada tabla, obtener información detallada
for tabla in todas_tablas:
    # 3.1. Obtener columnas
    columnas = inspector.get_columns(tabla)
    # Ejecuta: SELECT * FROM information_schema.columns WHERE table_name = tabla
    
    # 3.2. Obtener índices
    indices = inspector.get_indexes(tabla)
    # Ejecuta: SELECT * FROM pg_indexes WHERE tablename = tabla
    
    # 3.3. Obtener claves foráneas
    fks = inspector.get_foreign_keys(tabla)
    # Ejecuta: SELECT * FROM information_schema.table_constraints WHERE constraint_type = 'FOREIGN KEY'
```

---

## 📋 TABLAS ESCANEADAS

### Todas las tablas del esquema `public`:

El sistema escanea **TODAS las tablas** que existen en el esquema `public` de PostgreSQL, incluyendo:

**Tablas del Sistema:**
- `clientes`
- `prestamos`
- `cuotas`
- `pagos`
- `users`
- `configuracion_sistema`
- `notificaciones`
- `tickets`
- `auditoria`
- `conversaciones_ai`
- `fine_tuning_jobs`
- `documentos_ai`
- `documento_ai_embeddings`
- `ai_diccionario_semantico`
- `ai_definiciones_campos`
- `ai_calificaciones_chat`
- `modelos_riesgo`
- `modelos_impago_cuotas`
- Y todas las demás tablas que existan en la BD

---

## 🔍 INFORMACIÓN OBTENIDA POR CAMPO

Para cada campo, el sistema obtiene:

1. **Nombre del campo** (`column_name`)
2. **Tipo de dato** (`data_type`): VARCHAR, INTEGER, DATE, NUMERIC, BOOLEAN, etc.
3. **Nullable** (`is_nullable`): Si permite NULL o es NOT NULL
4. **Primary Key** (`primary_key`): Si es clave primaria
5. **Tiene Índice** (`tiene_indice`): Si tiene índice creado
6. **Es Clave Foránea** (`es_clave_foranea`): Si referencia otra tabla
7. **Tabla Referenciada** (`tabla_referenciada`): Nombre de la tabla FK
8. **Campo Referenciado** (`campo_referenciado`): Nombre del campo FK

---

## ⚡ ACTUALIZACIÓN AUTOMÁTICA

### ¿Cuándo se actualiza?

El escaneo se realiza **en tiempo real** cada vez que:
1. Se llama al endpoint `GET /api/v1/configuracion/ai/tablas-campos`
2. Se ejecuta la sincronización `POST /api/v1/configuracion/ai/definiciones-campos/sincronizar`

### ¿Qué pasa si agregas/eliminas campos?

✅ **Detección automática:**
- Si agregas un campo nuevo → Aparece en el siguiente escaneo
- Si eliminas un campo → Desaparece del escaneo
- Si cambias el tipo de dato → Se actualiza automáticamente
- Si agregas un índice → Se detecta automáticamente
- Si agregas una FK → Se detecta automáticamente

**No requiere:**
- ❌ Reiniciar el servidor
- ❌ Actualizar archivos de configuración
- ❌ Modificar código
- ❌ Ejecutar scripts manuales

---

## 🔗 CONEXIÓN A BASE DE DATOS

### Conexión utilizada:

```python
# La sesión de BD viene de:
db: Session = Depends(get_db)

# Que obtiene la conexión desde:
from app.db.session import SessionLocal

# Que usa la configuración de:
DATABASE_URL = "postgresql://usuario:password@host:puerto/nombre_bd"
```

**Motor:** PostgreSQL  
**Driver:** `psycopg2` o `asyncpg`  
**ORM:** SQLAlchemy

---

## 📊 EJEMPLO DE RESPUESTA

```json
{
  "tablas_campos": {
    "clientes": [
      {
        "nombre": "id",
        "tipo": "INTEGER",
        "nullable": false,
        "es_obligatorio": true,
        "es_primary_key": true,
        "tiene_indice": true,
        "es_clave_foranea": false
      },
      {
        "nombre": "cedula",
        "tipo": "VARCHAR(20)",
        "nullable": false,
        "es_obligatorio": true,
        "es_primary_key": false,
        "tiene_indice": true,
        "es_clave_foranea": false
      },
      {
        "nombre": "nombres",
        "tipo": "VARCHAR(255)",
        "nullable": false,
        "es_obligatorio": true,
        "es_primary_key": false,
        "tiene_indice": false,
        "es_clave_foranea": false
      }
    ],
    "prestamos": [
      {
        "nombre": "id",
        "tipo": "INTEGER",
        "nullable": false,
        "es_obligatorio": true,
        "es_primary_key": true,
        "tiene_indice": true,
        "es_clave_foranea": false
      },
      {
        "nombre": "cliente_id",
        "tipo": "INTEGER",
        "nullable": false,
        "es_obligatorio": true,
        "es_primary_key": false,
        "tiene_indice": true,
        "es_clave_foranea": true,
        "tabla_referenciada": "clientes",
        "campo_referenciado": "id"
      }
    ]
  },
  "total_tablas": 25,
  "fecha_consulta": "2025-01-14T15:30:00"
}
```

---

## ✅ CONCLUSIÓN

### Fuente de Escaneo:

1. **Base de Datos:** PostgreSQL
2. **Esquema:** `public`
3. **Método:** SQLAlchemy Inspector
4. **Vistas Consultadas:**
   - `information_schema.tables` → Lista de tablas
   - `information_schema.columns` → Columnas y tipos
   - `pg_indexes` → Índices
   - `information_schema.table_constraints` → Claves foráneas

### Características:

- ✅ **Escaneo en tiempo real** del esquema de PostgreSQL
- ✅ **Detección automática** de cambios en la estructura
- ✅ **Información completa** de cada campo (tipo, nullable, índices, FKs)
- ✅ **Sin configuración manual** requerida
- ✅ **Actualización automática** al cambiar la estructura de BD

---

**Última actualización:** 2025-01-14  
**Tecnología:** SQLAlchemy Inspector + PostgreSQL System Views  
**Fuente:** Esquema real de PostgreSQL (`information_schema` y `pg_catalog`)
