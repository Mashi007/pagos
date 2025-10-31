# ✅ Verificación de Conexión BD - Plantillas y Notificaciones

## 🔍 Estado de Conexión a Base de Datos

### ✅ Endpoints Conectados Correctamente

Todos los endpoints están conectados a la base de datos usando `db: Session = Depends(get_db)`:

1. **Plantillas:**
   - `GET /api/v1/notificaciones/plantillas` - Listar plantillas ✅
   - `GET /api/v1/notificaciones/plantillas/verificar` - **NUEVO: Verificar estado** ✅
   - `POST /api/v1/notificaciones/plantillas` - Crear plantilla ✅
   - `PUT /api/v1/notificaciones/plantillas/{id}` - Actualizar plantilla ✅
   - `DELETE /api/v1/notificaciones/plantillas/{id}` - Eliminar plantilla ✅
   - `GET /api/v1/notificaciones/plantillas/{id}` - Obtener plantilla ✅

2. **Notificaciones:**
   - `GET /api/v1/notificaciones/` - Listar notificaciones ✅
   - `POST /api/v1/notificaciones/enviar` - Enviar notificación ✅
   - `POST /api/v1/notificaciones/plantillas/{id}/enviar` - Enviar con plantilla ✅

## 📋 Cómo Verificar el Estado

### 1. Verificar Conexión y Plantillas

```bash
GET /api/v1/notificaciones/plantillas/verificar
```

**Respuesta esperada:**
```json
{
  "conexion_bd": true,
  "total_plantillas": 7,
  "plantillas_activas": 7,
  "tipos_esperados": [
    "PAGO_5_DIAS_ANTES",
    "PAGO_3_DIAS_ANTES",
    "PAGO_1_DIA_ANTES",
    "PAGO_DIA_0",
    "PAGO_1_DIA_ATRASADO",
    "PAGO_3_DIAS_ATRASADO",
    "PAGO_5_DIAS_ATRASADO"
  ],
  "tipos_encontrados": [...],
  "tipos_faltantes": [],
  "plantillas_ok": true,
  "mensaje": "✅ Todas las plantillas necesarias están configuradas"
}
```

### 2. Si la BD está vacía (todo en blanco)

Ejecuta el script SQL para crear las plantillas iniciales:

```sql
-- Archivo: scripts/sql/EJECUTAR_MIGRACION_PLANTILLAS.sql
```

Este script crea:
- Tabla `notificacion_plantillas` (si no existe)
- 7 plantillas iniciales con todos los tipos necesarios
- Variables disponibles en cada plantilla

### 3. Verificar después de cargar

```bash
GET /api/v1/notificaciones/plantillas/verificar
```

## 🔧 Configuración de Variables

Las plantillas usan variables dinámicas con formato `{{variable}}`:

- `{{nombre}}` - Nombre del cliente
- `{{monto}}` - Monto de la cuota
- `{{numero_cuota}}` - Número de cuota
- `{{fecha_vencimiento}}` - Fecha de vencimiento
- `{{prestamo_id}}` - ID del préstamo

## 📝 Ejemplo de Uso

### Crear plantilla manualmente:

```bash
POST /api/v1/notificaciones/plantillas
{
  "nombre": "Recordatorio - 5 Días Antes",
  "tipo": "PAGO_5_DIAS_ANTES",
  "asunto": "Recordatorio de Pago - Cuota {{numero_cuota}}",
  "cuerpo": "Estimado/a {{nombre}}, le recordamos que el pago de {{monto}} VES vence en 5 días.",
  "activa": true
}
```

### Enviar notificación con plantilla:

```bash
POST /api/v1/notificaciones/plantillas/{plantilla_id}/enviar
{
  "cliente_id": 123,
  "variables": {
    "nombre": "Juan Pérez",
    "monto": "500.00",
    "numero_cuota": "3",
    "fecha_vencimiento": "2025-11-15"
  }
}
```

## ✅ Checklist de Verificación

- [ ] Endpoints conectados a BD: ✅ Todos verificados
- [ ] Tabla `notificacion_plantillas` existe: Verificar con script SQL
- [ ] Plantillas iniciales cargadas: Ejecutar `EJECUTAR_MIGRACION_PLANTILLAS.sql`
- [ ] Todas las plantillas activas: Verificar con endpoint `/plantillas/verificar`
- [ ] Variables configuradas: Revisar campo `variables_disponibles` en plantillas

## 🚀 Próximos Pasos

1. **Si está en blanco:** Ejecutar script SQL para crear plantillas iniciales
2. **Verificar conexión:** Usar endpoint `/plantillas/verificar`
3. **Crear plantillas faltantes:** Usar endpoint POST `/plantillas` o el frontend
4. **Configurar email:** Ir a Configuración > Email para configurar SMTP

