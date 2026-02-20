# MENSAJES DE ADVERTENCIA - SISTEMA DE REVISIÓN MANUAL

## 📋 Resumen Ejecutivo
Sistema de alertas **COMPLETO** en todos los botones críticos de revisión manual. Previene acciones accidentales.

---

## 🎯 MENSAJES POR ACCIÓN

### **1. LISTA PRINCIPAL - Botón "¿Sí?" (Confirmar TODO)**

**Trigger**: Click en botón ✓ Sí

**Mensaje de Confirmación**:
```
⚠️ CONFIRMAR REVISIÓN - {NOMBRE_CLIENTE}

✓ Se marcarán TODOS los datos como correctos:
  - Datos del cliente
  - Datos del préstamo
  - Cuotas y pagos

✓ El préstamo desaparecerá de esta lista
✓ NO PODRÁS EDITAR ESTE PRÉSTAMO DE NUEVO

¿Confirmas que todo está correcto?
```

**Si cancela**:
```
ℹ️ Confirmación cancelada
```

**Si confirma**:
```
✅ Usted ha auditado todos los términos de este préstamo por lo que no podrá editar de nuevo
```

**Si hay error**:
```
❌ [Mensaje de error específico]
```

---

### **2. LISTA PRINCIPAL - Botón "¿No?" (Iniciar Edición)**

**Trigger**: Click en botón ✎ No

**Mensaje de Confirmación**:
```
⚠️ INICIAR EDICIÓN

Al presionar "No", accederás a la interfaz de edición donde podrás:
✓ Editar datos del cliente
✓ Editar datos del préstamo
✓ Editar cuotas y pagos

✓ Puedes guardar cambios parciales (Guardar Parciales)
✓ O finalizar la revisión (Guardar y Cerrar)

¿Deseas continuar?
```

**Si cancela**:
```
ℹ️ Edición cancelada
```

**Si confirma**:
```
ℹ️ Edición iniciada. Abriendo editor...
```

**Si hay error**:
```
❌ [Mensaje de error específico]
```

---

### **3. PÁGINA DE EDICIÓN - Botón Cerrar (ArrowLeft)**

**Trigger**: Click en botón ← del header

**Validación**: Si hay cambios sin guardar...

**Mensaje de Confirmación**:
```
⚠️ Tienes cambios sin guardar.

Si cierras ahora, se perderán todos los cambios realizados.
¿Estás seguro de que deseas cerrar sin guardar?
```

**Si cancela**: Permanece en página de edición

**Si confirma**: Vuelve a `/prestamos` (pierde cambios)

---

### **4. PÁGINA DE EDICIÓN - Botón "Guardar Parciales"**

**Trigger**: Click en botón [Guardar Parciales]

**Validación 1**: Si no hay cambios...
```
ℹ️ No hay cambios para guardar
```

**Validación 2**: Si hay errores en guardado...
```
❌ Error en cliente: [detalle específico]
```
o
```
❌ Error en préstamo: [detalle específico]
```
o
```
❌ Error en cuota #{numero}: [detalle específico]
```

**Si guardó correctamente**:
```
✅ Cambios parciales guardados en BD
```

**Si guardó parcialmente**:
```
⚠️ Algunos cambios no se guardaron. Revisa los errores arriba
```

---

### **5. PÁGINA DE EDICIÓN - Botón "Guardar y Cerrar"**

**Trigger**: Click en botón [Guardar y Cerrar]

**Mensaje de Confirmación** (CRÍTICO):
```
⚠️ CONFIRMAR FINALIZACIÓN DE REVISIÓN

✓ Se guardarán todos los cambios pendientes
✓ El préstamo se marcará como REVISADO
✓ NO PODRÁS EDITAR ESTE PRÉSTAMO DE NUEVO

¿Estás completamente seguro?
```

**Si cancela**:
```
ℹ️ Finalización cancelada
```

**Si confirma y tiene éxito**:
```
✅ Usted ha auditado todos los términos de este préstamo por lo que no podrá editar de nuevo
```
(Sistema espera 1.5 segundos antes de volver a `/prestamos`)

**Si hay error en cliente**:
```
❌ Error en cliente: [detalle específico]
```

**Si hay error en préstamo**:
```
❌ Error en préstamo: [detalle específico]
```

**Si hay error en cuota**:
```
❌ Error en cuota #{numero}: [detalle específico]
```

**Si hay error al finalizar**:
```
❌ Error al finalizar: [detalle específico]
```

---

### **6. PÁGINA DE EDICIÓN - Botón "Cerrar sin guardar"**

**Trigger**: Click en botón [Cerrar sin guardar]

**Validación**: Si hay cambios sin guardar...

**Mensaje de Confirmación**:
```
⚠️ Tienes cambios sin guardar.

Si cierras ahora, se perderán todos los cambios realizados.
¿Estás seguro de que deseas cerrar sin guardar?
```

