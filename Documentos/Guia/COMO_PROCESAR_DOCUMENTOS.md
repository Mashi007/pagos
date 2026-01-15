# 📄 Guía: Cómo Procesar Documentos en el Sistema RAG

**Fecha:** 2025-01-XX  
**Sistema:** RAPICREDIT - Chat AI

---

## 🎯 ¿Qué significa "Procesar Documentos"?

**Procesar un documento** significa extraer el texto del archivo (PDF/TXT/DOCX) y guardarlo en la base de datos para que el Chat AI pueda usarlo.

---

## 📋 Formas de Procesar Documentos

### **Opción 1: Procesamiento Automático (Recomendado)**

**Cuándo ocurre:** Al subir un documento nuevo

**Proceso:**
1. Subes el documento en la pestaña "Gestión de Documentos" (RAGTab)
2. El sistema automáticamente intenta procesarlo
3. Si tiene éxito, el documento queda procesado inmediatamente

**Ventajas:**
- ✅ Automático, no requiere acción adicional
- ✅ Inmediato
- ✅ El documento está listo para usar

**Si falla:**
- El documento se guarda pero queda sin procesar
- Puedes procesarlo manualmente después (Opción 2)

---

### **Opción 2: Procesamiento Manual** ⚙️

**Cuándo usar:**
- ❌ El procesamiento automático falló
- 🔄 Quieres reprocesar un documento existente
- 📄 El documento fue subido pero no se procesó

---

#### **📱 Guía Visual Paso a Paso:**

**Paso 1: Navegar a la Gestión de Documentos**

```
1. Abre tu navegador y ve a:
   ┌─> https://rapicredit.onrender.com/configuracion?tab=ai

2. En la interfaz, busca la seción "Sistema Híbrido"
   ┌─> Haz clic en el tab "RAG"

3. Verás la pestaña "Gestión de Documentos"
   ┌─> Esta es donde están todos tus documentos
```

---

**Paso 2: Identificar Documentos Sin Procesar**

En la lista de documentos, busca documentos con estos indicadores:

```
┌─────────────────────────────────────────────────────────┐
│ 📄 Políticas de Préstamos                    │
│ ┌───────────────────────────────────────────────┐      │
│ │ ⚠️ Sin procesar  │ Activo │ Inactivo │      │
│ └───────────────────────────────────────────────┘      │
│ Descripción: Documento con políticas...              │
│ 📎 politicas.pdf │ PDF │ 2.5 MB │ 2025-01-15 │
│                                    [Procesar] [✏️ Editar] [🗑️ Eliminar] │
└─────────────────────────────────────────────────────────┘
```

**Indicadores visuales:**
- ⚠️ **Badge "Sin procesar"** (amarillo con ícono AlertCircle) = Necesita procesamiento
- ✅ **Badge "Procesado"** (verde con ícono CheckCircle) = Ya procesado
- 🔵 **Badge "Activo"** = Documento activo para usar en AI
- 🔴 **Badge "Inactivo"** = Documento no disponible

---

**Paso 3: Procesar el Documento**

```
1. En la fila del documento sin procesar:
   ┌─> Busca el botón "Procesar" (ícono FileText azul)

2. Haz clic en "Procesar"
   ┌─> El botón mostrará "Procesando..." con spinner

3. El sistema procesará el documento:
   ├─> Busca el archivo físico
   ├─> Extrae texto según tipo (PDF/TXT/DOCX)
   ├─> Limpia y normaliza el texto
   ├─> Guarda contenido_texto en BD
   └─> Marca contenido_procesado = true
```

**Durante el procesamiento:**
- ⏳ El botón muestra "Procesando..." con spinner
- 🔒 El botón está desabilitado para evitar clics múltiples
- ⏱ Puedes seguir usando otras partes de la interfaz

---

**Paso 4: Verificar Éxito**

Después de procesar, verás:

