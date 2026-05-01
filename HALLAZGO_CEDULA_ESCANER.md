# 🔍 HALLAZGO: Extracción de Cédula en Escaneo de Comprobantes

**Verificación solicitada:**
> Al escanear comprobante en formulario, ¿se extrae la cédula automáticamente para Mercantil y BNC?

**Respuesta: ❌ NO, ACTUALMENTE NO LO HACE**

---

## 📊 ANÁLISIS DEL CÓDIGO

### **Ubicación del Gemini OCR**
Archivo: `backend/app/services/pagos_gmail/gemini_service.py` (líneas 1-2400+)

### **Hallazgo Principal**

**Líneas 39-46**: Existe un **MODO ESPECIAL** llamado `error_email_rescan` que SÍ extrae cédula de Mercantil (A) y BNC (B):

```python
GEMINI_PAGOS_GMAIL_MODO_ERROR_EMAIL_AB = """
MODO ESPECIAL — RE-ESCANEO (solo esta peticion; el backend usa scan_filter **error_email_rescan**):
  El hilo puede tener etiqueta Gmail **ERROR EMAIL** ...
  FORMATOS **A** y **B** — el campo JSON **"cedula"** **si** se evalua en este modo (excepcion al bloque REGLA CEDULA **solo** para esta peticion y solo si clasificas A o B):
    - Extrae la cedula del **depositante** **unicamente** desde el comprobante: **DP:V-** / **DP:E-** / **DP:J-** + digitos, **Cedula Dep.**, casillas **Nro. de Cédula** en papel Mercantil, etc.
    - Si **todos** los digitos son inequivocos, devuelve cadena con prefijo **V**, **E** o **J** en mayuscula + digitos sin puntos (ej. **V30145077**).
    - Si hay **cualquier** duda en un digito, la zona esta tapada/sellada o no hay patron claro -> **"cedula":"ERROR"** (literal ERROR, sin comillas extra en JSON).
```

---

## ⚠️ EL PROBLEMA

**Línea 52-64: REGLA CEDULA (GLOBAL)**

```python
REGLA CEDULA (SISTEMA — obligatoria imagen 1–6 / formatos A, B, C, D, E, F, NR):
  NO extraigas, NO copies y NO infieras el **numero de cedula** (ni V-, E-, J-, CI, RIF, documento del depositante) desde:
    - imagen embebida, adjunta, PDF, etc.
  En JSON el campo "cedula" debe ser SIEMPRE el literal **"NA"** para **imagen 1 (A)**, **imagen 2 (B)**, ...
  El backend asigna la cedula real consultando la tabla clientes por el email del remitente (cabecera De / From).
```

**TRADUCCIÓN**: 
- ❌ **Modo normal (defecto)**: Cédula = "NA" siempre
- ✅ **Modo error_email_rescan**: Cédula = se extrae de Mercantil/BNC

---

## 🎯 SOLUCIÓN

**Necesita dos cambios:**

### **1. En el Gemini OCR (gemini_service.py)**

Crear una función o parámetro que extraiga cédula SIEMPRE para Mercantil (A) y BNC (B) en escaneo manual:

```python
def extract_infopagos_campos_desde_comprobante(
    image_bytes: bytes,
    banco: str = "autodetect",  # "Mercantil", "BNC", "otro"
    extraer_cedula: bool = True  # ← NUEVO: permitir extracción de cédula
):
    """
    Escáner personal (cobros module, revisión manual):
    - Si banco="Mercantil" (A) y extraer_cedula=True → extrae DP:V-, DP:E-, etc.
    - Si banco="BNC" (B) y extraer_cedula=True → extrae de casilla cédula
    - Otros → cédula="NA" (manual)
    """
    # Usar el MISMO prompt que error_email_rescan pero con parámetro
```

### **2. En el endpoint de escaneo (cobros/routes.py o cobros_publico/routes.py)**

El endpoint que recibe el escaneo debe:

```python
@router.post("/escaner/extraer-comprobante")
def escaner_infopagos(
    request: Request,
    image: UploadFile,
    banco: Optional[str] = None,  # "Mercantil", "BNC", o None=autodetect
    db: Session = Depends(get_db),
):
    """
    Escaneo en formulario de editar pago:
    - Detecta banco automáticamente O usa banco parámetro
    - Si Mercantil o BNC → extrae cédula también
    - Retorna: { comprobante_imagen_id, numero_cedula, ... }
    """
    
    # Llamar a Gemini con extraer_cedula=True para Mercantil/BNC
    campos = extract_infopagos_campos_desde_comprobante(
        image_bytes=image.file.read(),
        banco=banco or "autodetect",
        extraer_cedula=True  # ← PERMITE EXTRACCIÓN
    )
    
    # Si Mercantil (A) o BNC (B) → rellenar numero_cedula
    if campos.get("formato") in ("A", "B"):
        numero_cedula = campos.get("cedula")  # Ahora no es "NA"
        if numero_cedula and numero_cedula != "ERROR":
            # Guardar en formulario
            return {
                "comprobante_imagen_id": borrador_id,
                "numero_cedula": numero_cedula,  # ← AUTOMÁTICO
                "banco": campos.get("formato_etiqueta"),
                ...
            }
```

---

## 📋 CAMBIOS NECESARIOS

| Componente | Cambio | Dónde |
|-----------|--------|-------|
| **Gemini Prompt** | Usar siempre `error_email_rescan` logic para Mercantil/BNC en escaneo manual | `gemini_service.py` |
| **Función Extracción** | Agregar parámetro `extraer_cedula=True` | `gemini_service.py` |
| **Endpoint Escaneo** | Pasar `extraer_cedula=True` para Mercantil/BNC | `cobros/routes.py` o `cobros_publico/routes.py` |
| **Frontend (Formulario)** | Al recibir respuesta, llenar campo `numero_cedula` si no es "NA" | `frontend/src/pages/CobrosEditarPage.tsx` o similar |

---

## 🎯 RESULTADO ESPERADO

**ANTES (actual):**
```
[Escanear comprobante Mercantil]
  ↓
OCR retorna: { comprobante_imagen, numero_cedula: "NA", ... }
  ↓
Usuario debe escribir manualmente: V30145077
```

**DESPUÉS (con fix):**
```
[Escanear comprobante Mercantil]
  ↓
OCR retorna: { comprobante_imagen, numero_cedula: "V30145077", ... }
  ↓
✅ Campo de cédula relleno automáticamente
```

---

## 💡 NOTA IMPORTANTE

La **regla CEDULA GLOBAL** (línea 52-64) existe para Gmail porque:
- Gmail: Backend obtiene cédula desde email del remitente
- Está **correcta** para ese caso

Pero para **escaneo manual en formulario**:
- No hay email confiable
- Usuario está autenticado y autorizado
- Debe extraerse la cédula del comprobante

**Esto requiere un parámetro o función separada**, no cambiar la regla global.

---

**Implementación pendiente** ⏳

