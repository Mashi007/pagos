# 🔗 Guía: Integración de Templates de Meta con Sistema de Pagos

## 📋 **Resumen**

Esta guía explica cómo integrar templates de Meta WhatsApp con el sistema de pagos, permitiendo enviar notificaciones automáticas usando templates aprobados que cumplen con las políticas de Meta.

---

## 🎯 **Cómo Funciona la Integración**

### **Flujo Completo:**

1. **Sistema detecta cuota a notificar** (scheduler ejecuta job)
2. **Sistema construye variables** desde BD (cliente, préstamo, cuota)
3. **Sistema mapea tipo de notificación** → template de Meta
4. **Sistema extrae parámetros** del template desde variables
5. **Sistema envía mensaje** usando template de Meta con parámetros
6. **Meta procesa y envía** el mensaje al cliente

---

## 🔧 **Configuración del Sistema**

### **1. Mapeo de Tipos de Notificación a Templates**

**Archivo**: `backend/app/services/whatsapp_template_mapper.py`

El sistema tiene un mapeo predefinido:

```python
TEMPLATE_MAP = {
    "PAGO_5_DIAS_ANTES": "notificacion_pago_5_dias",
    "PAGO_3_DIAS_ANTES": "notificacion_pago_3_dias",
    "PAGO_1_DIA_ANTES": "notificacion_pago_1_dia",
    "PAGO_DIA_0": "notificacion_pago_dia_0",
    "MORA_1_DIA": "notificacion_mora_1_dia",
    "MORA_3_DIAS": "notificacion_mora_3_dias",
    "MORA_5_DIAS": "notificacion_mora_5_dias",
    "MORA_10_DIAS": "notificacion_mora_10_dias",
    "PREJUDICIAL": "notificacion_prejudicial",
}
```

**Para agregar nuevos tipos:**
1. Agrega el mapeo en `TEMPLATE_MAP`
2. Crea el template correspondiente en Meta Developers

---

## 📝 **Cómo Crear Templates en Meta Developers**

### **Paso 1: Acceder a Meta Developers**

