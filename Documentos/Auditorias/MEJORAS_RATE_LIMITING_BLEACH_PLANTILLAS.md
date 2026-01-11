# ✅ Mejoras de Seguridad Adicionales - Módulo Plantillas

**Fecha de Implementación:** 2025-01-27  
**Módulo:** `/herramientas/plantillas`  
**Estado:** ✅ COMPLETADO

---

## 📋 Resumen

Se han implementado **2 mejoras adicionales** de seguridad identificadas en la auditoría:

1. ✅ **Rate Limiting** (Prioridad Media) - Protección contra abuso
2. ✅ **Sanitización HTML con Bleach** (Prioridad Baja) - Sanitización más robusta

---

## 🔒 Mejoras Implementadas

### 1. ✅ Rate Limiting en Endpoints de Plantillas

**Archivo:** `backend/app/api/v1/endpoints/notificaciones.py`

**Funcionalidad:**
- Limita creación y actualización de plantillas a **20 requests/minuto** por IP/usuario
- Protege contra abuso y creación masiva de plantillas
- Usa el sistema de rate limiting existente (`slowapi`) con soporte para Redis distribuido

**Implementación:**
```python
from app.core.rate_limiter import RATE_LIMITS, get_rate_limiter

# Inicializar limiter
limiter = get_rate_limiter()

@router.post("/plantillas", response_model=NotificacionPlantillaResponse)
@limiter.limit(RATE_LIMITS["sensitive"])  # ✅ Rate limiting: 20 requests/minuto
def crear_plantilla(
    request: Request,  # ✅ Necesario para rate limiting
    plantilla: NotificacionPlantillaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ...

@router.put("/plantillas/{plantilla_id}", response_model=NotificacionPlantillaResponse)
@limiter.limit(RATE_LIMITS["sensitive"])  # ✅ Rate limiting: 20 requests/minuto
def actualizar_plantilla(
    request: Request,  # ✅ Necesario para rate limiting
    plantilla_id: int,
    plantilla: NotificacionPlantillaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ...
```

**Límites Aplicados:**
- **Crear plantilla:** 20 requests/minuto (`RATE_LIMITS["sensitive"]`)
- **Actualizar plantilla:** 20 requests/minuto (`RATE_LIMITS["sensitive"]`)

**Características:**
- ✅ Usa `slowapi` con soporte para Redis distribuido
- ✅ Fallback a memoria si Redis no está disponible
- ✅ Respuesta HTTP 429 cuando se excede el límite
- ✅ Considera proxies y headers `X-Forwarded-For` para obtener IP real

**Mensaje de Error:**
Cuando se excede el límite, el usuario recibe:
```json
{
  "detail": "429 Too Many Requests: 20 per 1 minute"
}
```

**Beneficios:**
- 🔒 Protección contra abuso del endpoint
- 🔒 Previene creación masiva de plantillas
- 🔒 Control de recursos del servidor
- 🔒 Mejor experiencia para usuarios legítimos

---

### 2. ✅ Sanitización HTML con Bleach

**Archivo:** `backend/app/utils/plantilla_validators.py`  
**Dependencia:** `bleach==6.1.0` (agregada a `requirements.txt`)

**Funcionalidad:**
- Sanitización HTML más robusta usando la librería `bleach`
- Protege contra XSS y otros ataques de inyección HTML
- Mantiene compatibilidad con método básico si bleach no está disponible

