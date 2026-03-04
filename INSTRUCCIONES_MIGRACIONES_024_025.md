# 🚀 INSTRUCCIONES - EJECUTAR MIGRACIONES SQL (024 Y 025)

## 📋 RESUMEN

Necesitas ejecutar **2 migraciones SQL** para activar la carga masiva completa:

```
024: clientes_con_errores     ← Para carga de clientes
025: prestamos_con_errores    ← Para carga de préstamos
```

---

## 🔧 OPCIÓN A: DBeaver (Recomendado)

### Paso 1: Conectar a BD

1. Abre **DBeaver**
2. Click en tu conexión a BD Render (postgres)
3. Abre **SQL Editor** (Ctrl+Alt+E o botón SQL)

### Paso 2: Ejecutar Migración 024

En SQL Editor, pega:

```sql
-- Migración 024: Crear tabla clientes_con_errores

CREATE TABLE IF NOT EXISTS public.clientes_con_errores (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(20),
    nombres VARCHAR(100),
    telefono VARCHAR(100),
    email VARCHAR(100),
    direccion TEXT,
    fecha_nacimiento VARCHAR(50),
    ocupacion VARCHAR(100),
    estado VARCHAR(30) DEFAULT 'PENDIENTE',
    errores_descripcion TEXT,
    observaciones TEXT,
    fila_origen INTEGER,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_registro VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_clientes_con_errores_cedula 
    ON public.clientes_con_errores(cedula);
CREATE INDEX IF NOT EXISTS idx_clientes_con_errores_email 
    ON public.clientes_con_errores(email);
CREATE INDEX IF NOT EXISTS idx_clientes_con_errores_estado 
    ON public.clientes_con_errores(estado);
CREATE INDEX IF NOT EXISTS idx_clientes_con_errores_fecha 
    ON public.clientes_con_errores(fecha_registro DESC);

SELECT COUNT(*) as tabla_024 FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'clientes_con_errores';
```

**Esperado:** Output muestra `tabla_024 | 1`

### Paso 3: Ejecutar Migración 025

En SQL Editor, pega:

```sql
-- Migración 025: Crear tabla prestamos_con_errores

CREATE TABLE IF NOT EXISTS public.prestamos_con_errores (
    id SERIAL PRIMARY KEY,
    cedula_cliente VARCHAR(20),
    total_financiamiento NUMERIC(14, 2),
    modalidad_pago VARCHAR(50),
    numero_cuotas INTEGER,
    producto VARCHAR(255),
    analista VARCHAR(255),
    concesionario VARCHAR(255),
    estado VARCHAR(30) DEFAULT 'PENDIENTE',
    errores_descripcion TEXT,
    observaciones TEXT,
    fila_origen INTEGER,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_registro VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_prestamos_con_errores_cedula 
    ON public.prestamos_con_errores(cedula_cliente);
CREATE INDEX IF NOT EXISTS idx_prestamos_con_errores_estado 
    ON public.prestamos_con_errores(estado);
CREATE INDEX IF NOT EXISTS idx_prestamos_con_errores_fecha 
    ON public.prestamos_con_errores(fecha_registro DESC);

SELECT COUNT(*) as tabla_025 FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'prestamos_con_errores';
```

**Esperado:** Output muestra `tabla_025 | 1`

---

## 🔧 OPCIÓN B: psql (Terminal)

### Paso 1: Conectar

```bash
psql -h db-hostname -U dbuser -d dbname
```

O si tienes URL:

```bash
psql postgresql://user:password@host:port/dbname
```

### Paso 2-3: Copiar/Pegar SQL

En terminal psql, pega las queries de arriba (mismo contenido).

---

## 🔧 OPCIÓN C: Render SQL Editor

1. Ve a dashboard Render
2. Selecciona BD PostgreSQL
3. Abre **Query Editor**
4. Pega SQL y ejecuta

---

## ✅ VERIFICACIÓN FINAL

Para confirmar que ambas tablas existen:

```sql
-- Verificar tablas creadas
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('clientes_con_errores', 'prestamos_con_errores')
ORDER BY table_name;

-- Esperado output:
-- table_name
-- clientes_con_errores
-- prestamos_con_errores
```

---

## 🎯 DESPUÉS DE EJECUTAR

### 1. Deploy Backend
- Ya está en main
- Render auto-deployará cuando detecte cambios
- O manualmente en dashboard

### 2. Deploy Frontend
- Build: `npm run build` (en carpeta frontend)
- Deploy a Render/Vercel

### 3. Verificar en Producción

**Clientes:**
```
URL: https://rapicredit.onrender.com/pagos/clientes
• Click "Nuevo Cliente" → "Cargar desde Excel"
• Probar con archivo de test
```

**Préstamos:**
```
URL: https://rapicredit.onrender.com/pagos/prestamos
• Click "Nuevo Préstamo" → "Cargar desde Excel"
• Probar con archivo de test
```

---

## 🚨 TROUBLESHOOTING

### Error: "Table already exists"

```
Esto está OK - usa CREATE TABLE IF NOT EXISTS
(la query incluye IF NOT EXISTS)
```

### Error: "Index already exists"

```
Esto está OK - usa CREATE INDEX IF NOT EXISTS
(la query incluye IF NOT EXISTS)
```

### Error: "Connection refused"

```
Verificar:
1. URL de BD correcta
2. Credenciales correctas
3. Firewall permite conexión
4. BD está online (Render dashboard)
```

### Error: "Permission denied"

```
Necesitas usuario con permisos de DDL
(CREATE TABLE, CREATE INDEX)
Generalmente el usuario principal de BD tiene estos permisos
```

---

## ✅ CHECKLIST

```
[ ] Migración 024 ejecutada (clientes_con_errores creada)
[ ] Migración 025 ejecutada (prestamos_con_errores creada)
[ ] Ambas tablas verificadas en BD
[ ] Backend deployado
[ ] Frontend deployado
[ ] Página /pagos/clientes accesible
[ ] Página /pagos/prestamos accesible
[ ] Botones "Nuevo Cliente" y "Nuevo Préstamo" con dropdown
[ ] Upload Excel funciona en ambas páginas
[ ] Tab "Con errores" muestra tabla
```

---

**¡Listo para activación!** 🚀