```
┌─────────────────────────────────────────────────────────┐
│ 📄 Políticas de Préstamos                    │
│ ┌───────────────────────────────────────────────┐      │
│ │ ✅ Procesado  │ Activo │ Inactivo │      │
│ └───────────────────────────────────────────────┘      │
│ Descripción: Documento con políticas...              │
│ 📎 politicas.pdf │ PDF │ 2.5 MB │ 2025-01-15 │
│                                    [✏️ Editar] [🗑️ Eliminar] │
└─────────────────────────────────────────────────────────┘

✅ Toast: "Documento procesado exitosamente (15,234 caracteres extraídos)"
```

**Cambios visibles:**
- ✅ Badge "Sin procesar" → Badge "Procesado" (verde)
- 📊 Mensaje de éxito con cantidad de caracteres extraídos
- 🎯 El documento está listo para generar embeddings

---

#### **🔧 Ejemplo Completo Visual:**

**Antes de Procesar:**
```
┌─────────────────────────────────────────────────────────┐
│ Documentos Existentes                        │
├─────────────────────────────────────────────────────────┤
│                                            │
│ 📄 Manual de Usuario                      │
│ [⚠️ Sin procesar] [🔵 Activo]        │
│                                            │
│                                            │
│ 📎 manual.pdf │ PDF │ 1.2 MB │ 2025-01-10 │
│                                            │
│ [📄 Procesar] [✏️ Editar] [🗑️ Eliminar] │
│                                            │
└─────────────────────────────────────────────────────────┘
```

**Después de Procesar:**
```
┌─────────────────────────────────────────────────────────┐
│ Documentos Existentes                        │
├─────────────────────────────────────────────────────────┤
│                                            │
│ 📄 Manual de Usuario                      │
│ [✅ Procesado] [🔵 Activo] [✅ Disponible para AI] │
│                                            │
│                                            │
│ 📎 manual.pdf │ PDF │ 1.2 MB │ 2025-01-10 │
│                                            │
│ [✏️ Editar] [🗑️ Eliminar]                    │
│                                            │
└─────────────────────────────────────────────────────────┘

✅ Toast: "Documento procesado exitosamente (8,456 caracteres extraídos)"
```

---

#### **⚠️ Mensajes de Error Comunes:**

**Si el archivo no existe:**
```
❌ Toast: "El archivo físico no existe en el servidor. 
Por favor, elimina este documento y súbelo nuevamente."

💡 Solución: 
1. Elimina el documento desde la interfaz
2. Súbelo nuevamente
3. El sistema intentará procesarlo automáticamente
```

**Si falla la extracción:**
```
❌ Toast: "No se pudo extraer texto del documento 'Manual.pdf'.
El archivo puede estar corrupto, encriptado, o ser un PDF escaneado."

💡 Soluciones:
- Verifica que el PDF tenga texto (no solo imágenes)
- Si está encriptado, desencripta antes de subirlo
- Si es escaneado, convierte a texto primero
```

---

#### **✅ Verificación Post-Procesamiento:**

**En la Interfaz:**
- ✅ Badge "Procesado" visible (verde)
- ✅ Mensaje de éxito con caracteres extraídos
- ✅ Si está activo, muestra "✅ Disponible para AI"

**En la Base de Datos:**
```sql
-- Verificar que el documento esté procesado
SELECT 
    id,
    titulo,
    contenido_procesado,  -- Debe ser TRUE
    LENGTH(contenido_texto) as caracteres_extraidos  -- Debe ser > 0
FROM documentos_ai
WHERE id = {documento_id};

-- Resultado esperado:
-- id | titulo              | contenido_procesado | caracteres_extraidos
-- 1  | Políticas Préstamos | true            | 15234
```

#### **Desde la API (Programáticamente):**

**Endpoint:** `POST /api/v1/configuracion/ai/documentos/{documento_id}/procesar`

**Ejemplo con cURL:**
```bash
curl -X POST \
  https://rapicredit.onrender.com/api/v1/configuracion/ai/documentos/1/procesar \
  -H "Authorization: Bearer TU_TOKEN"
```