**Implementación:**
```python
# Intentar importar bleach para sanitización HTML robusta
try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False

def sanitizar_html(texto: str, permitir_html: bool = True) -> str:
    """
    Sanitiza HTML permitiendo solo tags y atributos seguros.
    Usa bleach si está disponible para sanitización robusta.
    """
    if not texto:
        return texto

    if not permitir_html:
        return escape(texto)

    # Proteger variables {{variable}}
    variables_protegidas = {}
    variable_pattern = r"\{\{([^}]+)\}\}"
    texto_procesado = texto
    idx = 0
    for match in re.finditer(variable_pattern, texto):
        placeholder = f"__VARIABLE_PROTECTED_{idx}__"
        variables_protegidas[placeholder] = match.group(0)
        texto_procesado = texto_procesado.replace(match.group(0), placeholder, 1)
        idx += 1

    # Usar bleach si está disponible
    if BLEACH_AVAILABLE:
        tags_permitidos = HTML_TAGS_PERMITIDOS
        atributos_permitidos = {
            "a": ["href", "title", "target"],
            "div": ["class"],
            "span": ["class"],
        }
        
        texto_sanitizado = bleach.clean(
            texto_procesado,
            tags=tags_permitidos,
            attributes=atributos_permitidos,
            protocols=["http", "https", "mailto"],  # Solo protocolos seguros
            strip=True,  # Eliminar tags no permitidos
        )
    else:
        # Fallback a método básico
        texto_sanitizado = escape(texto_procesado)
        # ... código de sanitización básica ...

    # Restaurar variables protegidas
    for placeholder, variable in variables_protegidas.items():
        texto_sanitizado = texto_sanitizado.replace(placeholder, variable)

    return texto_sanitizado
```

**Características:**
- ✅ Usa `bleach` para sanitización robusta si está disponible
- ✅ Fallback automático a método básico si bleach no está instalado
- ✅ Protege variables `{{variable}}` durante el proceso
- ✅ Valida protocolos en URLs (`http`, `https`, `mailto`)
- ✅ Elimina tags no permitidos automáticamente

**Tags Permitidos:**
- `p`, `br`, `strong`, `em`, `b`, `i`, `u`, `ul`, `ol`, `li`, `a`, `div`, `span`

**Atributos Permitidos:**
- `<a>`: `href`, `title`, `target`
- `<div>`, `<span>`: `class`

**Protocolos Permitidos en URLs:**
- `http://`, `https://`, `mailto:`

**Beneficios:**
- 🔒 Protección robusta contra XSS
- 🔒 Sanitización más completa que método básico
- 🔒 Compatibilidad hacia atrás (fallback si bleach no está disponible)
- 🔒 Validación estricta de protocolos en URLs

---

## 🔧 Archivos Modificados

### Archivos Modificados
1. **`requirements.txt`**
   - Agregado: `bleach==6.1.0`

2. **`backend/app/utils/plantilla_validators.py`**
   - Importación condicional de `bleach`
   - Mejora de función `sanitizar_html()` para usar bleach si está disponible
   - Mantiene fallback a método básico

3. **`backend/app/api/v1/endpoints/notificaciones.py`**
   - Importación de `RATE_LIMITS` y `get_rate_limiter`
   - Importación de `Request` de FastAPI
   - Aplicación de rate limiting en `crear_plantilla()`
   - Aplicación de rate limiting en `actualizar_plantilla()`

---

## ✅ Checklist de Verificación

### Rate Limiting
- [x] Rate limiting implementado en creación de plantillas
- [x] Rate limiting implementado en actualización de plantillas
- [x] Límite configurado: 20 requests/minuto
- [x] Usa sistema existente (`slowapi`)
- [x] Soporte para Redis distribuido
- [x] Fallback a memoria si Redis no está disponible

### Sanitización HTML
- [x] Bleach agregado a requirements.txt
- [x] Sanitización mejorada usando bleach
- [x] Fallback a método básico si bleach no está disponible
- [x] Variables `{{variable}}` protegidas
- [x] Protocolos validados en URLs
- [x] Tags y atributos permitidos configurados

---

## 🧪 Pruebas Recomendadas

### 1. Prueba de Rate Limiting
```python
# Test: Exceder límite de rate limiting
import requests

# Hacer 21 requests rápidamente
for i in range(21):
    response = requests.post(
        "/api/v1/notificaciones/plantillas",
        headers={"Authorization": f"Bearer {token}"},
        json={...}
    )
    if i == 20:
        assert response.status_code == 429
        assert "Too Many Requests" in response.json()["detail"]
```