1. Ve a [Meta Developers](https://developers.facebook.com/)
2. Selecciona tu App
3. Ve a **WhatsApp** → **Message Templates**

### **Paso 2: Crear Template**

1. Haz clic en **"Create Template"**
2. Selecciona categoría: **"UTILITY"** (para notificaciones)
3. Nombre del template: Debe coincidir con el mapeo (ej: `notificacion_pago_dia_0`)

### **Paso 3: Definir Contenido del Template**

**Ejemplo para "Notificación Pago Día 0":**

```
Nombre del Template: notificacion_pago_dia_0
Categoría: UTILITY
Idioma: Español (es)

Cuerpo del Mensaje:
Hola {{1}}, te recordamos que hoy {{2}} vence tu cuota de {{3}} por el monto de {{4}}. 
Por favor realiza el pago para evitar intereses de mora.

Parámetros:
{{1}} = Nombre del cliente
{{2}} = Fecha de vencimiento
{{3}} = Número de cuota
{{4}} = Monto de la cuota
```

**Formato en Meta:**
```
Hola {{1}}, te recordamos que hoy {{2}} vence tu cuota de {{3}} por el monto de {{4}}. 
Por favor realiza el pago para evitar intereses de mora.
```

### **Paso 4: Enviar para Aprobación**

1. Revisa el template
2. Haz clic en **"Submit for Review"**
3. Espera aprobación (puede tardar horas/días)

---

## 🔄 **Cómo el Sistema Extrae Variables**

### **Variables Disponibles:**

El sistema extrae automáticamente estas variables desde la BD:

- `nombre`: Nombre del cliente
- `monto`: Monto de la cuota
- `fecha_vencimiento`: Fecha de vencimiento (formato: DD/MM/YYYY)
- `numero_cuota`: Número de cuota
- `credito_id`: ID del préstamo
- `cedula`: Cédula del cliente
- `dias_atraso`: Días de atraso (si aplica)

### **Orden de Parámetros en Template:**

El sistema envía los parámetros en este orden:

1. **Nombre** (`nombre`)
2. **Monto** (`monto`)
3. **Fecha de Vencimiento** (`fecha_vencimiento`)
4. **Número de Cuota** (`numero_cuota`)
5. **ID de Crédito** (`credito_id`)
6. **Días de Atraso** (`dias_atraso`) - solo si aplica

**Ejemplo:**
```python
template_parameters = [
    {"text": "Juan Pérez"},           # {{1}} en template
    {"text": "150.00"},               # {{2}} en template
    {"text": "15/01/2024"},           # {{3}} en template
    {"text": "5"},                    # {{4}} en template
]
```

---

## 📊 **Ejemplo Completo: Template "Notificación Pago Día 0"**

### **1. Template en Meta Developers:**

**Nombre**: `notificacion_pago_dia_0`

**Cuerpo**:
```
Hola {{1}}, te recordamos que hoy {{2}} vence tu cuota {{3}} por el monto de {{4}} Bs. 
Por favor realiza el pago para evitar intereses de mora.
```

**Parámetros**:
- `{{1}}` = Nombre del cliente
- `{{2}}` = Fecha de vencimiento
- `{{3}}` = Número de cuota
- `{{4}}` = Monto de la cuota

### **2. Código del Sistema:**

```python
# El scheduler detecta cuota a notificar
tipo_notificacion = "PAGO_DIA_0"

# El sistema mapea a template
template_name = WhatsAppTemplateMapper.get_template_name("PAGO_DIA_0")
# Resultado: "notificacion_pago_dia_0"

# El sistema construye variables desde BD
variables = {
    "nombre": "Juan Pérez",
    "monto": "150.00",
    "fecha_vencimiento": "15/01/2024",
    "numero_cuota": "5",
    "credito_id": "123"
}

# El sistema extrae parámetros
template_parameters = [
    {"text": "Juan Pérez"},      # {{1}}
    {"text": "15/01/2024"},      # {{2}}
    {"text": "5"},               # {{3}}
    {"text": "150.00"}           # {{4}}
]

# El sistema envía usando template
await whatsapp_service.send_message(
    to_number="+584121234567",
    message=cuerpo,  # Se usa como fallback si template falla
    template_name="notificacion_pago_dia_0",
    template_parameters=template_parameters
)
```

### **3. Mensaje Final que Recibe el Cliente:**

```
Hola Juan Pérez, te recordamos que hoy 15/01/2024 vence tu cuota 5 por el monto de 150.00 Bs. 
Por favor realiza el pago para evitar intereses de mora.
```

---

## ⚙️ **Configuración Avanzada**

### **Personalizar Orden de Parámetros:**

Si necesitas un orden diferente de parámetros, modifica `extract_template_parameters` en `whatsapp_template_mapper.py`:

```python
@classmethod
def extract_template_parameters(cls, message: str, variables: Dict[str, str], template_name: Optional[str] = None) -> List[Dict[str, str]]:
    parameters = []
    
    # Orden personalizado según template_name
    if template_name == "notificacion_pago_dia_0":
        # Orden específico para este template
        if "nombre" in variables:
            parameters.append({"text": variables["nombre"]})
        if "fecha_vencimiento" in variables:
            parameters.append({"text": variables["fecha_vencimiento"]})
        if "numero_cuota" in variables:
            parameters.append({"text": variables["numero_cuota"]})
        if "monto" in variables:
            parameters.append({"text": variables["monto"]})
    else:
        # Orden por defecto
        for var_name in ["nombre", "monto", "fecha_vencimiento", "numero_cuota"]:
            if var_name in variables:
                parameters.append({"text": variables[var_name]})
    
    return parameters
```

### **Agregar Nuevos Tipos de Notificación:**

1. **Agrega el mapeo** en `whatsapp_template_mapper.py`:
```python
TEMPLATE_MAP = {
    # ... mapeos existentes ...
    "NUEVO_TIPO": "nuevo_template_meta",
}
```

2. **Crea el template** en Meta Developers con nombre `nuevo_template_meta`

3. **El sistema automáticamente** usará el template para ese tipo de notificación

---

## 🔍 **Verificación y Debugging**

### **Logs que Verás:**

**Si el template se usa correctamente:**
```
📋 [TEMPLATE] Usando template 'notificacion_pago_dia_0' con 4 parámetros para notificación PAGO_DIA_0
📋 [COMPLIANCE] Enviando template 'notificacion_pago_dia_0' a 584121234567
📤 [ENVÍO] Enviando mensaje a Meta API:
   Tipo: template
   Template: notificacion_pago_dia_0
✅ [COMPLIANCE] Mensaje WhatsApp enviado exitosamente
```

**Si hay error:**
```
⚠️ [TEMPLATE] Error extrayendo variables para template 'notificacion_pago_dia_0': ...
⚠️ [TEMPLATE] No se encontraron variables, usando mensaje completo como parámetro único
```

### **Verificar que el Template Funciona:**

1. **Revisa los logs** del backend después de enviar una notificación
2. **Busca**: `📋 [TEMPLATE]` para ver si se está usando el template
3. **Busca**: `✅ [COMPLIANCE]` para confirmar envío exitoso
4. **Verifica en Meta Developers** que el template esté aprobado

---

## ⚠️ **Notas Importantes**

1. **Templates Requieren Aprobación:**
   - Meta revisa cada template antes de aprobarlo
   - Puede tardar horas o días
   - Solo templates aprobados funcionan

2. **Orden de Parámetros:**
   - El orden de parámetros en el template de Meta debe coincidir con el orden que envía el sistema
   - Revisa el mapeo en `extract_template_parameters`

3. **Fallback a Mensaje Libre:**
   - Si no hay template configurado, el sistema usa mensaje libre
   - Si el template falla, el sistema intenta con mensaje libre
   - Mensajes libres solo funcionan dentro de ventana de 24h

4. **Variables Disponibles:**
   - El sistema extrae variables automáticamente desde la BD
   - Si falta una variable, se omite ese parámetro
   - Revisa `VariablesNotificacionService` para ver todas las variables disponibles

---

## 🚀 **Próximos Pasos**

1. **Crear templates en Meta Developers** para cada tipo de notificación
2. **Esperar aprobación** de Meta
3. **Verificar logs** después de enviar notificaciones
4. **Ajustar orden de parámetros** si es necesario
5. **Probar en modo pruebas** antes de producción

---

## 🔗 **Referencias**

- [Meta WhatsApp Business API - Message Templates](https://developers.facebook.com/docs/whatsapp/business-management-api/message-templates)
- [Documento de Compliance](Documentos/General/Configuracion/COMPLIANCE_WHATSAPP_META.md)
- [Problema de Mensajes No Llegan](Documentos/General/Configuracion/PROBLEMA_MENSAJES_NO_LLEGAN_WHATSAPP.md)

