# 🚀 INSTRUCCIONES EJECUCIÓN MIGRACIÓN 016 POR PLATAFORMA

**Status**: Migración lista para ejecutar  
**Archivo**: `backend/scripts/016_crear_tabla_cuota_pagos.sql`  
**Duración**: 2-5 minutos

---

## 🌐 OPCIÓN 1: RENDER (Producción - Recomendado)

### Paso 1: Conectarse a la BD de Render

```bash
# Obtener la URL de conexión de Render
# Dashboard → pagos → Environment → DATABASE_URL
# Ejemplo: postgresql://user:pass@host:5432/dbname

# Conectarse
psql postgresql://user:pass@host:5432/dbname
```

### Paso 2: Ejecutar migración

```sql
-- Copiar TODO el contenido de backend/scripts/016_crear_tabla_cuota_pagos.sql
-- y pegarlo en la consola psql
```

**O desde terminal**:

```bash
psql postgresql://user:pass@host:5432/dbname < backend/scripts/016_crear_tabla_cuota_pagos.sql
```

### Paso 3: Verificar

```bash
psql postgresql://user:pass@host:5432/dbname -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'cuota_pagos'"

# Debería retornar: 1
```

---

## 🖥️ OPCIÓN 2: PGADMIN (UI Web - Más fácil)

### Paso 1: Abrir pgAdmin

```
https://pgadmin.rapicredit.onrender.com
(o la URL configurada)
```

### Paso 2: Conectarse a la BD

1. **Servers** → Seleccionar servidor BD
2. **Databases** → Seleccionar base de datos
3. **Tools** → **Query Tool**

### Paso 3: Copiar migración

Copiar TODO de `backend/scripts/016_crear_tabla_cuota_pagos.sql` y pegarlo en Query Tool

### Paso 4: Ejecutar

**Click en botón ▶️ Execute** (o `F5`)

**Resultado esperado**:
```
NOTICE: table "cuota_pagos" already exists, skipping
INSERT 0 123
```

---

## 💻 OPCIÓN 3: DBEAVER (Desktop - Para desarrollo)

### Paso 1: Crear conexión

1. **Database** → **New Database Connection**
2. Seleccionar **PostgreSQL**
3. Ingresar credenciales (desde `.env` o Render)

### Paso 2: Abrir SQL Script

1. **File** → **New** → **SQL Script**
2. Copiar `016_crear_tabla_cuota_pagos.sql`
3. Pegarlo

### Paso 3: Ejecutar

**Click en ▶️ Execute Statement** (o `Ctrl+Enter`)

---

## 🐳 OPCIÓN 4: DOCKER LOCAL (Desarrollo)

Si tienes Docker corriendo:

```bash
# Ver contenedor BD
docker ps | grep postgres

# Ejecutar SQL
docker exec -i postgres_container psql -U postgres -d pagos_db < backend/scripts/016_crear_tabla_cuota_pagos.sql
```

---

## ✅ VERIFICACIÓN RÁPIDA (Después de ejecutar)

Ejecutar ESTO en cualquier cliente SQL:

```sql
-- Test 1: ¿Existe tabla?
SELECT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'cuota_pagos'
) as tabla_existe;
-- Resultado esperado: true

-- Test 2: ¿Cuántos registros?
SELECT COUNT(*) as registros_migrados FROM public.cuota_pagos;
-- Resultado esperado: > 0 (si había cuotas con pago_id)

-- Test 3: ¿Índices?
SELECT COUNT(*) as total_indices FROM pg_indexes 
WHERE schemaname = 'public' AND tablename = 'cuota_pagos';
-- Resultado esperado: 4

-- Test 4: ¿FK funciona?
SELECT COUNT(*) FROM information_schema.table_constraints 
WHERE table_name = 'cuota_pagos' AND constraint_type = 'FOREIGN KEY';
-- Resultado esperado: 2
```

**Si todos retornan lo esperado = ✅ ÉXITO**

---

## 🛑 SI FALLA

### Error: "permission denied"
```
Causa: Usuario sin permisos
Solución: Conectarse como superuser (postgres)
```

### Error: "table already exists"
```
Causa: Ya fue creada antes
Solución: Normal, ignorar. El SQL tiene IF NOT EXISTS
```

### Error: "foreign key constraint fails"
```
Causa: Hay cuotas o pagos inválidos
Solución: Ver SQL_MIGRACION_016_VERIFICACION.md → Errores
```

---

## 📋 CHECKLIST

- [ ] Accedí a cliente SQL (psql, pgAdmin o DBeaver)
- [ ] Copié `016_crear_tabla_cuota_pagos.sql`
- [ ] Ejecuté (sin errores esperados)
- [ ] Verificué que tabla existe
- [ ] Verificué que se migraron registros
- [ ] Verificué que índices existen
- [ ] Backend levanta sin errores

---

## 🎯 PRÓXIMO PASO

Una vez que la migración está hecha:

1. **Redeploy de Render** (para que incluya modelo `CuotaPago`)
2. **Test manual**: Crear pago → verificar que aparece en `cuota_pagos`
3. **Listo para producción**

---

**¿Ejecutaste ya? Cuál plataforma usas? Dime cómo te fue 🚀**
