# 🔍 Identificar Tablas que Apoyan Procesos de CRM

**Fecha:** 2025-01-27  
**Objetivo:** Scripts para identificar todas las tablas relacionadas con procesos de CRM (Customer Relationship Management)

---

## 📋 Tablas CRM Identificadas

### Tablas Principales

| Categoría | Tabla | Descripción |
|------------|-------|-------------|
| **CORE** | `clientes` | Tabla principal de clientes - Información demográfica y de contacto |
| **ATENCIÓN** | `tickets` | Tickets de atención al cliente - Gestión de consultas, incidencias y reclamos |
| **COMUNICACIÓN** | `conversaciones_whatsapp` | Conversaciones de WhatsApp entre clientes y bot/sistema |
| **COMUNICACIÓN** | `comunicaciones_email` | Comunicaciones por Email - Emails recibidos y enviados |
| **COMUNICACIÓN** | `notificaciones` | Notificaciones - Recordatorios y alertas enviadas a clientes |
| **IA** | `conversaciones_ai` | Conversaciones con IA - Interacciones con asistente virtual |
| **VENTAS** | `prestamos` | Préstamos - Embudo de ventas y gestión de créditos |
| **COBRANZA** | `pagos` | Pagos - Seguimiento de pagos y cobranza |

### Tablas de Catálogo Relacionadas

| Tabla | Descripción |
|-------|-------------|
| `concesionarios` | Catálogo de concesionarios - Usado en préstamos |
| `analistas` | Catálogo de analistas - Usado en préstamos |
| `modelos_vehiculos` | Catálogo de modelos de vehículos - Usado en préstamos |
| `users` | Usuarios del sistema - Asignación de tickets y gestión |
| `notificacion_plantillas` | Plantillas de notificaciones - Templates para comunicaciones |

---

## 🚀 Cómo Usar los Scripts

### Opción 1: Script SQL (DBeaver / pgAdmin)

**Ubicación:** `scripts/sql/identificar_tablas_crm.sql`

**Pasos:**

1. Abrir DBeaver o pgAdmin
2. Conectarse a la base de datos PostgreSQL
3. Abrir el archivo `scripts/sql/identificar_tablas_crm.sql`
4. Ejecutar el script completo (F5 o botón Ejecutar)
5. Revisar los resultados en las pestañas de resultados

**El script genera:**

- ✅ Lista de tablas principales de CRM con total de registros
- ✅ Relaciones entre tablas (Foreign Keys)
- ✅ Estadísticas de uso por cliente
- ✅ Tablas de catálogo relacionadas
- ✅ Resumen de funciones de cada tabla
- ✅ Verificación de existencia de tablas
- ✅ Índices en tablas CRM
- ✅ Estadísticas de actividad (últimos 30 días)

---

### Opción 2: Script Python

**Ubicación:** `backend/scripts/identificar_tablas_crm.py`

**Pasos:**

```powershell
# 1. Navegar al directorio backend
cd backend

# 2. Ejecutar el script
py scripts/identificar_tablas_crm.py
```

**El script genera un reporte en consola con:**

- ✅ Tablas principales de CRM organizadas por categoría
- ✅ Relaciones entre tablas (Foreign Keys)
- ✅ Estadísticas de uso generales
- ✅ Actividad CRM de los últimos 30 días
- ✅ Tablas de catálogo relacionadas
- ✅ Resumen ejecutivo

**Ejemplo de salida:**

```
============================================================
🔍 IDENTIFICACIÓN DE TABLAS CRM
============================================================

============================================================
📊 TABLAS PRINCIPALES DE CRM
============================================================

📁 CORE:
   ✅ clientes                        -   1234 registros

📁 ATENCION:
   ✅ tickets                         -    567 registros

📁 COMUNICACION:
   ✅ conversaciones_whatsapp         -   8901 registros
   ✅ comunicaciones_email            -    234 registros
   ✅ notificaciones                  -   5678 registros

...
```

---

## 📊 Módulos CRM y sus Funciones

### 1. Gestión de Clientes
- **Tabla:** `clientes`
- **Función:** Almacena información demográfica, de contacto y estado de clientes

### 2. Atención al Cliente
- **Tabla:** `tickets`
- **Función:** Gestiona consultas, incidencias, reclamos y solicitudes de clientes

### 3. Comunicaciones
- **Tablas:** 
  - `conversaciones_whatsapp` - Almacena conversaciones de WhatsApp
  - `comunicaciones_email` - Almacena emails recibidos y enviados
  - `notificaciones` - Gestiona notificaciones automáticas

### 4. Inteligencia Artificial
- **Tabla:** `conversaciones_ai`
- **Función:** Almacena conversaciones con asistente virtual para análisis y mejora

