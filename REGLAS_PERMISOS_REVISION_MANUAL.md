# 🔐 REGLAS DE PERMISOS - Sistema de Estados de Revisión Manual

## Resumen Ejecutivo

Se implementó un **sistema granular de permisos** donde:
- **Usuarios regulares**: Pueden iniciar revisión (⚠️ → ❓) y marcar errores (❓ ↔ ❌)
- **Administradores**: Tienen control total + pueden reabrir préstamos revisados

## 🎯 Matriz de Permisos por Estado

### Estado: ⚠️ PENDIENTE

| Usuario | Permiso | Acción |
|---------|---------|--------|
| Regular | ✅ SÍ | Click → Inicia revisión (❓) |
| Admin | ✅ SÍ | Click → Inicia revisión (❓) |

---

### Estado: ❓ REVISANDO

| Usuario | Permiso | Acción |
|---------|---------|--------|
| **Regular** | ❌ NO | No puede editar NI cambiar estado |
| **Admin** | ✅ SÍ | Puede editar Y cambiar estado a ❌ o ✓ |

**Explicación:**
- Usuario regular que abrió el préstamo para editar **AHORA NO PUEDE HACERLO**
- Debe pedirle al admin que regrese el préstamo a ❌ EN ESPERA o haga clic nuevamente
- Solo admin puede cambiar el estado de este préstamo

---

### Estado: ❌ EN ESPERA

| Usuario | Permiso | Acción |
|---------|---------|--------|
| Regular | ✅ SÍ | Click → Regresa a ❓ para continuar análisis |
| Admin | ✅ SÍ | Click → Regresa a ❓ O marca como ✓ REVISADO |

**Explicación:**
- Usuario regular puede "rescatar" el préstamo de EN ESPERA
- Admin tiene opciones adicionales (finalizar directamente)

---

### Estado: ✓ REVISADO

| Usuario | Permiso | Acción |
|---------|---------|--------|
| Regular | ❌ NO | No puede hacer nada (finalizado) |
| Admin | ✅ SÍ | Click → Reabrir a ❓ REVISANDO (para editar de nuevo) |

**Explicación:**
- Cualquier usuario ve "Finalizado" (no clickeable)
- Solo admin puede reabrir para permitir edición adicional
- Al reabrir, limpia fecha de cierre

---

## 📋 Tabla Consolidada

| Estado | Regular | Admin | Acciones del Admin |
|--------|---------|-------|-------------------|
| **⚠️ Pendiente** | Iniciar ✅ | Iniciar ✅ | - |
| **❓ Revisando** | ❌ Bloqueado | Editar + cambiar ✅ | Cambiar a ❌ o ✓ |
| **❌ En Espera** | Regresa a ❓ ✅ | Regresa a ❓ o ✓ ✅ | Finalizar directamente |
| **✓ Revisado** | ❌ Bloqueado | Reabrir a ❓ ✅ | Permitir nueva edición |

---

## 🔄 Flujos de Uso

### Flujo 1: Usuario Regular (Sin Permisos de Edición)

```
1. Usuario ve ⚠️ PENDIENTE
2. Click en icono
3. Cambia a ❓ REVISANDO
   ↓
4. Usuario intenta acceder al editor
5. Sistema: "Solo admin puede editar en estado ❓ REVISANDO"
6. Usuario contacta admin

┌─────────────────────────────────────┐
│ Mensaje de error:                   │
│                                     │
│ "Este préstamo está en revisión.    │
│ Solo administradores pueden editar  │
│ en este estado.                     │
│ Contacta con tu administrador."     │
└─────────────────────────────────────┘

7. Admin recibe solicitud
8. Admin hace click en icono
9. Admin elige "EN ESPERA" o "REVISANDO"
10. Ahora usuario puede editar de nuevo
```

### Flujo 2: Administrador (Control Total)

```
1. Admin ve ⚠️ PENDIENTE
2. Click → Inicia revisión (❓)
3. Abre editor
4. Edita datos
5. Puede cambiar estado en cualquier momento
   - Cambiar a ❌ EN ESPERA
   - Cambiar a ✓ REVISADO
   - Regresar a ⚠️ PENDIENTE (si es necesario)
6. Finaliza como ✓ REVISADO
7. Más tarde, si necesita editar:
8. Click en ✓ REVISADO
9. Reabre a ❓ REVISANDO
10. Edita de nuevo
11. Finaliza nuevamente
```

