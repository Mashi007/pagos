# 🔍 Cómo Verificar si el Prompt Personalizado está siendo Usado

**Fecha:** 2025-01-27  
**Objetivo:** Documentar todos los métodos para verificar si un prompt personalizado está configurado y activo en el sistema.

---

## 📋 Resumen Ejecutivo

El sistema de AI tiene dos modos de operación:
1. **Prompt Default**: Usa el prompt predefinido del sistema
2. **Prompt Personalizado**: Usa un prompt configurado por el usuario

El sistema verifica automáticamente en cada consulta si hay un prompt personalizado y lo usa si existe.

---

## 🔍 Métodos de Verificación

### 1. **Verificación en Base de Datos (SQL)**

Ejecuta el script SQL: `scripts/verificar_prompt_personalizado.sql`

```sql
-- Verificar si existe prompt personalizado
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM configuracion_sistema
            WHERE categoria = 'AI'
            AND clave = 'system_prompt_personalizado'
            AND valor IS NOT NULL
            AND valor != ''
        ) THEN '✅ PROMPT PERSONALIZADO CONFIGURADO'
        ELSE '❌ NO HAY PROMPT PERSONALIZADO (usando default)'
    END AS estado;
```

**Resultado esperado:**
- ✅ `PROMPT PERSONALIZADO CONFIGURADO` = El prompt está guardado y será usado
- ❌ `NO HAY PROMPT PERSONALIZADO` = Se usará el prompt default

---

### 2. **Verificación desde la API (Backend)**

#### Endpoint: `GET /api/v1/configuracion/ai/prompt`

**Respuesta:**
```json
{
  "prompt_personalizado": "...",
  "tiene_prompt_personalizado": true,
  "usando_prompt_default": false,
  "variables_personalizadas": [...]
}
```

**Campos importantes:**
- `tiene_prompt_personalizado`: `true` = está configurado y será usado
- `usando_prompt_default`: `false` = NO está usando el default (está usando el personalizado)

---

### 3. **Verificación en Logs del Backend**

Cuando el sistema usa el prompt personalizado, aparece este log:

```
INFO: Usando prompt personalizado configurado por el usuario
```

**Ubicación del código:**
```python
# backend/app/services/ai_chat_service.py línea 134
if usar_prompt_personalizado:
    logger.info("Usando prompt personalizado configurado por el usuario")
```

**Cómo verificar:**
1. Hacer una pregunta en el Chat AI
2. Revisar los logs del backend
3. Buscar el mensaje "Usando prompt personalizado"

---

### 4. **Verificación desde el Frontend**

En la interfaz de configuración de AI (`/configuracion?tab=ai`):

1. **Sección "Prompt Personalizado"**
   - Si hay un checkbox marcado: "✅ Usando prompt personalizado" = **ESTÁ ACTIVO**
   - Si no hay checkbox o está desmarcado = **NO está activo**

2. **Campo de texto del prompt**
   - Si tiene contenido = **ESTÁ CONFIGURADO**
   - Si está vacío = **NO está configurado**

---

## 🔧 Cómo Funciona el Sistema

### Flujo de Decisión

```
Usuario hace pregunta en Chat AI
    ↓
AIChatService.inicializar_configuracion()
    ↓
Obtiene config_dict desde BD
    ↓
AIChatService.construir_system_prompt()
    ↓
Verifica: config_dict.get("system_prompt_personalizado")
    ↓
¿Existe y no está vacío?
    ├─ SÍ → Usa _construir_system_prompt_personalizado()
    │        ↓
    │        Log: "Usando prompt personalizado configurado por el usuario"
    │
    └─ NO → Usa _construir_system_prompt_default()
             ↓
             Log: (no hay log específico, es el comportamiento default)
```

### Código Relevante

**Backend - Verificación:**
```python
# backend/app/services/ai_chat_service.py
prompt_personalizado = self.config_dict.get("system_prompt_personalizado", "")
usar_prompt_personalizado = prompt_personalizado and prompt_personalizado.strip()

if usar_prompt_personalizado:
    logger.info("Usando prompt personalizado configurado por el usuario")
    # ... usar prompt personalizado
else:
    # ... usar prompt default
```

