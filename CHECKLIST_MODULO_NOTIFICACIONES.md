# ✅ CHECKLIST MÓDULO NOTIFICACIONES Y PLANTILLAS

**Fecha revisión:** 2025-10-30  
**Estado general:** 🟢 **FUNCIONAL** (requiere configuración externa para scheduler)

---

## 📋 BACKEND - ESTADO ACTUAL

### ✅ Modelos de Base de Datos
- [x] **`Notificacion`** (tabla `notificaciones`)
  - Campos: `canal`, `asunto`, `mensaje`, `estado`, `enviada_en`, etc.
  - Relaciones: `cliente_id`, `user_id`
- [x] **`NotificacionPlantilla`** (tabla `notificacion_plantillas`)
  - Campos: `nombre`, `tipo`, `asunto`, `cuerpo`, `activa`, `variables_disponibles`
  - Índices y validaciones OK
- [x] Migración Alembic creada: `20251030_add_cols_canal_asunto_notificaciones.py`

### ✅ Endpoints API - Notificaciones
- [x] `GET /api/v1/notificaciones/` - Listar notificaciones
- [x] `GET /api/v1/notificaciones/{id}` - Obtener notificación
- [x] `POST /api/v1/notificaciones/enviar` - Enviar notificación individual
- [x] `POST /api/v1/notificaciones/envio-masivo` - Envío masivo
- [x] `GET /api/v1/notificaciones/estadisticas/resumen` - Estadísticas

### ✅ Endpoints API - Plantillas
- [x] `GET /api/v1/notificaciones/plantillas` - Listar plantillas
- [x] `GET /api/v1/notificaciones/plantillas/{id}` - Obtener plantilla
- [x] `POST /api/v1/notificaciones/plantillas` - Crear plantilla
- [x] `PUT /api/v1/notificaciones/plantillas/{id}` - Actualizar plantilla
- [x] `DELETE /api/v1/notificaciones/plantillas/{id}` - Eliminar plantilla
- [x] `GET /api/v1/notificaciones/plantillas/{id}/export` - Exportar plantilla (JSON)
- [x] `POST /api/v1/notificaciones/plantillas/{id}/enviar` - Enviar con plantilla
- [x] `GET /api/v1/notificaciones/plantillas/verificar` - Verificar estado de plantillas

### ✅ Endpoints API - Notificaciones Automáticas
- [x] `POST /api/v1/notificaciones/automaticas/procesar` - Procesar automáticas (para scheduler)

### ✅ Servicios
- [x] `NotificacionAutomaticaService` - Procesa cuotas y envía según días
- [x] `EmailService` - Envío de correos
- [x] `WhatsAppService` - Envío WhatsApp (si aplica)

### ✅ Auditoría
- [x] Auditoría en crear plantilla
- [x] Auditoría en actualizar plantilla
- [x] Auditoría en eliminar plantilla
- [x] Auditoría en exportar plantilla

### ✅ Integración con Cobranzas
- [x] `POST /api/v1/cobranzas/notificaciones/atrasos` - Disparar desde Cobranzas

---

## 📋 FRONTEND - ESTADO ACTUAL

### ✅ Navegación y Rutas
- [x] Ruta protegida: `/herramientas/plantillas` (solo Admin)
- [x] Submenú en Sidebar: "Herramientas → Plantillas" (visible solo Admin)
- [x] Componente `PlantillasNotificaciones.tsx` creado
- [x] Página `Plantillas.tsx` creada

### ✅ Editor de Plantillas
- [x] Lista de plantillas (panel izquierdo)
- [x] Formulario completo:
  - [x] Nombre
  - [x] Tipo (selector con tipos sugeridos)
  - [x] Toggle "Habilitar envío automático a las 3:00 AM" (activa)
  - [x] Asunto
  - [x] Encabezado
  - [x] Cuerpo
  - [x] Firma
- [x] **Variables dinámicas:**
  - [x] Input para escribir variable
  - [x] Botón "Agrega" que inserta `{{variable}}`
  - [x] Sugerencias mostradas en UI
- [x] **WYSIWYG básico:**
  - [x] Botones B, I, U, Lista, Enlace
  - [x] Aplica formato al campo enfocado
