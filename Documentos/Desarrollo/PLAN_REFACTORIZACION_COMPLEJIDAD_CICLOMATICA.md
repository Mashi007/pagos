# 📋 Plan de Refactorización: Complejidad Ciclomática (C901)

## 📊 Resumen Ejecutivo

**Total de funciones con complejidad alta:** 110  
**Límite configurado:** 10  
**Estado:** No crítico (advertencias, no errores)  
**Prioridad:** Media-Alta (mejora mantenibilidad y testabilidad)

---

## 🎯 Objetivos

1. **Reducir complejidad ciclomática** de funciones críticas a < 10
2. **Mejorar mantenibilidad** del código
3. **Facilitar testing** unitario
4. **Aumentar legibilidad** del código
5. **Prevenir bugs** futuros

---

## 📈 Estrategias de Refactorización

### 1. **Extracción de Funciones (Extract Method)**
- Dividir funciones largas en funciones más pequeñas y específicas
- Cada función debe tener una responsabilidad única

### 2. **Extracción de Clases (Extract Class)**
- Agrupar funciones relacionadas en clases de servicio
- Separar lógica de negocio de lógica de presentación

### 3. **Eliminación de Condiciones Anidadas**
- Usar guard clauses (early returns)
- Aplicar patrón Strategy para múltiples if/else

### 4. **Uso de Polimorfismo**
- Reemplazar switch/case o múltiples if/else con polimorfismo
- Implementar patrón Command para operaciones complejas

### 5. **Simplificación de Lógica Booleana**
- Extraer condiciones complejas a funciones con nombres descriptivos
- Usar variables intermedias para claridad

---

## 🔥 Funciones Críticas (Prioridad Alta)

### **Complejidad > 40** (Refactorización Urgente)

#### 1. `configuracion.py:5495` - `chat_ai` (Complejidad: 91)
**Problema:** Función extremadamente compleja que maneja múltiples responsabilidades  
**Estrategia:**
- Extraer lógica de construcción de prompts a `_build_ai_prompt()`
- Separar lógica de búsqueda de contexto a `_get_context_from_documents()`
- Crear clase `AIChatService` para encapsular toda la lógica
- Extraer validaciones a funciones separadas

**Archivo:** `backend/app/api/v1/endpoints/configuracion.py`

#### 2. `ai_training.py:1092` - `entrenar_modelo_riesgo` (Complejidad: 44)
**Problema:** Lógica de entrenamiento ML mezclada con validaciones y logging  
**Estrategia:**
- Extraer validación de datos a `_validate_training_data()`
- Separar extracción de features a `_extract_features()`
- Crear método `_train_model()` para la lógica de entrenamiento
- Extraer logging y métricas a funciones helper

**Archivo:** `backend/app/api/v1/endpoints/ai_training.py`

#### 3. `ai_training.py:1728` - `entrenar_modelo_impago` (Complejidad: 44)
**Problema:** Similar a `entrenar_modelo_riesgo`  
**Estrategia:** Aplicar misma estrategia que modelo de riesgo

**Archivo:** `backend/app/api/v1/endpoints/ai_training.py`

#### 4. `cache.py:94` - `TryExcept block` (Complejidad: 44)
**Problema:** Bloque try/except con múltiples condiciones anidadas  
**Estrategia:**
- Extraer inicialización de Redis a función `_initialize_redis()`
- Separar manejo de errores a funciones específicas
- Usar guard clauses para validaciones tempranas

**Archivo:** `backend/app/core/cache.py`

#### 5. `configuracion.py:2956` - `procesar_documento_ai` (Complejidad: 49)
**Problema:** Procesamiento de documentos con múltiples formatos y validaciones  
**Estrategia:**
- Crear clase `DocumentProcessor` con métodos específicos por tipo
- Extraer extracción de texto a `_extract_text_by_type()`
- Separar generación de embeddings a `_generate_embeddings()`
- Extraer validaciones a `_validate_document()`

**Archivo:** `backend/app/api/v1/endpoints/configuracion.py`

---

## ⚠️ Funciones Importantes (Prioridad Media)

### **Complejidad 20-40** (Refactorización Recomendada)

#### 6. `dashboard.py:1369` - `dashboard_administrador` (Complejidad: 77)
**Estrategia:**
- Extraer cálculo de KPIs a `_calculate_kpis()`
- Separar obtención de datos por módulo a funciones específicas
- Crear clase `DashboardDataAggregator`

#### 7. `auditoria.py:597` - `estadisticas_auditoria` (Complejidad: 70)
**Estrategia:**
- Extraer consultas SQL a funciones separadas
- Crear clase `AuditStatisticsService`
- Separar cálculos de estadísticas por tipo

#### 8. `dashboard.py:4559` - `obtener_financiamiento_tendencia_mensual` (Complejidad: 59)
**Estrategia:**
- Extraer lógica de cálculo de tendencias
- Separar procesamiento de datos históricos
- Crear helper functions para cálculos estadísticos

#### 9. `configuracion.py:2603` - `_extraer_texto_documento` (Complejidad: 33)
**Estrategia:**
- Usar patrón Strategy para diferentes tipos de documentos
- Crear extractores específicos por tipo (PDF, DOCX, TXT)
- Extraer validaciones a funciones separadas

#### 10. `configuracion.py:2778` - `crear_documento_ai` (Complejidad: 25)
**Estrategia:**
- Separar validación de archivo
- Extraer procesamiento a función `_process_document()`
- Separar guardado en BD

---

## 📝 Funciones Menores (Prioridad Baja)

### **Complejidad 11-20** (Mejoras Incrementales)

Estas funciones pueden mejorarse gradualmente durante el desarrollo normal:

