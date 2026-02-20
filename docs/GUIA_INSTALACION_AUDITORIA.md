# GUÍA DE INSTALACIÓN - TABLA DE AUDITORÍA

## 📍 Archivo SQL Limpio

```
backend/sql/auditoria_revision_manual_clean.sql
```

**Este archivo NO tiene caracteres especiales, está listo para copiar/pegar.**

---

## 🚀 OPCIÓN 1: Ejecutar desde DBeaver

1. Abre DBeaver
2. Conecta a tu base de datos PostgreSQL
3. Abre pestaña SQL
4. Copia TODO el contenido de `auditoria_revision_manual_clean.sql`
5. Pega en DBeaver
6. Click en **Execute** (Ctrl+Enter)
7. ✅ Listo

---

## 🚀 OPCIÓN 2: Ejecutar desde Terminal

```bash
psql -U postgres -d pagos -f backend/sql/auditoria_revision_manual_clean.sql
```

Reemplaza:
- `postgres` → tu usuario PostgreSQL
- `pagos` → nombre de tu base de datos
- Ruta del archivo si es diferente

---

## 🚀 OPCIÓN 3: Ejecutar línea por línea (para evitar errores)

Si el archivo completo falla, ejecuta en orden:

### Paso 1: Crear tabla
```sql
CREATE TABLE IF NOT EXISTS public.auditoria_revision_manual (
    id SERIAL PRIMARY KEY,
    prestamo_id INTEGER NOT NULL,
    cliente_id INTEGER,
    cuota_id INTEGER,
    tipo_cambio VARCHAR(50) NOT NULL,
    tabla_afectada VARCHAR(50) NOT NULL,
    campo_modificado VARCHAR(100) NOT NULL,
    valor_anterior TEXT,
    valor_nuevo TEXT,
    usuario_email VARCHAR(255),
    usuario_id INTEGER,
    ip_address VARCHAR(45),
    fecha_cambio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revision_manual_id INTEGER,
    estado_revision_en_momento VARCHAR(20),
    observaciones TEXT,
    CONSTRAINT fk_auditoria_prestamo FOREIGN KEY (prestamo_id) 
        REFERENCES public.prestamos(id) ON DELETE CASCADE,
    CONSTRAINT fk_auditoria_cliente FOREIGN KEY (cliente_id) 
        REFERENCES public.clientes(id) ON DELETE SET NULL,
    CONSTRAINT fk_auditoria_cuota FOREIGN KEY (cuota_id) 
        REFERENCES public.cuotas(id) ON DELETE SET NULL,
    CONSTRAINT fk_auditoria_revision FOREIGN KEY (revision_manual_id) 
        REFERENCES public.revision_manual_prestamos(id) ON DELETE SET NULL
);
```

### Paso 2: Crear índices (ejecutar cada uno)
```sql
CREATE INDEX IF NOT EXISTS idx_auditoria_prestamo_id ON public.auditoria_revision_manual(prestamo_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_cliente_id ON public.auditoria_revision_manual(cliente_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_cuota_id ON public.auditoria_revision_manual(cuota_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON public.auditoria_revision_manual(fecha_cambio DESC);
CREATE INDEX IF NOT EXISTS idx_auditoria_tipo_cambio ON public.auditoria_revision_manual(tipo_cambio);
CREATE INDEX IF NOT EXISTS idx_auditoria_usuario ON public.auditoria_revision_manual(usuario_email);
CREATE INDEX IF NOT EXISTS idx_auditoria_revision_id ON public.auditoria_revision_manual(revision_manual_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_prestamo_fecha ON public.auditoria_revision_manual(prestamo_id, fecha_cambio DESC);
```

