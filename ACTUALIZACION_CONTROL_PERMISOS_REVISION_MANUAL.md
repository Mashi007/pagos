# ✅ ACTUALIZACIÓN: Control de Permisos por Rol en Revisión Manual

## 📢 Cambios Implementados

Se agregó un **sistema granular de control de permisos** donde los usuarios regulares y administradores tienen diferentes niveles de acceso según el estado de revisión del préstamo.

---

## 🎯 Reglas de Acceso Implementadas

### 1. **Usuarios Regulares** (Revisores)

```
PERMITIDO:
✅ Iniciar revisión (⚠️ → ❓)
✅ Cambiar a EN ESPERA (❓ ↔ ❌)
✅ Editar cliente, préstamo, cuotas en estado: ⚠️ PENDIENTE o ❌ EN ESPERA
✅ Ver todos los estados

BLOQUEADO:
❌ Editar cuando está en ❓ REVISANDO
❌ Editar cuando está en ✓ REVISADO
❌ Marcar como ✓ REVISADO
❌ Cambiar de ✓ REVISADO a ❓ REVISANDO
```

### 2. **Administradores**

```
PERMITIDO:
✅ ACCESO TOTAL
✅ Editar en CUALQUIER estado
✅ Cambiar entre CUALQUIER estado
✅ Marcar como ✓ REVISADO
✅ Reaabrir ✓ REVISADO a ❓ REVISANDO (para permitir nueva edición)
✅ Gestionar flujos de usuarios
✅ Resolver bloqueos
```

---

## 🔄 Matriz de Control

### Estado: ❓ REVISANDO (Cambio Crítico)

| Rol | Acción | Resultado |
|-----|--------|-----------|
| **Usuario** | Intenta editar | ❌ HTTPException 403 |
| **Usuario** | Intenta cambiar estado | ❌ HTTPException 403 |
| **Admin** | Edita datos | ✅ Permitido |
| **Admin** | Cambia estado | ✅ Permitido |

### Estado: ✓ REVISADO (Cambio Crítico)

| Rol | Acción | Resultado |
|-----|--------|-----------|
| **Usuario** | Intenta editar | ❌ HTTPException 403 |
| **Usuario** | Intenta reabrir | ❌ HTTPException 403 |
| **Admin** | Reabrir a ❓ | ✅ Permitido |
| **Admin** | Editar de nuevo | ✅ Permitido |

---

## 💾 Cambios en Backend

### Nueva Función: `_validar_permiso_edicion()`

```python
def _validar_permiso_edicion(
    db: Session,
    prestamo_id: int,
    current_user: Any,
    actor: str,
) -> None:
    """
    Valida permisos de edición según estado y rol del usuario.
    
    Reglas:
    - ✓ REVISADO: Nadie puede editar (solo admin desde BD)
    - ❓ REVISANDO: Solo admin
    - ⚠️ PENDIENTE, ❌ EN ESPERA: Todos
    """
```

### Endpoints Actualizados

```
PUT /revision-manual/clientes/{id}
PUT /revision-manual/prestamos/{id}
PUT /revision-manual/cuotas/{id}
DELETE /revision-manual/prestamos/{id}/cuotas/{id}
PATCH /revision-manual/prestamos/{id}/estado-revision (mejorado)
```

### Validaciones Agregadas

```python
# En cambiar_estado_revision():
- Solo admin puede marcar como "revisado"
- Solo admin puede cambiar de "revisado" a "revisando"
- Se limpia fecha_revision si se regresa de "revisado"
```

---

## 🎨 Cambios en Frontend

### Componente: `EstadoRevisionIcon.tsx`

**Actualizado para mostrar diálogos mejorados:**

```typescript
// Cuando está en ✓ REVISADO:
const opciones = `Este préstamo está REVISADO.

Opciones (solo admin):
1. ❓ REVISANDO - Abrir para que usuario edite de nuevo
2. Cancelar`

// Si usuario no es admin:
// "No clickeable - Solo muestra 'Finalizado'"
```

### Mensajes de Error Mejorados

```typescript
// Error 1: Usuario intenta editar en ❓ REVISANDO
"Este préstamo está en revisión. Solo administradores pueden editar 
 en este estado. Contacta con tu administrador."

// Error 2: Usuario intenta reabrir ✓ REVISADO
"Solo administradores pueden cambiar un préstamo revisado 
 de vuelta a revisión"
```

---

## 🔐 Auditoría Mejorada

Cada cambio registra:

```json
{
  "usuario": "juan@empresa.com",
  "accion": "cambiar_estado_revision",
  "prestamo_id": 123,
  "estado_anterior": "revisando",
  "estado_nuevo": "en_espera",
  "timestamp": "2026-03-31T14:30:00Z",
  "detalles": "Usuario marcó como EN ESPERA - necesita revisión"
}
```

---

## 🎯 Flujos de Trabajo

### Flujo 1: Usuario Intenta Editar (Bloqueado)

