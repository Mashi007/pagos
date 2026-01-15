# 🔧 Análisis: Herramienta para Entrenar Palabras

**Fecha:** 2025-01-XX  
**Sistema:** RAPICREDIT - Chat AI

---

## ❌ Estado Actual: NO Existe Herramienta de UI

### **Lo que SÍ existe:**

1. **Mapeo Semántico Hardcodeado**
   - Ubicación: `backend/app/api/v1/endpoints/configuracion.py`
   - Función: `_obtener_mapeo_semantico_campos()` (línea ~5352)
   - Estado: ✅ Funcional pero estático (requiere cambios en código)

2. **Variables Personalizadas del Prompt**
   - Ubicación: `backend/app/models/ai_prompt_variable.py`
   - Tabla: `ai_prompt_variables`
   - Propósito: Placeholders en el prompt (ej: `{mi_variable}`)
   - Estado: ✅ Funcional pero NO es para sinónimos

---

## ⚠️ Limitación Actual

**El mapeo de palabras comunes está hardcodeado** en el código Python:

```python
# Ejemplo del código actual:
mapeo.append("  • cedula, cédula, documento, documento identidad, DNI, CI, identificación")
mapeo.append("  • nombres, nombre, nombre completo, cliente, persona, titular")
mapeo.append("  • pago, pagos, transacción, abono, depósito, transferencia")
```

**Para agregar nuevas palabras, necesitas:**
1. Modificar el código fuente
2. Hacer deploy del backend
3. Reiniciar el servidor

**NO hay una interfaz web** para que los administradores agreguen sinónimos dinámicamente.

---

## ✅ Propuesta: Crear Herramienta de Entrenamiento de Palabras

### **Funcionalidad Propuesta:**

#### **1. Modelo de Base de Datos**

```python
# Nuevo modelo: backend/app/models/ai_sinonimo.py
class AISinonimo(Base):
    __tablename__ = "ai_sinonimos"
    
    id = Column(Integer, primary_key=True)
    campo_tecnico = Column(String(100), nullable=False)  # Ej: "cedula"
    sinonimos = Column(Text, nullable=False)  # JSON: ["cédula", "documento", "DNI", "CI"]
    categoria = Column(String(50))  # Ej: "identificacion", "pagos", "prestamos"
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, onupdate=func.now())
```

#### **2. Endpoints Backend**

```python
# Nuevos endpoints en configuracion.py:
POST   /api/v1/configuracion/ai/sinonimos          # Crear sinónimo
GET    /api/v1/configuracion/ai/sinonimos           # Listar sinónimos
PUT    /api/v1/configuracion/ai/sinonimos/{id}      # Actualizar sinónimo
DELETE /api/v1/configuracion/ai/sinonimos/{id}      # Eliminar sinónimo
GET    /api/v1/configuracion/ai/sinonimos/categorias # Listar categorías
```

#### **3. Componente Frontend**

**Ubicación:** `frontend/src/components/configuracion/SinonimosTab.tsx`

**Funcionalidades:**
- ✅ Listar sinónimos existentes por categoría
- ✅ Agregar nuevo sinónimo (campo técnico + lista de sinónimos)
- ✅ Editar sinónimos existentes
- ✅ Eliminar sinónimos
- ✅ Activar/desactivar sinónimos
- ✅ Buscar sinónimos por campo técnico o palabra

#### **4. Integración con Mapeo Semántico**

**Modificar función `_obtener_mapeo_semantico_campos()`:**

```python
def _obtener_mapeo_semantico_campos(db: Session = None) -> str:
    """Genera mapeo semántico combinando hardcodeado + BD"""
    mapeo = []
    
    # Mapeo hardcodeado (base)
    mapeo_base = _obtener_mapeo_semantico_base()
    mapeo.append(mapeo_base)
    
    # Mapeo desde BD (sinónimos personalizados)
    if db:
        sinonimos_bd = db.query(AISinonimo).filter(AISinonimo.activo == True).all()
        if sinonimos_bd:
            mapeo.append("\n=== SINÓNIMOS PERSONALIZADOS ===")
            for sin in sinonimos_bd:
                sinonimos_list = json.loads(sin.sinonimos)
                mapeo.append(f"  • {sin.campo_tecnico}: {', '.join(sinonimos_list)}")
    
    return "\n".join(mapeo)
```

---

## 📋 Estructura Propuesta de la Herramienta

### **Interfaz de Usuario:**