### Paso 3: Crear vista 1
```sql
DROP VIEW IF EXISTS public.v_auditoria_revision_prestamo CASCADE;
CREATE VIEW public.v_auditoria_revision_prestamo AS
SELECT 
    arm.id as cambio_id,
    arm.prestamo_id,
    p.cedula,
    p.nombres,
    arm.tipo_cambio,
    arm.tabla_afectada,
    arm.campo_modificado,
    arm.valor_anterior,
    arm.valor_nuevo,
    arm.usuario_email,
    arm.fecha_cambio,
    rmp.estado_revision,
    arm.observaciones,
    CASE 
        WHEN arm.valor_anterior IS NULL THEN 'CREADO'
        WHEN arm.valor_nuevo IS NULL THEN 'ELIMINADO'
        ELSE 'MODIFICADO'
    END as operacion
FROM public.auditoria_revision_manual arm
LEFT JOIN public.prestamos p ON arm.prestamo_id = p.id
LEFT JOIN public.revision_manual_prestamos rmp ON arm.revision_manual_id = rmp.id
ORDER BY arm.fecha_cambio DESC;
```

### Paso 4: Crear vista 2
```sql
DROP VIEW IF EXISTS public.v_auditoria_usuario CASCADE;
CREATE VIEW public.v_auditoria_usuario AS
SELECT 
    usuario_email,
    COUNT(*) as total_cambios,
    COUNT(DISTINCT prestamo_id) as prestamos_modificados,
    MIN(fecha_cambio) as primer_cambio,
    MAX(fecha_cambio) as ultimo_cambio
FROM public.auditoria_revision_manual
WHERE usuario_email IS NOT NULL
GROUP BY usuario_email
ORDER BY total_cambios DESC;
```

### Paso 5: Crear función 1
```sql
CREATE OR REPLACE FUNCTION public.fn_registrar_cambio_revision_manual(
    p_prestamo_id INTEGER,
    p_cliente_id INTEGER,
    p_cuota_id INTEGER,
    p_tipo_cambio VARCHAR,
    p_tabla_afectada VARCHAR,
    p_campo_modificado VARCHAR,
    p_valor_anterior TEXT,
    p_valor_nuevo TEXT,
    p_usuario_email VARCHAR,
    p_usuario_id INTEGER,
    p_revision_manual_id INTEGER,
    p_estado_revision VARCHAR,
    p_observaciones TEXT DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_id INTEGER;
BEGIN
    INSERT INTO public.auditoria_revision_manual (
        prestamo_id,
        cliente_id,
        cuota_id,
        tipo_cambio,
        tabla_afectada,
        campo_modificado,
        valor_anterior,
        valor_nuevo,
        usuario_email,
        usuario_id,
        revision_manual_id,
        estado_revision_en_momento,
        observaciones,
        fecha_cambio
    ) VALUES (
        p_prestamo_id,
        p_cliente_id,
        p_cuota_id,
        p_tipo_cambio,
        p_tabla_afectada,
        p_campo_modificado,
        p_valor_anterior,
        p_valor_nuevo,
        p_usuario_email,
        p_usuario_id,
        p_revision_manual_id,
        p_estado_revision,
        p_observaciones,
        CURRENT_TIMESTAMP
    )
    RETURNING id INTO v_id;
    
    RETURN v_id;
END;
$$;
```

### Paso 6: Crear función 2
```sql
CREATE OR REPLACE FUNCTION public.fn_obtener_cambios_prestamo(p_prestamo_id INTEGER)
RETURNS TABLE (
    cambio_id INTEGER,
    tipo_cambio VARCHAR,
    campo VARCHAR,
    valor_anterior TEXT,
    valor_nuevo TEXT,
    usuario VARCHAR,
    fecha TIMESTAMP,
    operacion VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        arm.id,
        arm.tipo_cambio,
        arm.campo_modificado,
        arm.valor_anterior,
        arm.valor_nuevo,
        arm.usuario_email,
        arm.fecha_cambio,
        CASE 
            WHEN arm.valor_anterior IS NULL THEN 'CREADO'
            WHEN arm.valor_nuevo IS NULL THEN 'ELIMINADO'
            ELSE 'MODIFICADO'
        END::VARCHAR
    FROM public.auditoria_revision_manual arm
    WHERE arm.prestamo_id = p_prestamo_id
    ORDER BY arm.fecha_cambio DESC;
END;
$$ LANGUAGE plpgsql;
```