- [x] Vista previa (asunto + cuerpo final)
- [x] Validación de variables obligatorias por tipo

### ✅ Funcionalidades
- [x] Crear plantilla nueva
- [x] Editar plantilla existente
- [x] Eliminar plantilla
- [x] Exportar plantilla (descarga JSON)
- [x] Enviar prueba:
  - [x] Selector de cliente con búsqueda
  - [x] Envío usando plantilla

### ✅ Integración Backend
- [x] `notificacionService` completo:
  - [x] `listarPlantillas()`
  - [x] `obtenerPlantilla()`
  - [x] `crearPlantilla()`
  - [x] `actualizarPlantilla()`
  - [x] `eliminarPlantilla()`
  - [x] `exportarPlantilla()`
  - [x] `enviarConPlantilla()`

---

## ⚠️ PENDIENTE / FALTANTE

### 🔴 CRÍTICO - Configuración Externa Requerida
- [ ] **Scheduler externo (CRON/Task Scheduler) para ejecutar a las 3:00 AM**
  - Endpoint a llamar: `POST /api/v1/notificaciones/automaticas/procesar`
  - **Nota:** El backend NO tiene scheduler interno automático. Se requiere configuración manual del sistema operativo.

### 🟡 MEJORAS OPCIONALES (No bloquean funcionamiento)

#### Backend
- [ ] Endpoint para importar plantilla desde JSON
- [ ] Endpoint para clonar/duplicar plantilla
- [ ] Historial de versiones de plantillas
- [ ] Estadísticas de uso de plantillas

#### Frontend
- [ ] **Vista previa HTML renderizada** (actualmente solo texto plano)
- [ ] Editor WYSIWYG más avanzado (opcional, actual es básico)
- [ ] Validación en tiempo real de variables mientras escribes
- [ ] Plantillas predefinidas/ejemplos al crear nueva
- [ ] Búsqueda/filtro de plantillas en lista
- [ ] Confirmación visual al guardar (toast/notificación)
- [ ] Manejo de errores más amigable (actualmente usa `alert()`)

#### Integración
- [ ] Botón "Procesar ahora" en UI de Cobranzas que llame al endpoint
- [ ] Dashboard de notificaciones enviadas

---

## ✅ RESUMEN EJECUTIVO

### 🟢 COMPLETADO Y LISTO PARA USAR:
1. **Backend completo:** Modelos, endpoints, servicios, auditoría
2. **Frontend funcional:** Editor completo, CRUD, exportar, enviar prueba
3. **Validaciones:** Variables obligatorias por tipo
4. **Integración Cobranzas:** Endpoint listo

### ⚠️ REQUIERE CONFIGURACIÓN MANUAL:
1. **Scheduler externo:** Configurar CRON/Task Scheduler en servidor para ejecutar `POST /api/v1/notificaciones/automaticas/procesar` a las 3:00 AM

### 🟡 MEJORAS FUTURAS (OPCIONAL):
- Vista previa HTML renderizada
- Editor WYSIWYG avanzado
- Importar plantillas
- Estadísticas de uso

---

## 📝 NOTAS IMPORTANTES

1. **Variables disponibles:**
   - `{{nombre}}`, `{{monto}}`, `{{fecha_vencimiento}}`, `{{numero_cuota}}`, `{{credito_id}}`, `{{cedula}}`, `{{dias_atraso}}`

2. **Tipos de plantilla (reglas del programador):**
   - `PAGO_5_DIAS_ANTES`, `PAGO_3_DIAS_ANTES`, `PAGO_1_DIA_ANTES`, `PAGO_DIA_0`
   - `PAGO_1_DIA_ATRASADO`, `PAGO_3_DIAS_ATRASADO`, `PAGO_5_DIAS_ATRASADO`

3. **Toggle "Habilitar envío automático 3:00 AM":**
   - Marca `activa=true` en BD
   - El scheduler externo debe llamar al endpoint de procesar automáticas

4. **Exportación:**
   - Descarga JSON con: `id`, `nombre`, `tipo`, `asunto`, `cuerpo`, `activa`
   - Útil para backup o compartir entre ambientes

---

**Estado Final:** ✅ **LISTO PARA USAR** (requiere configuración de scheduler externo para automatización)