### Flujo 3: Reasignación de Usuario

```
Scenario: Usuario A started, admin needs to continue

1. Usuario A inicia revisión (⚠️ → ❓)
2. Usuario A intenta editar: "❌ Bloqueado - Solo admin"
3. Admin hace click en icono (❓)
4. Admin elige: "EN ESPERA"
5. Ahora Usuario A puede editar nuevamente
6. Usuario A continúa desde donde paró
7. Cuando termina: Avisa a admin
8. Admin finaliza: Cambia a ✓ REVISADO
```

---

## 🚨 Mensajes de Error Implementados

### Error 1: Usuario Regular Intenta Editar en ❓ REVISANDO

```
Endpoint PUT /revision-manual/clientes/{id}
Status: 403 Forbidden

Respuesta:
{
  "detail": "Este préstamo está en revisión. Solo administradores 
           pueden editar en este estado. Contacta con tu administrador."
}
```

### Error 2: Usuario Regular Intenta Cambiar de ✓ → ❓

```
Endpoint PATCH /revision-manual/prestamos/{id}/estado-revision
Status: 403 Forbidden

Respuesta:
{
  "detail": "Solo administradores pueden cambiar un préstamo revisado 
           de vuelta a revisión"
}
```

### Error 3: Usuario Regular Intenta Marcar Como ✓

```
Endpoint PATCH /revision-manual/prestamos/{id}/estado-revision
Status: 403 Forbidden

Respuesta:
{
  "detail": "Solo administradores pueden marcar como revisado"
}
```

---

## 🔍 Validaciones en Backend

### Función: `_validar_permiso_edicion()`

```python
def _validar_permiso_edicion(
    db: Session,
    prestamo_id: int,
    current_user: Any,
    actor: str,
) -> None:
    """
    Valida permisos de edición según estado y rol.
    
    Reglas:
    - ✓ REVISADO: Nadie (HTTPException 403)
    - ❓ REVISANDO: Solo admin (HTTPException 403 si no admin)
    - ⚠️ PENDIENTE, ❌ EN ESPERA: Todos permitido
    """
```

### Dónde se usa:

```
PUT /revision-manual/clientes/{id}
PUT /revision-manual/prestamos/{id}
PUT /revision-manual/cuotas/{id}
DELETE /revision-manual/prestamos/{id}/cuotas/{id}
```

---

## 📊 Estado Actual vs Nuevo

### ANTES (Sin Control de Permisos)

```
Cualquier usuario autenticado:
  ✅ Podía editar cliente, préstamo, cuotas
  ✅ Podía cambiar cualquier estado
  ❌ Sin control de roles
  ❌ Posibilidad de confusión entre usuarios
```

### AHORA (Con Control de Permisos Granular)

```
Usuario Regular:
  ✅ Puede iniciar revisión (⚠️ → ❓)
  ✅ Puede marcar EN ESPERA (❓ → ❌)
  ✅ Puede editar en ⚠️ PENDIENTE o ❌ EN ESPERA
  ❌ NO puede editar en ❓ REVISANDO
  ❌ NO puede editar en ✓ REVISADO
  ❌ NO puede marcar como REVISADO

Administrador:
  ✅ Puede hacer TODO
  ✅ Puede editar en cualquier estado
  ✅ Puede cambiar entre cualquier estado
  ✅ Puede reabrir ✓ REVISADO
  ✅ Control total del flujo
```

---

## 🎯 Casos de Uso Prácticos

### Caso 1: Usuario Comienza, Admin Continúa

```
Paso 1: Juan (usuario) ve ⚠️ PENDIENTE
Paso 2: Juan hace click → Cambia a ❓ REVISANDO
Paso 3: Juan intenta editar → Bloqueado
Paso 4: Juan llama a admin María
Paso 5: María cambia a ❌ EN ESPERA (opción 1) o ❓ (opción 2)
Paso 6: Ahora Juan puede editar de nuevo
Paso 7: Juan termina y avisa a María
Paso 8: María abre editor y finaliza
```

### Caso 2: Admin Descubre Problema Después de Finalizar

