# 🔍 VALIDADORES DISPONIBLES EN EL SISTEMA

## 📋 **RESUMEN GENERAL**

El sistema RAPICREDIT cuenta con un conjunto completo de validadores organizados en dos módulos principales:

1. **Validadores Avanzados** (`validators_service.py`) - Con auto-formateo y soporte multi-país
2. **Validadores Básicos** (`validators.py`) - Funciones de validación específicas

---

## 🚀 **VALIDADORES AVANZADOS (validators_service.py)**

### **1. 📱 ValidadorTelefono**
- **Países soportados:** Venezuela, República Dominicana, Colombia
- **Funcionalidades:**
  - Auto-formateo de números telefónicos
  - Validación de operadoras por país
  - Formato internacional estándar
- **Ejemplos:**
  - `4241234567` → `+58 424 1234567`
  - `8091234567` → `+1 809 1234567`
  - `3001234567` → `+57 300 1234567`

### **2. 🆔 ValidadorCedula**
- **Países soportados:** Venezuela, República Dominicana, Colombia
- **Funcionalidades:**
  - Validación de formato por país
  - Auto-formateo con prefijos
  - Validación de dígitos verificadores
- **Ejemplos:**
  - `12345678` → `V12345678` (Venezuela)
  - `1234567` → `001-1234567-8` (Rep. Dominicana)
  - `12345678` → `12345678` (Colombia)

### **3. 📅 ValidadorFecha**
- **Funcionalidades:**
  - Validación con reglas de negocio
  - Múltiples formatos de entrada
  - Validación de fechas futuras/pasadas
  - Integración con calendarios
- **Reglas de negocio:**
  - Fecha de entrega: No puede ser futura
  - Fecha de pago: Máximo 1 día en el futuro

### **4. 💰 ValidadorMonto**
- **Funcionalidades:**
  - Validación con límites por tipo
  - Auto-formateo con separadores de miles
  - Validación de rangos específicos
- **Límites:**
  - Total financiamiento: $100 - $50,000,000
  - Formato display: `$X,XXX.XX`

### **5. 📊 ValidadorAmortizaciones**
- **Funcionalidades:**
  - Validación de rango 1-84 meses
  - Conversión automática de decimales
  - Validación de enteros
- **Ejemplo:** `60.5` → `60 meses`

### **6. 📧 ValidadorEmail**
- **Funcionalidades:**
  - Validación RFC 5322
  - Normalización de formato
  - Lista de dominios bloqueados
- **Ejemplo:** `USUARIO@GMAIL.COM` → `usuario@gmail.com`

---

## 🔧 **VALIDADORES BÁSICOS (validators.py)**

### **Documentos de Identidad:**
- `validate_dni(dni)` - DNI/Cédula (7-11 dígitos)
- `validate_ruc(ruc)` - RUC paraguayo (XXXXXXXX-X)
- `format_dni(dni)` - Formateo con puntos y guiones

### **Comunicaciones:**
- `validate_phone(phone)` - Teléfonos paraguayos
- `validate_email(email)` - Emails básicos
- `format_phone(phone)` - Formateo telefónico

### **Montos y Finanzas:**
- `validate_positive_amount(amount)` - Montos positivos
- `validate_percentage(percentage)` - Porcentajes (0-100%)
- `validate_tasa_interes(tasa)` - Tasas de interés (0-100%)
- `validate_monto_vs_ingreso()` - Cuota vs ingreso (máx 40%)
- `validate_payment_amount()` - Validación de pagos con tolerancia

### **Fechas:**
- `validate_date_range()` - Rango de fechas válido
- `validate_future_date()` - Fechas futuras
- `validate_past_date()` - Fechas pasadas
- `validate_date_not_future()` - Fechas no futuras

### **Préstamos y Cuotas:**
- `validate_cuotas(numero_cuotas)` - Cuotas (1-360)
- `validate_codigo_prestamo(codigo)` - Código PREST-YYYYMMDD-XXXX

### **Bancarios:**
- `validate_cuenta_bancaria(cuenta)` - Cuentas bancarias (8-20 dígitos)

### **Utilidades:**
- `sanitize_string(text)` - Sanitización de texto
- `normalize_text(text)` - Normalización para búsquedas

---

## 🌍 **CONFIGURACIÓN POR PAÍS**

### **Venezuela:**
- **Código:** +58
- **Operadoras:** 424, 414, 416, 426, 412, 425
- **Cédula:** V12345678

### **República Dominicana:**
- **Código:** +1
- **Operadoras:** 809, 829, 849
- **Cédula:** 001-1234567-8

### **Colombia:**
- **Código:** +57
- **Operadoras:** 300, 301, 302, 310-323
- **Cédula:** 12345678

---

## 🔗 **ENDPOINTS DISPONIBLES**

### **Validación Individual:**
- `POST /api/v1/validadores/validar-campo` - Validar campo específico
- `GET /api/v1/validadores/configuracion` - Configuración de validadores
- `GET /api/v1/validadores/verificacion-validadores` - Estado del sistema

### **Corrección Masiva:**
- `POST /api/v1/validadores/corregir-datos` - Corrección de datos de cliente
- `GET /api/v1/validadores/ejemplos-correccion` - Ejemplos de corrección

---

## ⚙️ **CARACTERÍSTICAS ESPECIALES**

### **Auto-Formateo:**
- ✅ Teléfonos
- ✅ Cédulas
- ✅ Emails
- ✅ Montos
- ❌ Fechas (requiere calendario)
- ❌ Amortizaciones

### **Validación en Tiempo Real:**
- ✅ Todos los validadores soportan validación en tiempo real
- ✅ Respuesta inmediata en formularios
- ✅ Mensajes de error específicos

### **Reglas de Negocio:**
- Fecha de entrega: No puede ser futura
- Fecha de pago: Máximo 1 día en el futuro
- Monto de pago: No puede exceder saldo pendiente
- Total financiamiento: Entre $100 y $50,000,000
- Amortizaciones: Entre 1 y 84 meses

---

## 🎯 **EJEMPLOS DE USO**

### **Validación de Teléfono:**
```python
resultado = ValidadorTelefono.validar_y_formatear_telefono(
    "4241234567", 
    "VENEZUELA"
)
# Resultado: {"valido": True, "valor_formateado": "+58 424 1234567"}
```

### **Validación de Cédula:**
```python
resultado = ValidadorCedula.validar_y_formatear_cedula(
    "12345678", 
    "VENEZUELA"
)
# Resultado: {"valido": True, "valor_formateado": "V12345678"}
```

### **Validación de Monto:**
```python
resultado = ValidadorMonto.validar_y_formatear_monto(
    "15000", 
    "financiamiento"
)
# Resultado: {"valido": True, "valor_formateado": "15000.00", "display": "$15,000.00"}
```

---

## 📊 **ESTADO DEL SISTEMA**

- ✅ **6 Validadores Avanzados** implementados
- ✅ **20+ Validadores Básicos** implementados
- ✅ **3 Países** soportados
- ✅ **Auto-formateo** en 5 de 6 validadores
- ✅ **Validación en tiempo real** en todos
- ✅ **Reglas de negocio** integradas

---

**El sistema de validadores está completamente funcional y listo para uso en producción.** 🚀