### Paso 7: Crear función 3
```sql
CREATE OR REPLACE FUNCTION public.fn_resumen_cambios_revision(p_prestamo_id INTEGER)
RETURNS TABLE (
    total_cambios BIGINT,
    cambios_cliente BIGINT,
    cambios_prestamo BIGINT,
    cambios_cuotas BIGINT,
    usuarios_modificadores TEXT[],
    primer_cambio TIMESTAMP,
    ultimo_cambio TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT,
        COUNT(*) FILTER (WHERE arm.tipo_cambio = 'cliente')::BIGINT,
        COUNT(*) FILTER (WHERE arm.tipo_cambio = 'prestamo')::BIGINT,
        COUNT(*) FILTER (WHERE arm.tipo_cambio = 'cuota')::BIGINT,
        ARRAY_AGG(DISTINCT arm.usuario_email)::TEXT[],
        MIN(arm.fecha_cambio)::TIMESTAMP,
        MAX(arm.fecha_cambio)::TIMESTAMP
    FROM public.auditoria_revision_manual arm
    WHERE arm.prestamo_id = p_prestamo_id;
END;
$$ LANGUAGE plpgsql;
```

### Paso 8: Crear tabla de sesiones (OPCIONAL)
```sql
CREATE TABLE IF NOT EXISTS public.sesion_revision_manual (
    id SERIAL PRIMARY KEY,
    usuario_email VARCHAR(255) NOT NULL,
    usuario_id INTEGER,
    prestamo_id INTEGER NOT NULL,
    fecha_inicio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_fin TIMESTAMP,
    duracion_minutos NUMERIC(10, 2),
    ip_address VARCHAR(45),
    navegador VARCHAR(255),
    dispositivo VARCHAR(100),
    estado_final VARCHAR(20),
    cambios_totales INTEGER DEFAULT 0,
    CONSTRAINT fk_sesion_prestamo FOREIGN KEY (prestamo_id) 
        REFERENCES public.prestamos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sesion_prestamo ON public.sesion_revision_manual(prestamo_id);
CREATE INDEX IF NOT EXISTS idx_sesion_usuario ON public.sesion_revision_manual(usuario_email);
CREATE INDEX IF NOT EXISTS idx_sesion_fecha ON public.sesion_revision_manual(fecha_inicio DESC);
```

---

## ✅ Verificar que se creó correctamente

```sql
-- Ver estructura de la tabla
SELECT * FROM information_schema.columns
WHERE table_name = 'auditoria_revision_manual'
ORDER BY ordinal_position;

-- Ver que existen los índices
SELECT indexname FROM pg_indexes
WHERE tablename = 'auditoria_revision_manual';

-- Ver que existen las vistas
SELECT viewname FROM pg_views
WHERE schemaname = 'public' AND viewname LIKE 'v_auditoria%';

-- Ver que existen las funciones
SELECT routine_name FROM information_schema.routines
WHERE routine_schema = 'public' AND routine_name LIKE 'fn_%revision%';
```

---

## 🔧 Si hay errores

Si recives error de "syntax error at or near", intenta:

1. **Eliminar toda la tabla y crear nueva**:
```sql
DROP TABLE IF EXISTS public.auditoria_revision_manual CASCADE;
DROP TABLE IF EXISTS public.sesion_revision_manual CASCADE;
```

2. **Luego ejecutar el SQL limpio nuevamente**

3. **Si persiste el error, reporta:**
   - Línea del error
   - Mensaje exacto
   - Tu versión de PostgreSQL (`SELECT version();`)

---

## 📋 Resumen

| Elemento | Cantidad | Propósito |
|----------|----------|-----------|
| Tablas | 2 | Auditoría + Sesiones |
| Índices | 8 | Performance |
| Vistas | 2 | Consultas formateadas |
| Funciones | 3 | Lógica reutilizable |

**Total de objetos: 15**

---

## ✅ Listo

Una vez ejecutado el SQL, tu sistema de auditoría está listo para registrar TODOS los cambios en revisión manual.
