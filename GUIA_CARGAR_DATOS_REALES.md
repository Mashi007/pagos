# 📘 GUÍA MAESTRA PARA CARGAR DATOS REALES

## 🎯 OBJETIVO
Cargar datos reales en el sistema para resolver los errores 503 y tener el sistema 100% funcional.

---

## ⚠️ IMPORTANTE ANTES DE EMPEZAR

### **Los errores 503 son NORMALES porque las tablas están vacías:**
- ❌ `/api/v1/clientes/` - Error 503 (tabla vacía)
- ❌ `/api/v1/pagos/` - Error 503 (tabla vacía)
- ❌ `/api/v1/reportes/cartera` - Error 503 (sin datos)

### **Una vez que ingreses datos reales, TODO funcionará correctamente** ✅

---

## 📋 PROCESO COMPLETO (7 PASOS)

### **ORDEN OBLIGATORIO DE EJECUCIÓN:**

```
┌──────────────────────────────────────────────────┐
│ PASO 0: Obtener Token                           │
│ Script: paso_0_obtener_token.ps1                │
└──────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────┐
│ PASO 1: Crear Asesores                          │
│ Script: paso_1_crear_asesores.ps1               │
│ Depende de: Token                                 │
└──────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────┐
│ PASO 2: Crear Concesionarios                    │
│ Script: paso_2_crear_concesionarios.ps1         │
│ Depende de: Token                                 │
└──────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────┐
│ PASO 3: Crear Modelos de Vehículos              │
│ Script: paso_3_crear_modelos_vehiculos.ps1      │
│ Depende de: Token                                 │
└──────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────┐
│ PASO 4: Crear Clientes ⭐ MÁS IMPORTANTE         │
│ Script: paso_4_crear_clientes.ps1               │
│ Depende de: Token, Asesores                      │
└──────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────┐
│ PASO 5: Crear Préstamos                         │
│ Script: paso_5_crear_prestamos.ps1              │
│ Depende de: Token, Clientes                      │
└──────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────┐
│ PASO 6: Registrar Pagos                         │
│ Script: paso_6_crear_pagos.ps1                  │
│ Depende de: Token, Préstamos                     │
└──────────────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────┐
│ PASO 7: Verificar Sistema Completo              │
│ Script: paso_7_verificar_sistema.ps1            │
└──────────────────────────────────────────────────┘
```

---

## 🚀 INSTRUCCIONES DE EJECUCIÓN

### **OPCIÓN 1: Ejecución Paso a Paso (Recomendada)**

```powershell
# Paso 0: Obtener token
powershell -ExecutionPolicy Bypass -File paso_0_obtener_token.ps1

# Paso 1: Crear asesores
powershell -ExecutionPolicy Bypass -File paso_1_crear_asesores.ps1

# Paso 2: Crear concesionarios
powershell -ExecutionPolicy Bypass -File paso_2_crear_concesionarios.ps1

# Paso 3: Crear modelos de vehículos
powershell -ExecutionPolicy Bypass -File paso_3_crear_modelos_vehiculos.ps1

# Paso 4: Crear clientes (IMPORTANTE: Modifica los IDs de asesores antes)
powershell -ExecutionPolicy Bypass -File paso_4_crear_clientes.ps1

# Paso 5: Crear préstamos (IMPORTANTE: Modifica los IDs de clientes antes)
powershell -ExecutionPolicy Bypass -File paso_5_crear_prestamos.ps1

# Paso 6: Registrar pagos (IMPORTANTE: Modifica los IDs de préstamos antes)
powershell -ExecutionPolicy Bypass -File paso_6_crear_pagos.ps1

# Paso 7: Verificar sistema completo
powershell -ExecutionPolicy Bypass -File paso_7_verificar_sistema.ps1
```

### **OPCIÓN 2: Ejecución Automática (Todos los pasos)**

```powershell
# Ejecutar todos los pasos en secuencia
& paso_0_obtener_token.ps1
& paso_1_crear_asesores.ps1
& paso_2_crear_concesionarios.ps1
& paso_3_crear_modelos_vehiculos.ps1
& paso_4_crear_clientes.ps1
& paso_5_crear_prestamos.ps1
& paso_6_crear_pagos.ps1
& paso_7_verificar_sistema.ps1
```

---

## ⚙️ PERSONALIZACIÓN DE DATOS

### **MODIFICAR DATOS ANTES DE EJECUTAR:**