**Si cancela**: Permanece en página de edición

**Si confirma**: Vuelve a `/prestamos` (pierde cambios)

---

## 🎨 TIPOS DE MENSAJES

### **Confirmación** (⚠️)
- Pregunta importante al usuario
- Requiere acción: [Aceptar] [Cancelar]
- Riesgo medio/alto (cambios irreversibles)

### **Informativo** (ℹ️)
- Solo informa, no requiere acción
- Se auto-cierra después de 3 segundos
- Riesgo bajo

### **Éxito** (✅)
- Confirma que acción se completó
- Color verde
- Duración: 2 segundos

### **Error** (❌)
- Indica fallo en la operación
- Color rojo
- Muestra detalle del error
- No se auto-cierra

---

## 🔄 FLUJOS COMPLETOS

### **Flujo 1: Confirmar TODO (¿Sí?)**
```
Lista → Click ✓Sí
    ↓
Confirmar revisión ⚠️
    ↓
[Aceptar]
    ↓
✅ Auditado completamente
    ↓
Préstamo desaparece de lista (estado: revisado)
```

### **Flujo 2: Editar (¿No?)**
```
Lista → Click ✎No
    ↓
Confirmar edición ⚠️
    ↓
[Aceptar]
    ↓
ℹ️ Edición iniciada
    ↓
Navega a /revision-manual/editar/{id}
    ↓
Estado: revisando
```

### **Flujo 3: Cerrar sin guardar (desde header ←)**
```
Editor → Click ←
    ↓
¿Hay cambios sin guardar? SÍ
    ↓
⚠️ Confirmar cierre
    ↓
[Aceptar]
    ↓
Vuelve a /prestamos
    ↓
Cambios PERDIDOS
```

### **Flujo 4: Guardar y Cerrar**
```
Editor → Click [Guardar y Cerrar]
    ↓
⚠️ Confirmar finalización (CRÍTICO)
    ↓
[Aceptar]
    ↓
Guardar cliente/préstamo/cuotas
    ↓
✅ Auditado completamente
    ↓
Estado: revisado
    ↓
Vuelve a /prestamos (después 1.5s)
```

### **Flujo 5: Guardar Parciales**
```
Editor → Click [Guardar Parciales]
    ↓
¿Hay cambios? NO
    ↓
ℹ️ No hay cambios para guardar
```

O:

```
Editor → Click [Guardar Parciales]
    ↓
¿Hay cambios? SÍ
    ↓
Guardar cliente/préstamo/cuotas
    ↓
✅ Cambios parciales guardados en BD
    ↓
Estado: revisando (MANTIENE)
```

---

## 📊 TABLA DE MENSAJES

| Botón | Acción | Confirmación | Éxito | Error | Auto-cierre |
|-------|--------|--------------|-------|-------|-------------|
| ✓Sí | Confirmar TODO | ⚠️ | ✅ | ❌ | No (cambios irreversibles) |
| ✎No | Editar | ⚠️ | ℹ️ | ❌ | No |
| ← | Cerrar | ⚠️ (si hay cambios) | - | - | No |
| Guardar Parciales | Guardar cambios | - | ✅ | ❌ | Sí (3s) |
| Guardar y Cerrar | Finalizar | ⚠️ | ✅ | ❌ | No (espera 1.5s) |
| Cerrar sin guardar | Cerrar | ⚠️ (si hay cambios) | - | - | No |

---

## 🔐 Principios de Seguridad

✅ **Confirmaciones en acciones irreversibles**
- Confirmar TODO
- Guardar y Cerrar
- Cerrar con cambios

✅ **Validaciones antes de guardado**
- Verificar campos vacíos
- Validar rangos de números
- Validar formatos de fecha

✅ **Errores específicos**
- No genéricos ("Error")
- Indicar qué campo falló
- Mostrar por qué falló

✅ **Prevención de pérdida de datos**
- Advertir si hay cambios sin guardar
- Delay antes de cerrar
- Mensajes claros de consecuencias

---

## 📋 Checklist de Implementación

- ✅ Confirmación en ¿Sí? (Confirmar TODO)
- ✅ Confirmación en ¿No? (Iniciar edición)
- ✅ Confirmación en Cerrar (← header)
- ✅ Validación en Guardar Parciales
- ✅ Confirmación en Guardar y Cerrar (CRÍTICA)
- ✅ Confirmación en Cerrar sin guardar
- ✅ Errores específicos por campo
- ✅ Mensajes informativos claros
- ✅ Tooltips en botones
- ✅ Auto-cierre de toasts de éxito

---

Documento: MENSAJES_ADVERTENCIA_REVISION_MANUAL.md  
Fecha: 2026-02-20  
Estado: ✅ Implementado y funcional