### 2. Prueba de Sanitización con Bleach
```python
# Test: XSS con bleach
cuerpo_malicioso = "<script>alert('XSS')</script><p>Hola {{nombre}}</p>"
cuerpo_sanitizado = sanitizar_html(cuerpo_malicioso)

# Resultado esperado: Variables protegidas, script eliminado, p permitido
assert "{{nombre}}" in cuerpo_sanitizado
assert "<script>" not in cuerpo_sanitizado
assert "<p>" in cuerpo_sanitizado
```

### 3. Prueba de Fallback sin Bleach
```python
# Test: Funcionamiento sin bleach instalado
# Simular que bleach no está disponible
import sys
sys.modules['bleach'] = None

# Debe funcionar con método básico
cuerpo_sanitizado = sanitizar_html("<script>alert('XSS')</script>")
assert "<script>" not in cuerpo_sanitizado
```

---

## 📊 Impacto de las Mejoras

### Seguridad
- **Rate Limiting:** 🟢 ALTO - Protección contra abuso
- **Sanitización Bleach:** 🟢 ALTO - Protección robusta contra XSS

### Rendimiento
- **Rate Limiting:** 🟢 POSITIVO - Control de recursos del servidor
- **Sanitización Bleach:** 🟡 NEUTRO - Ligeramente más lento que método básico, pero más seguro

### Mantenibilidad
- **Rate Limiting:** 🟢 ALTO - Usa sistema existente, fácil de mantener
- **Sanitización Bleach:** 🟢 ALTO - Librería estándar, bien mantenida

---

## 🎯 Configuración

### Rate Limiting

**Límites Configurados:**
- Crear plantilla: `RATE_LIMITS["sensitive"]` = `"20/minute"`
- Actualizar plantilla: `RATE_LIMITS["sensitive"]` = `"20/minute"`

**Para cambiar límites:**
Modificar en `backend/app/core/rate_limiter.py`:
```python
RATE_LIMITS = {
    "sensitive": "30/minute",  # Cambiar a 30 requests/minuto
    ...
}
```

**O usar límite específico:**
```python
@limiter.limit("10/minute")  # Límite específico
```

### Sanitización HTML

**Configuración de Bleach:**
Modificar en `backend/app/utils/plantilla_validators.py`:
```python
# Agregar más tags permitidos
HTML_TAGS_PERMITIDOS = ["p", "br", "strong", "em", "h1", "h2", ...]

# Agregar más atributos permitidos
atributos_permitidos = {
    "a": ["href", "title", "target", "rel"],
    "div": ["class", "id"],
    ...
}
```

---

## 📝 Notas Técnicas

### Rate Limiting
- Usa `slowapi` con soporte para Redis distribuido
- En producción distribuida, configure `REDIS_URL` para rate limiting compartido
- Sin Redis, usa memoria (limitado a instancia única)
- Considera proxies y headers `X-Forwarded-For` para obtener IP real

### Sanitización Bleach
- `bleach` es una librería estándar y bien mantenida para sanitización HTML
- Más robusta que método básico con regex
- Protege contra más vectores de ataque XSS
- Mantiene compatibilidad con fallback si no está instalado

---

## ✅ Conclusión

Las **2 mejoras adicionales** han sido implementadas exitosamente:

1. ✅ **Rate Limiting** - Protección contra abuso (20 requests/minuto)
2. ✅ **Sanitización HTML con Bleach** - Sanitización más robusta

El módulo de plantillas ahora tiene:
- ✅ **Nivel de seguridad:** ALTO
- ✅ **Protección contra abuso:** Implementada
- ✅ **Sanitización HTML:** Robusta con bleach
- ✅ **Listo para producción:** Sí

---

**Implementado por:** AI Assistant  
**Fecha:** 2025-01-27  
**Estado:** ✅ COMPLETADO