#### **Paso 1 - Asesores:**
Edita `paso_1_crear_asesores.ps1` y modifica:
```powershell
$asesores = @(
    @{
        nombre = "TU_NOMBRE"
        apellido = "TU_APELLIDO"
        email = "TU_EMAIL@rapicreditca.com"
        telefono = "TU_TELEFONO"
        especialidad = "TU_ESPECIALIDAD"
        activo = $true
    }
)
```

#### **Paso 4 - Clientes (MUY IMPORTANTE):**
Edita `paso_4_crear_clientes.ps1` y **MODIFICA LOS IDs**:
```powershell
# USA IDs REALES de asesores que creaste en paso_1
asesor_config_id = 1  # CAMBIA ESTO
```

#### **Paso 5 - Préstamos (MUY IMPORTANTE):**
Edita `paso_5_crear_prestamos.ps1` y **MODIFICA LOS IDs**:
```powershell
# USA IDs REALES de clientes que creaste en paso_4
cliente_id = 1  # CAMBIA ESTO
```

#### **Paso 6 - Pagos (MUY IMPORTANTE):**
Edita `paso_6_crear_pagos.ps1` y **MODIFICA LOS IDs**:
```powershell
# USA IDs REALES de préstamos que creaste en paso_5
prestamo_id = 1  # CAMBIA ESTO
```

---

## ✅ RESULTADO ESPERADO

### **Antes de cargar datos:**
```
❌ Clientes: Error 503
❌ Pagos: Error 503
❌ Reportes: Error 503
```

### **Después de cargar datos:**
```
✅ Asesores: 3 registros
✅ Concesionarios: 3 registros
✅ Modelos Vehículos: 6 registros
✅ Clientes: 3 registros
✅ Préstamos: 3 registros
✅ Pagos: 6 registros
✅ Reportes: Funcionando correctamente
```

---

## 🎯 PUNTOS CLAVE

1. **El token se obtiene solo UNA VEZ** (Paso 0) y se reutiliza en todos los demás pasos
2. **Guarda los IDs** que se crean en cada paso para usarlos en los siguientes
3. **El orden ES IMPORTANTE** - No puedes crear clientes sin asesores, ni préstamos sin clientes
4. **Modifica los datos de ejemplo** con tu información real antes de ejecutar
5. **Los scripts incluyen validaciones** - Si algo falla, te muestra el error claramente

---

## 📊 ESTRUCTURA DE DATOS

```
Asesores (independientes)
    ↓
Concesionarios (independientes)
    ↓
Modelos de Vehículos (independientes)
    ↓
Clientes (necesitan: Asesores)
    ↓
Préstamos (necesitan: Clientes)
    ↓
Pagos (necesitan: Préstamos)
```

---

## 🆘 SOLUCIÓN DE PROBLEMAS

### **Error: "Token no encontrado"**
**Solución:** Ejecuta primero `paso_0_obtener_token.ps1`

### **Error: "No se pudo crear el cliente"**
**Solución:** Verifica que el `asesor_config_id` sea un ID real de asesor

### **Error: "No se pudo crear el préstamo"**
**Solución:** Verifica que el `cliente_id` sea un ID real de cliente

### **Error: "No se pudo registrar el pago"**
**Solución:** Verifica que el `prestamo_id` sea un ID real de préstamo

### **Error 401: Unauthorized**
**Solución:** El token expiró. Ejecuta de nuevo `paso_0_obtener_token.ps1`

---

## 📞 VERIFICACIÓN MANUAL (Opcional)

Si prefieres verificar en el navegador:

1. Ve a: `https://pagos-f2qf.onrender.com/docs`
2. Haz click en "Authorize"
3. Ingresa el token obtenido en Paso 0
4. Prueba cada endpoint manualmente

---

## 🎉 CONFIRMACIÓN FINAL

Después de ejecutar todos los pasos, el script `paso_7_verificar_sistema.ps1` te mostrará:

```
🎉 EXCELENTE! SISTEMA 100% FUNCIONAL 🎉
Todos los endpoints funcionan correctamente con datos reales
El sistema está listo para producción
```

---

**Fecha:** 2025-10-16  
**URL del Sistema:** https://pagos-f2qf.onrender.com  
**Usuario:** itmaster@rapicreditca.com  
**Documentación API:** https://pagos-f2qf.onrender.com/docs  

---

## 🚀 ¿LISTO PARA EMPEZAR?

Ejecuta el primer script:
```powershell
powershell -ExecutionPolicy Bypass -File paso_0_obtener_token.ps1
```

¡Y sigue las instrucciones en pantalla!