### 5. Embudo de Ventas
- **Tabla:** `prestamos`
- **Función:** Gestiona el ciclo de vida de préstamos desde solicitud hasta aprobación

### 6. Cobranza
- **Tabla:** `pagos`
- **Función:** Registra y gestiona pagos de clientes para seguimiento de cobranza

---

## 🔗 Relaciones Principales

### Relaciones con `clientes` (Tabla Principal)

Las siguientes tablas tienen Foreign Key a `clientes.id`:

- ✅ `prestamos.cliente_id`
- ✅ `tickets.cliente_id`
- ✅ `conversaciones_whatsapp.cliente_id`
- ✅ `comunicaciones_email.cliente_id`
- ✅ `conversaciones_ai.cliente_id`
- ✅ `notificaciones.cliente_id`

### Relaciones entre Tablas CRM

- `tickets` ↔ `conversaciones_whatsapp` (bidireccional)
- `tickets` ↔ `comunicaciones_email` (bidireccional)
- `conversaciones_whatsapp` → `tickets` (self-reference para respuestas)
- `comunicaciones_email` → `tickets` (self-reference para respuestas)

---

## 📈 Casos de Uso

### 1. Verificar Integridad de Datos CRM

```sql
-- Verificar que todos los tickets tienen cliente válido
SELECT COUNT(*) 
FROM tickets t
LEFT JOIN clientes c ON t.cliente_id = c.id
WHERE t.cliente_id IS NOT NULL AND c.id IS NULL;
```

### 2. Analizar Actividad de Cliente

```sql
-- Ver todas las interacciones de un cliente
SELECT 
    'Ticket' as tipo,
    t.titulo as descripcion,
    t.creado_en as fecha
FROM tickets t
WHERE t.cliente_id = :cliente_id

UNION ALL

SELECT 
    'WhatsApp' as tipo,
    cw.body as descripcion,
    cw.timestamp as fecha
FROM conversaciones_whatsapp cw
WHERE cw.cliente_id = :cliente_id

ORDER BY fecha DESC;
```

### 3. Dashboard de Métricas CRM

```sql
-- Métricas generales de CRM
SELECT 
    (SELECT COUNT(*) FROM clientes) as total_clientes,
    (SELECT COUNT(*) FROM tickets WHERE estado = 'abierto') as tickets_abiertos,
    (SELECT COUNT(*) FROM conversaciones_whatsapp 
     WHERE timestamp >= NOW() - INTERVAL '24 hours') as conversaciones_hoy,
    (SELECT COUNT(*) FROM notificaciones 
     WHERE estado = 'ENVIADA' AND enviada_en >= NOW() - INTERVAL '24 hours') as notificaciones_enviadas_hoy;
```

---

## 🔍 Verificación de Tablas

### Verificar si todas las tablas CRM existen:

```sql
SELECT 
    table_name,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = t.table_name
        ) THEN '✅ EXISTE'
        ELSE '❌ NO EXISTE'
    END as estado
FROM (
    VALUES 
        ('clientes'),
        ('tickets'),
        ('conversaciones_whatsapp'),
        ('comunicaciones_email'),
        ('conversaciones_ai'),
        ('notificaciones'),
        ('prestamos'),
        ('pagos')
) AS t(table_name);
```

---

## 📚 Archivos Relacionados

- **Script SQL:** `scripts/sql/identificar_tablas_crm.sql`
- **Script Python:** `backend/scripts/identificar_tablas_crm.py`
- **Documentación de modelos:** `backend/app/models/`
- **Documentación de relaciones:** `Documentos/Analisis/MAPEO_RED_TABLAS_POSTGRES.md`

---

## ⚠️ Notas Importantes

1. **Dependencias:** Algunas tablas pueden no existir si no se han ejecutado todas las migraciones
2. **Rendimiento:** Los scripts de estadísticas pueden tardar en tablas grandes
3. **Permisos:** Asegúrate de tener permisos de lectura en todas las tablas

---

## 🆘 Solución de Problemas

### Error: "relation does not exist"

**Causa:** La tabla no existe en la base de datos.

**Solución:** 
- Verificar que se hayan ejecutado todas las migraciones: `alembic upgrade head`
- Verificar que estás conectado a la base de datos correcta

### Error: "permission denied"

**Causa:** No tienes permisos para leer la tabla.

**Solución:** 
- Contactar al administrador de la base de datos
- Verificar permisos del usuario de la base de datos

---

**¿Necesitas más información?** Revisa la documentación de cada modelo en `backend/app/models/` o consulta el mapeo completo de relaciones en `Documentos/Analisis/MAPEO_RED_TABLAS_POSTGRES.md`.