**Base de Datos - Almacenamiento:**
```sql
-- Tabla: configuracion_sistema
-- Categoría: 'AI'
-- Clave: 'system_prompt_personalizado'
-- Valor: (texto del prompt personalizado)
```

---

## ✅ Checklist de Verificación

Usa este checklist para verificar que el prompt personalizado está activo:

- [ ] **BD**: Ejecutar `verificar_prompt_personalizado.sql` → Debe mostrar "✅ PROMPT PERSONALIZADO CONFIGURADO"
- [ ] **API**: Llamar `GET /api/v1/configuracion/ai/prompt` → `tiene_prompt_personalizado` debe ser `true`
- [ ] **Frontend**: Verificar checkbox "Usando prompt personalizado" → Debe estar marcado
- [ ] **Logs**: Hacer una pregunta en Chat AI → Debe aparecer "Usando prompt personalizado configurado por el usuario"
- [ ] **Placeholders**: Verificar que el prompt tenga todos los placeholders requeridos:
  - [ ] `{resumen_bd}`
  - [ ] `{info_cliente_buscado}`
  - [ ] `{datos_adicionales}`
  - [ ] `{info_esquema}`
  - [ ] `{contexto_documentos}`

---

## 🚨 Problemas Comunes

### Problema 1: El prompt está guardado pero no se usa

**Síntomas:**
- El prompt aparece en la BD
- Pero los logs muestran que se usa el default

**Causas posibles:**
1. El prompt está vacío o solo tiene espacios en blanco
2. El prompt no tiene los placeholders requeridos (el sistema puede fallar silenciosamente)

**Solución:**
```sql
-- Verificar que el prompt no esté vacío
SELECT 
    clave,
    LENGTH(TRIM(valor)) AS longitud,
    CASE 
        WHEN LENGTH(TRIM(valor)) = 0 THEN '❌ VACÍO'
        ELSE '✅ TIENE CONTENIDO'
    END AS estado
FROM configuracion_sistema
WHERE categoria = 'AI'
AND clave = 'system_prompt_personalizado';
```

---

### Problema 2: El prompt se guarda pero desaparece

**Causas posibles:**
1. Se está eliminando desde el frontend (botón "Restaurar Default")
2. Hay un error en el guardado que hace rollback

**Solución:**
- Verificar logs del backend al guardar
- Verificar que no haya errores de validación de placeholders

---

### Problema 3: Los placeholders no se reemplazan

**Síntomas:**
- El prompt se usa pero aparecen `{resumen_bd}` literalmente en lugar de datos

**Causas posibles:**
1. El placeholder está mal escrito (ej: `{resumen_bd` sin cerrar)
2. Hay un error en `_construir_system_prompt_personalizado()`

**Solución:**
- Verificar que todos los placeholders estén correctamente escritos
- Revisar logs del backend para errores de formato

---

## 📊 Script SQL Completo

Ver archivo: `scripts/verificar_prompt_personalizado.sql`

Este script verifica:
1. ✅ Si existe el prompt personalizado
2. ✅ Detalles del prompt (longitud, fecha de actualización)
3. ✅ Si tiene todos los placeholders requeridos
4. ✅ Variables personalizadas activas
5. ✅ Resumen completo del estado

---

## 🔗 Referencias

- **Código Backend**: `backend/app/services/ai_chat_service.py` (línea 120-152)
- **Endpoint API**: `backend/app/api/v1/endpoints/configuracion.py` (línea 4165-4214)
- **Función de Construcción**: `backend/app/api/v1/endpoints/configuracion.py` (línea 6602-6631)
- **Script SQL**: `scripts/verificar_prompt_personalizado.sql`

---

## 📝 Notas Adicionales

1. **El sistema verifica automáticamente** en cada consulta, no hay caché
2. **Si eliminas el prompt personalizado**, automáticamente vuelve al default
3. **Los placeholders son obligatorios** - el sistema valida al guardar
4. **Las variables personalizadas** se agregan después de los placeholders base

---

**Última actualización:** 2025-01-27