- `listar_fine_tuning_jobs` (12)
- `obtener_clientes_atrasados` (22)
- `enviar_notificacion` (23)
- `_obtener_resumen_bd` (23)
- `listar_conversaciones_whatsapp` (24)
- `obtener_cobranzas_mensuales` (24)
- `obtener_cobranzas_semanales` (32)
- `_procesar_distribucion_rango_monto` (31)
- Y otras 90+ funciones...

**Estrategia General:**
- Aplicar extracción de funciones durante mantenimiento
- Usar guard clauses donde sea posible
- Simplificar condiciones booleanas complejas

---

## 🗓️ Plan de Implementación

### **Fase 1: Análisis y Preparación** (Semana 1-2)
- [ ] Crear tests unitarios para funciones críticas antes de refactorizar
- [ ] Documentar comportamiento actual de funciones complejas
- [ ] Identificar dependencias entre funciones
- [ ] Establecer métricas de éxito (cobertura de tests, reducción de complejidad)

### **Fase 2: Refactorización Crítica** (Semana 3-6)
- [ ] Refactorizar `chat_ai` (complejidad 91 → < 15)
- [ ] Refactorizar `entrenar_modelo_riesgo` (44 → < 15)
- [ ] Refactorizar `entrenar_modelo_impago` (44 → < 15)
- [ ] Refactorizar `procesar_documento_ai` (49 → < 15)
- [ ] Refactorizar bloque try/except en `cache.py` (44 → < 15)

### **Fase 3: Refactorización Importante** (Semana 7-10)
- [ ] Refactorizar `dashboard_administrador` (77 → < 20)
- [ ] Refactorizar `estadisticas_auditoria` (70 → < 20)
- [ ] Refactorizar `obtener_financiamiento_tendencia_mensual` (59 → < 20)
- [ ] Refactorizar `_extraer_texto_documento` (33 → < 15)
- [ ] Refactorizar `crear_documento_ai` (25 → < 15)

### **Fase 4: Mejoras Incrementales** (Ongoing)
- [ ] Aplicar refactorizaciones menores durante desarrollo normal
- [ ] Revisar código en code reviews
- [ ] Usar herramientas de análisis estático en CI/CD

---

## 🛠️ Herramientas y Métricas

### **Herramientas de Análisis**
- **Flake8 con mccabe:** Ya configurado (max-complexity=10)
- **Radon:** Para análisis más detallado de complejidad
- **Coverage:** Para asegurar que tests cubren código refactorizado

### **Métricas de Éxito**
- Reducir complejidad promedio de funciones críticas en 60%
- Aumentar cobertura de tests a > 80% para funciones refactorizadas
- Reducir tiempo de desarrollo de nuevas features en 20%
- Reducir bugs relacionados con lógica compleja en 50%

---

## 📋 Checklist de Refactorización

Para cada función a refactorizar:

- [ ] **Análisis:**
  - [ ] Identificar responsabilidades de la función
  - [ ] Mapear dependencias
  - [ ] Identificar condiciones anidadas
  - [ ] Identificar código duplicado

- [ ] **Preparación:**
  - [ ] Crear tests unitarios (cobertura > 80%)
  - [ ] Documentar comportamiento actual
  - [ ] Crear branch de refactorización

- [ ] **Refactorización:**
  - [ ] Extraer funciones helper
  - [ ] Aplicar guard clauses
  - [ ] Simplificar condiciones booleanas
  - [ ] Eliminar código duplicado
  - [ ] Mejorar nombres de variables/funciones

- [ ] **Validación:**
  - [ ] Ejecutar tests existentes
  - [ ] Ejecutar nuevos tests
  - [ ] Verificar que complejidad < 10
  - [ ] Code review
  - [ ] Verificar que no hay regresiones

---

## 🎓 Ejemplos de Refactorización

### **Ejemplo 1: Extracción de Funciones**

**Antes:**
```python
def procesar_pago(pago_data):
    if pago_data.get('monto'):
        if pago_data['monto'] > 0:
            if pago_data.get('cliente_id'):
                # ... 50 líneas más
```

**Después:**
```python
def procesar_pago(pago_data):
    if not _validar_pago(pago_data):
        raise ValueError("Datos de pago inválidos")
    
    pago = _crear_pago(pago_data)
    _aplicar_pago_a_cuotas(pago)
    _actualizar_estado_cliente(pago)
    return pago

def _validar_pago(pago_data):
    return (pago_data.get('monto', 0) > 0 and 
            pago_data.get('cliente_id') is not None)
```

### **Ejemplo 2: Guard Clauses**

**Antes:**
```python
def procesar_notificacion(notif):
    if notif:
        if notif.estado == 'PENDIENTE':
            if notif.cliente:
                # ... lógica principal
```

**Después:**
```python
def procesar_notificacion(notif):
    if not notif:
        return None
    if notif.estado != 'PENDIENTE':
        return None
    if not notif.cliente:
        raise ValueError("Notificación sin cliente")
    
    # ... lógica principal
```

---

## 📚 Recursos

- [Refactoring Guru - Complexity](https://refactoring.guru/smells/complexity)
- [Cyclomatic Complexity Explained](https://www.sonarsource.com/docs/CognitiveComplexity.pdf)
- [Python Refactoring Patterns](https://refactoring.com/catalog/)

---

## ✅ Criterios de Finalización

El plan se considerará completado cuando:
1. Todas las funciones con complejidad > 40 estén refactorizadas
2. 80% de funciones con complejidad 20-40 estén refactorizadas
3. Cobertura de tests > 80% para código refactorizado
4. No haya regresiones funcionales
5. Documentación actualizada

---

**Última actualización:** 2025-01-XX  
**Responsable:** Equipo de Desarrollo  
**Revisión:** Trimestral

