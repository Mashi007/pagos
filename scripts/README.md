# 🔧 SCRIPTS DE AUTOMATIZACIÓN

## 📋 **CONTENIDO DE ESTA CARPETA**

Esta carpeta contiene scripts de automatización para el sistema RapiCredit.

---

## 📁 **CARPETAS DISPONIBLES**

### **📜 [powershell/](./powershell/)**
- **Contenido**: Scripts PowerShell para operaciones del sistema
- **Archivos**: 5 scripts esenciales
- **Propósito**: Configuración, autenticación, testing y verificación
- **Estado**: FUNCIONALES Y NECESARIOS

---

## 🎯 **PROPÓSITO GENERAL**

Estos scripts proporcionan:
- ✅ **Automatización** de tareas repetitivas
- ✅ **Configuración** inicial del sistema
- ✅ **Testing** y verificación de funcionalidad
- ✅ **Carga de datos** de prueba
- ✅ **Monitoreo** de salud del sistema

---

## 🚀 **USO RÁPIDO**

### **Setup Inicial Completo:**
```powershell
cd scripts/powershell
. .\config_variables.ps1
. .\paso_0_obtener_token.ps1
. .\paso_manual_1_crear_asesor.ps1
. .\paso_manual_2_crear_cliente.ps1
. .\paso_7_verificar_sistema.ps1
```

### **Solo Verificación:**
```powershell
cd scripts/powershell
. .\paso_0_obtener_token.ps1
. .\paso_7_verificar_sistema.ps1
```

---

**📅 Última actualización**: 2025-10-16  
**🔧 Estado**: FUNCIONALES Y CERTIFICADOS