```
┌─────────────────────────────────────────────────────────┐
│ 🔤 Gestión de Sinónimos y Palabras Comunes             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Categoría: [Todas ▼]  Buscar: [________]  [+ Agregar] │
│                                                         │
│ ┌───────────────────────────────────────────────────┐  │
│ │ 👤 IDENTIFICACIÓN DE CLIENTES                     │  │
│ ├───────────────────────────────────────────────────┤  │
│ │ Campo: cedula                                     │  │
│ │ Sinónimos: cédula, documento, DNI, CI, identif...│  │
│ │ [✏️ Editar] [🗑️ Eliminar] [✅ Activo]            │  │
│ │                                                   │  │
│ │ Campo: nombres                                    │  │
│ │ Sinónimos: nombre, nombre completo, cliente...   │  │
│ │ [✏️ Editar] [🗑️ Eliminar] [✅ Activo]            │  │
│ └───────────────────────────────────────────────────┘  │
│                                                         │
│ ┌───────────────────────────────────────────────────┐  │
│ │ 💳 PAGOS Y TRANSACCIONES                          │  │
│ ├───────────────────────────────────────────────────┤  │
│ │ Campo: pago                                       │  │
│ │ Sinónimos: pagos, transacción, abono, depósito...│  │
│ │ [✏️ Editar] [🗑️ Eliminar] [✅ Activo]            │  │
│ └───────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### **Formulario de Agregar/Editar:**

```
┌─────────────────────────────────────────┐
│ ✏️ Agregar Sinónimo                     │
├─────────────────────────────────────────┤
│ Campo Técnico: [cedula________]         │
│                                         │
│ Categoría: [Identificación ▼]          │
│                                         │
│ Sinónimos (uno por línea):             │
│ ┌─────────────────────────────────────┐│
│ │ cédula                               ││
│ │ documento                            ││
│ │ DNI                                  ││
│ │ CI                                   ││
│ │ identificación                       ││
│ │                                      ││
│ └─────────────────────────────────────┘│
│                                         │
│ [Cancelar]  [Guardar]                  │
└─────────────────────────────────────────┘
```

---

## 🎯 Beneficios de la Herramienta

### **Para Administradores:**
- ✅ Agregar sinónimos sin modificar código
- ✅ Probar cambios inmediatamente
- ✅ Ver todos los sinónimos en un lugar
- ✅ Activar/desactivar sinónimos sin deploy

### **Para el Sistema:**
- ✅ Mapeo dinámico desde BD
- ✅ Sin necesidad de reiniciar servidor
- ✅ Historial de cambios (auditoría)
- ✅ Compatibilidad con mapeo hardcodeado existente

---

## 📊 Comparación: Actual vs Propuesta

| Característica | Actual (Hardcodeado) | Propuesta (BD) |
|----------------|----------------------|----------------|
| **Agregar sinónimo** | Modificar código + Deploy | Interfaz web |
| **Tiempo de cambio** | Minutos/horas | Segundos |
| **Requiere reinicio** | ✅ Sí | ❌ No |
| **Acceso** | Solo desarrolladores | Administradores |
| **Historial** | Git commits | Tabla BD |
| **Pruebas** | Deploy completo | Inmediato |

---

## 🚀 Plan de Implementación

### **Fase 1: Backend (Base)**
1. ✅ Crear modelo `AISinonimo`
2. ✅ Crear migración de BD
3. ✅ Crear endpoints CRUD
4. ✅ Modificar `_obtener_mapeo_semantico_campos()` para incluir BD

### **Fase 2: Frontend**
1. ✅ Crear componente `SinonimosTab.tsx`
2. ✅ Integrar en `AIConfig.tsx`
3. ✅ Agregar validaciones y feedback

### **Fase 3: Migración de Datos**
1. ✅ Script para migrar mapeo hardcodeado a BD
2. ✅ Mantener mapeo hardcodeado como fallback

### **Fase 4: Testing**
1. ✅ Probar agregar/editar/eliminar sinónimos
2. ✅ Verificar que el AI usa los nuevos sinónimos
3. ✅ Probar activar/desactivar sinónimos

---

## ⚠️ Consideraciones

### **Compatibilidad:**
- Mantener mapeo hardcodeado como base
- Sinónimos de BD se agregan al mapeo existente
- Si BD falla, usar solo mapeo hardcodeado

### **Validación:**
- Campo técnico debe existir en BD
- Sinónimos no pueden duplicarse
- Validar formato de sinónimos

### **Performance:**
- Cachear sinónimos en memoria
- Invalidar cache al actualizar
- Cargar sinónimos al iniciar servidor

---

## ✅ Conclusión

**Estado Actual:** ❌ **NO existe herramienta de UI para entrenar palabras**

**Solución Propuesta:** ✅ **Crear herramienta completa de gestión de sinónimos**

**Beneficios:**
- Administradores pueden agregar sinónimos sin código
- Cambios inmediatos sin deploy
- Mejor mantenibilidad
- Historial y auditoría

---

## 📝 Próximos Pasos

1. **Decisión:** ¿Implementar la herramienta propuesta?
2. **Prioridad:** ¿Es urgente o puede esperar?
3. **Alcance:** ¿Solo sinónimos o también otros tipos de entrenamiento?