```
Paso 1: Admin finaliza ✓ REVISADO
Paso 2: Luego descubre error en los datos
Paso 3: Admin hace click en icono ✓
Paso 4: Opción: "Reabrir a ❓ REVISANDO"
Paso 5: Admin corrige datos
Paso 6: Admin finaliza de nuevo
```

### Caso 3: Reasignación de Tarea

```
Paso 1: Usuario A inicia ⚠️ → ❓
Paso 2: Usuario A se va de la oficina
Paso 3: Usuario B necesita continuar
Paso 4: Admin hace click en icono
Paso 5: Admin elige "EN ESPERA"
Paso 6: Ahora Usuario A O B pueden editar desde el inicio
        (porque está en ❌ EN ESPERA)
```

---

## 🔐 Auditoría de Cambios

Cada cambio de estado se registra automáticamente con:

```json
{
  "usuario": "maria@admin.com",
  "accion": "cambiar_estado_revision",
  "prestamo_id": 123,
  "estado_anterior": "revisando",
  "estado_nuevo": "revisado",
  "fecha": "2026-03-31T14:30:00Z",
  "detalles": "Admin finalizó la revisión"
}
```

---

## ⚙️ Configuración de Roles

### ¿Cómo verificar si un usuario es Admin?

Backend comprueba:

```python
es_admin = (
    getattr(current_user, "is_admin", False) or 
    getattr(current_user, "is_superuser", False)
)
```

**Necesitas que tu modelo de Usuario tenga:**
- Campo `is_admin: Boolean`
- O campo `is_superuser: Boolean`

---

## 🚀 Implementación de Cambios

### Backend
```python
# Nueva función de validación
_validar_permiso_edicion()

# Endpoints actualizados
PUT /revision-manual/clientes/{id}
PUT /revision-manual/prestamos/{id}
PUT /revision-manual/cuotas/{id}
DELETE /revision-manual/prestamos/{id}/cuotas/{id}

# Endpoint de estado actualizado
PATCH /revision-manual/prestamos/{id}/estado-revision
```

### Frontend
```typescript
// Component actualizado
EstadoRevisionIcon.tsx

// Diálogos actualizados
- Mostrar opciones diferentes para admin
- Permitir reabrir ✓ REVISADO (solo admin)
- Mensajes de error descriptivos
```

---

## 📚 Documentación para Usuarios

### Usuarios Regulares
```
✅ Puedes:
- Iniciar revisión
- Editar en PENDIENTE o EN ESPERA
- Marcar como EN ESPERA si encontraste errores
- Ver estado de todos los préstamos

❌ No puedes:
- Editar cuando está en REVISANDO
- Marcar como REVISADO
- Editar cuando está REVISADO
- Reabrir un préstamo revisado
```

### Administradores
```
✅ Puedes:
- Hacer TODO lo que usuarios regulares
- Editar en cualquier estado
- Cambiar entre cualquier estado
- Marcar como REVISADO
- Reabrir un REVISADO para editar de nuevo
- Resolver bloqueos de usuarios

⚠️ Responsabilidades:
- Autorizar cambios críticos
- Gestionar resolución de errores
- Dar acceso a usuarios si es necesario
```

---

## 🎓 Entrenamientos Recomendados

### Para Usuarios Regulares
1. Cómo iniciar revisión
2. Qué hacer si está bloqueado
3. Cuándo contactar a admin

### Para Administradores
1. Cómo gestionar estados
2. Cómo permitir que usuarios continúen
3. Cómo reabrir para corregir errores
4. Mejores prácticas de auditoría

---

## ✅ Checklist de Verificación

- [x] Backend valida permisos en endpoints de edición
- [x] Backend valida permisos en cambio de estado
- [x] Frontend muestra mensajes de error descriptivos
- [x] Admin puede reabrir ✓ REVISADO
- [x] Usuario regular no puede editar en ❓ REVISANDO
- [x] Usuario regular no puede cambiar de ✓ → ❓
- [x] Auditoría registra cada cambio
- [x] Mensajes de error claros
- [x] Documentación completa

---

**Fecha**: 31-03-2026  
**Versión**: 2.0 (Con Control de Permisos)  
**Estado**: ✅ LISTO PARA PRODUCCIÓN