**Ejemplo con Python:**
```python
import requests

url = "https://rapicredit.onrender.com/api/v1/configuracion/ai/documentos/1/procesar"
headers = {"Authorization": "Bearer TU_TOKEN"}

response = requests.post(url, headers=headers)
print(response.json())
```

---

## 🔄 Proceso Completo Paso a Paso

### **Paso 1: Subir Documento**

```
1. Ve a: Configuración → AI → Sistema Híbrido → RAG
2. Pestaña: "Gestión de Documentos"
3. Completa el formulario:
   - Título: "Políticas de Préstamos"
   - Descripción: "Documento con políticas..."
   - Archivo: Selecciona tu PDF/TXT/DOCX
4. Haz clic en "Subir Documento"
```

**Resultado:**
- ✅ Archivo guardado físicamente
- ✅ Registro creado en BD
- ⚠️ Estado: "Sin procesar" (si el procesamiento automático falló)

---

### **Paso 2: Procesar Documento**

**Si el procesamiento automático falló:**

```
1. En la lista de documentos, encuentra el documento
2. Verás badge "Sin procesar" (amarillo)
3. Haz clic en el botón "Procesar"
4. Espera el mensaje de éxito
```

**Lo que hace el sistema:**
```
Usuario hace clic en "Procesar"
    ↓
Frontend: POST /api/v1/configuracion/ai/documentos/{id}/procesar
    ↓
Backend: Busca el archivo físico
    ↓
Backend: Detecta tipo de archivo (PDF/TXT/DOCX)
    ↓
Backend: Extrae texto según tipo:
    - PDF → PyPDF2 o pdfplumber
    - TXT → Lectura directa
    - DOCX → python-docx
    ↓
Backend: Limpia y normaliza el texto
    ↓
Backend: Guarda contenido_texto en BD
    ↓
Backend: Marca contenido_procesado = true
    ↓
✅ Documento procesado exitosamente
```

---

### **Paso 3: Verificar Procesamiento**

**En la interfaz:**
- ✅ Badge "Procesado" (verde) = Documento procesado correctamente
- ✅ Badge "Sin procesar" (amarillo) = Necesita procesamiento

**En la base de datos:**
```sql
-- Ver documentos procesados
SELECT id, titulo, contenido_procesado, 
       LENGTH(contenido_texto) as caracteres
FROM documentos_ai
WHERE contenido_procesado = true;

-- Ver documentos sin procesar
SELECT id, titulo, contenido_procesado
FROM documentos_ai
WHERE contenido_procesado = false;
```

---

## ⚙️ Requisitos para Procesar

### **1. Archivo Físico Disponible**
- El archivo debe existir en el servidor
- Ruta: `uploads/documentos_ai/` (o según configuración)

### **2. Herramientas Adicionales Requeridas** ⚠️

**⚠️ IMPORTANTE:** Necesitas instalar herramientas adicionales según el tipo de archivo:

| Tipo Archivo | Herramienta Requerida | Instalación |
|--------------|----------------------|------------|
| **TXT** | Ninguna | ✅ Ya disponible |
| **PDF** | PyPDF2 **O** pdfplumber | `pip install PyPDF2 pdfplumber` |
| **DOCX** | python-docx | `pip install python-docx` |

**Instalación completa recomendada:**
```bash
pip install PyPDF2 pdfplumber python-docx
```

**📚 Guía completa:** Ver `Documentos/Guia/HERRAMIENTAS_PROCESAMIENTO_DOCUMENTOS.md` para detalles de instalación, verificación y troubleshooting.

### **3. Permisos**
- Solo administradores pueden procesar documentos
- El usuario debe tener `is_admin = true`

---

## 🔍 Verificación del Procesamiento

### **Desde la Interfaz:**

1. **Ver estado del documento:**
   - Badge "Procesado" = ✅ Procesado
   - Badge "Sin procesar" = ❌ No procesado

2. **Ver información:**
   - El documento procesado mostrará información del archivo
   - Si está procesado, puedes generar embeddings

### **Desde el Backend:**

**Verificar en logs:**
```
✅ Documento procesado: {titulo}
   Caracteres extraídos: {cantidad}
   Contenido guardado en BD (disponible para entrenamiento)
```

