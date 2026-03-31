# 🎯 Sistema de Estados de Revisión Manual - Guía de Usuario

## Descripción General

El sistema de Revisión Manual ahora tiene un **indicador visual de estados clickeable** que permite a los usuarios gestionar el progreso de la revisión de cada préstamo de forma intuitiva.

## 📊 Estados y Transiciones

### 1. **⚠️ PENDIENTE** (No iniciado)
- **Icono**: Triángulo de advertencia (amarillo)
- **Color**: Amarillo/Ámbar (#FCD34D)
- **Significado**: El préstamo NO ha sido revisado aún
- **Acción clickeable**: Cambiar a "Revisando"
- **Siguiente estado**: ❓ Revisando

```
⚠️ PENDIENTE
    ↓
 (Click para iniciar)
    ↓
❓ REVISANDO
```

---

### 2. **❓ REVISANDO** (En análisis)
- **Icono**: Signo de interrogación (azul)
- **Color**: Azul (#3B82F6)
- **Significado**: El usuario está analizando el préstamo, puede guardar cambios parciales
- **Acción clickeable**: Abre diálogo para elegir siguiente estado
- **Opciones disponibles**:
  - Cambiar a "En Espera" (❌)
  - Cambiar a "Revisado" (✓) - solo admin
  - Cancelar

```
❓ REVISANDO
    ↓ (Click)
    ├─→ ❌ EN ESPERA (Necesita más revisión)
    ├─→ ✓ REVISADO (Finalizar, solo admin)
    └─→ Cancelar (mantener revisando)
```

---

### 3. **❌ EN ESPERA** (Requiere más revisión)
- **Icono**: X roja (rojo)
- **Color**: Rojo (#EF4444)
- **Significado**: Se encontraron errores o inconsistencias que requieren más análisis
- **Comportamiento**:
  - ❌ **NO guarda cambios automáticamente**
  - Solo marca que hay **atención máxima requerida**
  - El usuario debe regresar a este préstamo
  - Permite regresa a "Revisando" para continuar editando
- **Acción clickeable**: Abre diálogo para elegir siguiente estado
- **Opciones disponibles**:
  - Cambiar a "Revisando" (❓) - para continuar análisis
  - Cambiar a "Revisado" (✓) - si se resolvieron los problemas (solo admin)
  - Cancelar (mantener en espera)

```
❌ EN ESPERA
    ↓ (Click)
    ├─→ ❓ REVISANDO (Continuar análisis)
    ├─→ ✓ REVISADO (Finalizar, solo admin)
    └─→ Cancelar (mantener en espera)
```

---

### 4. **✓ REVISADO** (Finalizado)
- **Icono**: Check/Visto (verde)
- **Color**: Verde (#10B981)
- **Significado**: La revisión se completó, todos los cambios se guardaron en tablas originales
- **Acción**: 
  - ❌ **NO es clickeable**
  - **INMUTABLE**: No se puede revertir (solo admin puede hacer esto desde BD)
  - Todos los cambios ya están guardados
  - El usuario NO puede editar más este préstamo

```
✓ REVISADO
(Finalizado - No hay más transiciones)
```

---

## 🔄 Flujos de Trabajo Típicos

### Flujo A: Revisión Exitosa (Sin Errores)
```
⚠️ PENDIENTE
    ↓ (Click)
❓ REVISANDO
    ├─ Usuario edita cliente, préstamo y cuotas
    ├─ Guarda cambios parciales si es necesario
    ↓ (Click cuando termina)
✓ REVISADO (Todos los cambios se guardan)
```

### Flujo B: Revisión con Errores (Requiere Iteración)
```
⚠️ PENDIENTE
    ↓ (Click)
❓ REVISANDO
    ├─ Usuario encuentra inconsistencias
    ↓ (Click → "En Espera")
❌ EN ESPERA (Marca para revisión posterior)
    ├─ Usuario regresa más tarde
    ↓ (Click → "Revisando")
❓ REVISANDO (Continúa análisis)
    ├─ Usuario corrige los problemas
    ↓ (Click → "Revisado")
✓ REVISADO (Se guardan cambios corregidos)
```

### Flujo C: Revisión Incompleta
```
⚠️ PENDIENTE
    ↓ (Click)
❓ REVISANDO
    ├─ Usuario guarda cambios parciales
    ├─ Se va (sin marcar como revisado)
    ↓ (Al volver a la lista)
❓ REVISANDO (Estado se mantiene)
    ├─ Puede continuar desde donde paró
```

---

## 💾 Reglas de Guardado de Datos

| Estado | Guardar Cambios | Tabla Destino | Descripción |
|--------|-----------------|---------------|-------------|
| **⚠️ Pendiente** | N/A | - | Sin cambios aún |
| **❓ Revisando** | ✅ Sí (parciales) | Tablas temporales | Usuario puede guardar parciales |
| **❌ En Espera** | ❌ No automático | - | Solo marca estado, sin guardado |
| **✓ Revisado** | ✅ Sí (todos) | Tablas originales | Guardar automaticamente al finalizar |

---

## 👥 Permisos por Rol

### Usuario Regular (Revisor)
- ✅ Puede cambiar de ⚠️ → ❓ (iniciar)
- ✅ Puede cambiar ❓ ↔ ❌ (iteración)
- ✅ Puede guardar cambios parciales en ❓
- ❌ NO puede marcar como ✓ (solo admin)

### Administrador
- ✅ Todas las transiciones de usuario regular
- ✅ Puede marcar como ✓ REVISADO (finalizar)
- ✅ Puede acceder a reportes de auditoría
- ✅ Puede cambiar estado manualmente desde BD si es necesario

---

## 🎬 Acciones en Cada Estado

### Cuando ves ⚠️ PENDIENTE
```
1. Click en el ícono
2. Aparece confirmación: "¿Iniciar revisión?"
3. Si confirmas → cambia a ❓ REVISANDO
4. Si cancelas → se mantiene en ⚠️ PENDIENTE
```

### Cuando ves ❓ REVISANDO
```
1. Edita cliente, préstamo, cuotas
2. Haz clic en "Guardar Parciales" para guardar cambios intermedios
3. Click en el ícono para cambiar estado:
   - Opción 1: Marcar como ❌ EN ESPERA (si hay problemas)
   - Opción 2: Marcar como ✓ REVISADO (si terminó, requiere admin)
   - Opción 3: Cancelar (mantener revisando)
4. Botón "Guardar y Cerrar" guarda TODO y marca como ✓ REVISADO
```

### Cuando ves ❌ EN ESPERA
```
1. Indica que hay problemas encontrados
2. Requiere atención y revisión adicional
3. Click en el ícono:
   - Opción 1: Volver a ❓ REVISANDO (para continuar análisis)
   - Opción 2: Marcar como ✓ REVISADO (si se resolvieron, solo admin)
   - Opción 3: Cancelar (mantener en espera)
```

### Cuando ves ✓ REVISADO
```
1. El préstamo está completamente revisado
2. Todos los cambios fueron guardados
3. Ya NO se puede editar este préstamo
4. Aparece etiqueta "Finalizado" (no clickeable)
```

---

## 📝 Ejemplos Prácticos

### Ejemplo 1: Juan revisa un préstamo correctamente
```
1. Juan ve "⚠️ PENDIENTE" en la lista
2. Click en el ícono → se abre editor
3. Revisa datos del cliente, préstamo y cuotas
4. Todo está OK → Click "Guardar y Cerrar"
5. Sistema guarda cambios y marca como "✓ REVISADO"
6. Juan no puede editar de nuevo este préstamo
```

### Ejemplo 2: María encuentra inconsistencias
```
1. María ve "⚠️ PENDIENTE"
2. Click → estado cambia a "❓ REVISANDO"
3. María edita y encuentra que hay cuotas faltantes
4. Click en ícono de estado → elige "❌ EN ESPERA"
5. Sistema marca el préstamo para revisión posterior
6. María regresa al día siguiente
7. Click en "❌ EN ESPERA" → vuelve a "❓ REVISANDO"
8. Agrega cuotas faltantes
9. Click "Guardar y Cerrar" → "✓ REVISADO"
```

### Ejemplo 3: Carlos guarda cambios parciales
```
1. Carlos inicia revisión (⚠️ → ❓)
2. Edita datos del cliente
3. Click "Guardar Parciales" (datos se guardan temporalmente)
4. Se cierra y va a revisar otro préstamo
5. Al volver al de Carlos, aún está en "❓ REVISANDO"
6. Puede continuar desde donde paró
7. Completa la revisión y marca "✓ REVISADO"
```

---

## ⚙️ Flujo Técnico (Backend)

### Estado: ⚠️ PENDIENTE
```
GET /api/v1/revision-manual/prestamos
→ Filtra con estado_revision = "pendiente"
```

### Cambiar a ❓ REVISANDO
```
PATCH /api/v1/revision-manual/prestamos/{id}/estado-revision
Body: { "nuevo_estado": "revisando", "observaciones": null }
→ Actualiza revision_manual_prestamos.estado_revision = "revisando"
→ Registra en registro_cambios (auditoría)
```

### Cambiar a ❌ EN ESPERA
```
PATCH /api/v1/revision-manual/prestamos/{id}/estado-revision
Body: { 
  "nuevo_estado": "en_espera",
  "observaciones": "Faltan 3 cuotas por verificar"
}
→ Actualiza estado
→ Guarda observaciones
→ No guarda cambios del préstamo
```

### Cambiar a ✓ REVISADO (Solo Admin)
```
PATCH /api/v1/revision-manual/prestamos/{id}/estado-revision
Body: { "nuevo_estado": "revisado", "observaciones": null }
→ Guarda TODOS los cambios en tablas originales
→ Marca fecha_revision = NOW()
→ Registra usuario_revision_id
→ Registra en auditoría
→ Bloquea edición futura
```

---

## 🔒 Seguridad y Auditoría

- ✅ Cada cambio de estado se registra en `registro_cambios`
- ✅ Se registra quién hizo el cambio (usuario_revision_email)
- ✅ Se registra cuándo (fecha_revision, actualizado_en)
- ✅ Solo admin puede finalizar con ✓ REVISADO
- ✅ Los cambios son append-only (no se pueden borrar del historial)

---

## 📱 Iconografía Visual

| Estado | Icono | Color | Hover |
|--------|-------|-------|-------|
| ⚠️ Pendiente | `AlertTriangle` | Amarillo | Más oscuro + cursor pointer |
| ❓ Revisando | `HelpCircle` | Azul | Más oscuro + cursor pointer |
| ❌ En Espera | `X` | Rojo | Más oscuro + cursor pointer |
| ✓ Revisado | `CheckCircle` | Verde | Sin cambio (no clickeable) |

---

## ❓ Preguntas Frecuentes

**P: ¿Qué pasa si dejo un préstamo en "Revisando" y nunca lo termino?**  
R: Se queda en "Revisando" hasta que lo termines o cambies el estado manualmente.

**P: ¿Puedo deshacer un "Revisado"?**  
R: No, solo un administrador desde la base de datos. Por eso hay confirmación antes.

**P: Si marco como "En Espera", ¿se pierden mis cambios?**  
R: No. Los cambios parciales que guardaste se mantienen. Solo indica que necesita más revisión.

**P: ¿Puedo cambiar entre "Revisando" y "En Espera" varias veces?**  
R: Sí, sin límite. Hasta que marques como "Revisado".

**P: ¿Quién puede ver qué préstamos están en cada estado?**  
R: Todos pueden ver la lista, pero solo admin puede finalizar (marcar como "Revisado").

---

## 🚀 Siguientes Pasos

1. Ejecutar migración SQL: `039_AGREGAR_ESTADO_EN_ESPERA_REVISION_MANUAL.sql`
2. Reiniciar backend
3. Actualizar frontend con los cambios
4. Probar el flujo completo
5. Entrenar a usuarios sobre los nuevos estados

---

**Documento actualizado**: 31-03-2026  
**Versión**: 1.0  
**Estado**: Listo para producción