```
1. Usuario ve ⚠️ PENDIENTE
2. Click → Cambia a ❓ REVISANDO
3. Usuario intenta editar cliente
4. Sistema: 
   ❌ "Este préstamo está en revisión. 
      Solo administradores pueden editar."
5. Usuario contacta admin
6. Admin hace click → cambia a ❌ EN ESPERA
7. Ahora usuario puede editar nuevamente
```

### Flujo 2: Admin Reabre para Nueva Edición

```
1. Admin finalizó como ✓ REVISADO
2. Más tarde: necesita corregir error
3. Admin hace click en icono ✓
4. Opción: "Reabrir a ❓ REVISANDO"
5. Cambia a ❓ REVISANDO
6. Admin abre editor y edita
7. Admin finaliza de nuevo
```

---

## 🚨 Mensajes de Error Implementados

### HTTPException 403 - Permisos Insuficientes

```
Endpoint: PUT /revision-manual/clientes/{id}
Trigger: Usuario intenta editar en ❓ REVISANDO

Response:
{
  "detail": "Este préstamo está en revisión. Solo administradores 
            pueden editar en este estado. Contacta con tu administrador."
}
```

```
Endpoint: PATCH /revision-manual/prestamos/{id}/estado-revision
Trigger: Usuario intenta cambiar de ✓ → ❓

Response:
{
  "detail": "Solo administradores pueden cambiar un préstamo revisado 
            de vuelta a revisión"
}
```

---

## 📊 Comparación Antes vs Después

### ANTES (Sin control de roles)

```
❓ REVISANDO
  ✅ Cualquiera podía editar
  ✅ Cualquiera podía cambiar estado
  ❌ Posible confusión entre usuarios
  ❌ Sin control administrativo
```

### AHORA (Con control de roles)

```
❓ REVISANDO
  ✅ Solo admin puede editar
  ✅ Solo admin puede cambiar estado
  ✅ Usuarios regulares saben que está en manos de admin
  ✅ Control centralizado
  ✅ Auditoría clara de quién hizo qué
```

---

## ✅ Verificaciones Realizadas

```
✅ TypeScript: 0 errores
✅ Backend: Validaciones implementadas
✅ Frontend: Diálogos actualizados
✅ Auditoría: Cambios registrados
✅ Mensajes: Errores descriptivos
✅ Permisos: Validación en 5 endpoints
```

---

## 🚀 Cómo Probar

### Test 1: Usuario Intenta Editar (Debe Fallar)

```
1. Inicia como usuario regular
2. Ve /pagos/revision-manual
3. Click en ⚠️ PENDIENTE
4. Click en ✎ NO para editar
5. Intenta cambiar nombre del cliente
6. Haz click "Guardar Parciales"
7. Resultado esperado: ❌ Error 403
   "Este préstamo está en revisión..."
```

### Test 2: Admin Puede Editar

```
1. Inicia como admin
2. Ve /pagos/revision-manual
3. Click en ⚠️ PENDIENTE
4. Click en ✎ NO para editar
5. Edita cliente/préstamo/cuotas
6. Resultado esperado: ✅ Se guardan cambios
```

### Test 3: Admin Puede Reabrir

```
1. Inicia como admin
2. Finaliza un préstamo: ✓ REVISADO
3. Click en icono ✓ REVISADO
4. Opción: "Reabrir a ❓ REVISANDO"
5. Resultado esperado: Cambia a ❓ REVISANDO
6. Ahora puede editar de nuevo
```

---

## 📁 Archivos Modificados

```
backend/app/api/v1/endpoints/revision_manual.py
├─ Nueva función: _validar_permiso_edicion()
├─ Actualizada: editar_cliente_revision()
├─ Actualizada: editar_prestamo_revision()
├─ Actualizada: editar_cuota_revision()
├─ Actualizada: eliminar_cuota_revision()
└─ Mejorada: cambiar_estado_revision()

frontend/src/components/revision_manual/EstadoRevisionIcon.tsx
├─ Actualizada: handleShowDialog()
├─ Mejorados: Diálogos para admin
└─ Mejorados: Mensajes de error
```

---

## 📚 Documentación Creada

```
REGLAS_PERMISOS_REVISION_MANUAL.md
├─ Matriz de permisos
├─ Flujos de uso
├─ Mensajes de error
├─ Casos de uso prácticos
└─ Entrenamientos recomendados
```

---

## 🎓 Para Capacitar a Usuarios

### Usuarios Regulares
- "Solo pueden editar en ⚠️ y ❌ estados"
- "Si está en ❓, espera a que admin lo cambie"
- "Contactar a admin si está bloqueado"

### Administradores
- "Control total en cualquier estado"
- "Pueden reabrir ✓ REVISADO para nueva edición"
- "Responsables de autorizar cambios críticos"

---

## 🏁 Estado Final

**✅ COMPLETADO**

- Validación de permisos en backend
- Diálogos mejorados en frontend
- Mensajes de error descriptivos
- Auditoría de cambios
- TypeScript 100% verificado
- Documentación completa

---

**Actualización**: 31-03-2026  
**Versión**: 2.0 (Control de Permisos)  
**Estado**: ✅ LISTO PARA PRODUCCIÓN