**Verificar en BD:**
```sql
SELECT 
    id,
    titulo,
    contenido_procesado,
    CASE 
        WHEN contenido_texto IS NOT NULL 
        THEN LENGTH(contenido_texto) 
        ELSE 0 
    END as caracteres_extraidos
FROM documentos_ai
ORDER BY creado_en DESC;
```

---

## ⚠️ Problemas Comunes y Soluciones

### **Problema 1: "Archivo no encontrado"**

**Causa:** El archivo físico desapareció (sistemas efímeros como Render)

**Solución:**
1. Elimina el documento desde la interfaz
2. Súbelo nuevamente
3. El sistema intentará procesarlo automáticamente

---

### **Problema 2: "No se pudo extraer texto"**

**Causas posibles:**
- PDF encriptado con contraseña
- PDF escaneado (solo imágenes, sin texto)
- Archivo corrupto
- Dependencias no instaladas

**Soluciones:**

**Para PDF encriptado:**
- Desencripta el PDF antes de subirlo
- O usa un PDF sin protección

**Para PDF escaneado:**
- Necesitarías OCR (no implementado actualmente)
- Convierte el PDF escaneado a texto primero

**Para dependencias faltantes:**
```bash
# Instalar dependencias
pip install PyPDF2 python-docx pdfplumber
```

---

### **Problema 3: "Documento procesado pero sin contenido"**

**Causa:** El archivo está vacío o no tiene texto extraíble

**Solución:**
- Verifica que el archivo tenga contenido
- Intenta con otro formato (ej: convertir PDF a TXT)

---

## 📊 Estados de un Documento

| Estado | `contenido_procesado` | `contenido_texto` | Acciones Disponibles |
|--------|----------------------|-------------------|---------------------|
| **Subido** | `false` | `null` | Procesar manualmente |
| **Procesado** | `true` | Texto completo | ✅ Generar embeddings<br>✅ Usar en Chat AI |
| **Con Embeddings** | `true` | Texto completo | ✅ Búsqueda semántica<br>✅ Chat AI mejorado |

---

## 🎯 Flujo Completo Recomendado

```
1. SUBIR DOCUMENTO
   └─> Sistema intenta procesar automáticamente
       ├─> ✅ Éxito → Documento procesado
       └─> ❌ Falla → Documento sin procesar

2. PROCESAR MANUALMENTE (si falló)
   └─> Click en "Procesar"
       └─> ✅ Éxito → Documento procesado

3. VERIFICAR PROCESAMIENTO
   └─> Badge "Procesado" (verde)
       └─> ✅ Listo para siguiente paso

4. GENERAR EMBEDDINGS (Opcional)
   └─> Pestaña "Embeddings y Búsqueda"
       └─> Click en "Generar Embeddings"
           └─> ✅ Embeddings generados

5. USAR EN CHAT AI
   └─> El Chat AI usa automáticamente documentos procesados
       └─> ✅ Respuestas mejoradas con contexto
```

---

## 💡 Consejos y Mejores Prácticas

### **1. Formato de Archivos**
- ✅ **PDF:** Mejor si es PDF con texto (no escaneado)
- ✅ **TXT:** Más rápido de procesar
- ✅ **DOCX:** Funciona bien con python-docx

### **2. Tamaño de Archivos**
- ✅ Máximo recomendado: 10MB
- ✅ Archivos grandes pueden tardar más en procesar

### **3. Procesamiento Automático**
- ✅ Siempre intenta procesar automáticamente al subir
- ✅ Si falla, procesa manualmente después
- ✅ El contenido se guarda en BD (no depende del archivo físico)

### **4. Verificación**
- ✅ Verifica que el documento tenga badge "Procesado"
- ✅ Revisa los logs si hay problemas
- ✅ Verifica en BD que `contenido_texto` no esté vacío

---

## 🔗 Endpoints Relacionados

| Acción | Endpoint | Método |
|--------|----------|--------|
| **Subir documento** | `/api/v1/configuracion/ai/documentos` | POST |
| **Procesar documento** | `/api/v1/configuracion/ai/documentos/{id}/procesar` | POST |
| **Listar documentos** | `/api/v1/configuracion/ai/documentos` | GET |
| **Ver documento** | `/api/v1/configuracion/ai/documentos/{id}` | GET |
| **Eliminar documento** | `/api/v1/configuracion/ai/documentos/{id}` | DELETE |

---

---

## 🔧 Troubleshooting Específico: Procesamiento Manual

### **Problema: El botón "Procesar" no aparece**

**Causas posibles:**
- El documento ya está procesado (`contenido_procesado = true`)
- No tienes permisos de administrador
- Error de carga de documentos

**Soluciones:**

**Si el documento ya está procesado:**
- ✅ No necesitas procesarlo nuevamente
- ✅ Puedes generar embeddings directamente
- ✅ El Chat AI ya puede usarlo

**Si no tienes permisos:**
- 🔒 Solo administradores pueden procesar documentos
- 📧 Contacta al administrador del sistema

**Si hay error de carga:**
- 🔄 Recarga la página (F5)
- 🔄 Verifica tu conexión a internet
- 📧 Revisa la consola del navegador (F12) para errores

---

### **Problema: El procesamiento tarda mucho**

**Causas:**
- Archivo muy grande (>10MB)
- Servidor lento o sobrecargado
- Proceso de extracción complejo (PDF con muchas imágenes)

**Soluciones:**
- �️ Espera a que termine (puede tardar varios minutos)
- 📊 Verifica el progreso en los logs del servidor
- 🔄 Si falla después de mucho tiempo, intenta con un archivo más pequeño

---

### **Problema: "Procesado" pero sin contenido**

**Verificación:**
```sql
SELECT 
    id,
    titulo,
    contenido_procesado,
    CASE 
        WHEN contenido_texto IS NULL THEN 'NULL'
        WHEN contenido_texto = '' THEN 'VACÍO'
        ELSE CONCAT('OK: ', LENGTH(contenido_texto), ' caracteres')
    END as estado_contenido
FROM documentos_ai
WHERE id = {documento_id};
```

**Si el contenido está NULL o VACÍO:**
- ❌ El procesamiento falló silenciosamente
- 🔄 Intenta procesarlo nuevamente
- 📧 Si persiste, el archivo puede estar corrupto o vacío

---

## ✅ Resumen Ejecutivo

### **📋 Formas de Procesar:**

| Método | Cuándo Usar | Ventajas |
|--------|--------------|----------|
| **Automático** | Al subir documento | ✅ Inmediato<br>✅ Sin acción adicional |
| **Manual** | Si falla automático<br>Reprocesar existente | ✅ Control total<br>✅ Verificación explícita |

---

### **🎯 Pasos Rápidos:**

**Procesamiento Automático:**
```
1. Sube documento → Sistema procesa automáticamente → ✅ Listo
```

**Procesamiento Manual:**
```
1. Ve a: Configuración → AI → RAG → Gestión Documentos
2. Busca documento con badge "⚠️ Sin procesar"
3. Haz clic en botón "📄 Procesar"
4. Espera mensaje de éxito → ✅ Badge cambia a "Procesado"
```

---

### **📊 Resultado Final:**

Después de procesar (automático o manual):

✅ **Estado en BD:**
- `contenido_procesado = true`
- `contenido_texto` = Texto completo extraído
- Documento disponible para Chat AI

✅ **Estado en Interfaz:**
- Badge "✅ Procesado" (verde)
- Si está activo: "✅ Disponible para AI"
- Botón "Procesar" desaparece (ya no es necesario)

✅ **Siguiente Paso (Opcional):**
- Generar embeddings para búsqueda semántica
- Activar documento si no está activo
- Usar en Chat AI (automático si está activo)

---

**🎯 El procesamiento convierte archivos físicos (PDF/TXT/DOCX) en texto utilizable por el Chat AI, guardándolo permanentemente en la base de datos.**
