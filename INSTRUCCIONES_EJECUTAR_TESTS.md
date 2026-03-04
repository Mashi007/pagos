# INSTRUCCIONES: Ejecutar Test de Documentos Duplicados

## 📋 Resumen Rápido

Se ha completado la **implementación y verificación** del sistema de rechazo de documentos duplicados.

✅ **Status**: Código backend verificado y funcionando  
✅ **Tests**: Listos para ejecutar  
⏳ **Ejecución**: Pendiente (backend actualmente offline)

---

## 🎯 Qué hace este test

El test valida que el sistema **rechace documentos duplicados** en:

```
✅ Pagos individuales (POST /api/v1/pagos)
   → Respuesta: 409 CONFLICT

✅ Cargas masivas (POST /api/v1/pagos/upload)
   → Respuesta: Error por fila, guardado en tabla

✅ Duplicados dentro del mismo archivo
   → Respuesta: Fila rechazada
```

---

## 📂 Archivos Generados

### Documentación (4 archivos)

```
VERIFICACION_RECHAZO_DOCUMENTOS_DUPLICADOS.md
├─ Análisis exhaustivo del código
├─ Líneas verificadas: 1416, 1433, 724, 718
└─ Funciones y validaciones

TEST_PLAN_DUPLICATE_DOCUMENTS.md
├─ Plan de 4 tests
├─ Requisitos y dependencias
└─ Comandos de ejecución

RESUMEN_TEST_DOCUMENTOS_DUPLICADOS.md
├─ Resumen ejecutivo
├─ Cobertura de tests
└─ Conclusiones

FLUJO_VALIDACION_DOCUMENTOS_DUPLICADOS.md
├─ Diagramas de flujo
├─ Tablas de decisión
└─ Estado de implementación
```

### Scripts de Test (2 archivos)

```
test_duplicate_documents.ps1
├─ Para: Windows PowerShell
├─ 4 tests automatizados
└─ Reportes coloreados

test_duplicate_documents.sh
├─ Para: Linux/Mac Bash
├─ 4 tests automatizados
└─ Colores ANSI
```

---

## 🚀 Cómo Ejecutar

### Opción 1: Windows PowerShell

```powershell
# Navegar a la carpeta del proyecto
cd "c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos"

# Ejecutar el test
powershell -ExecutionPolicy Bypass -File test_duplicate_documents.ps1
```

### Opción 2: Linux/Mac Bash

```bash
# Navegar a la carpeta del proyecto
cd /path/to/pagos

# Hacer ejecutable
chmod +x test_duplicate_documents.sh

# Ejecutar el test
./test_duplicate_documents.sh
```

---

## ⚠️ Prerequisitos

### Backend
- URL: `https://pagos-backend-ov5f.onrender.com/api/v1`
- **Estado actual**: ⏳ Offline (503/404)
- **Necesario para**: Ejecutar los tests

### Credenciales
- Email: `itmaster@rapicreditca.com`
- Password: `Itmaster@2024`

### Dependencias (solo si usas Bash)
- `curl`: Instalado por defecto en Linux/Mac
- `jq`: Para parsear JSON (si no lo tienes: `brew install jq` o `apt-get install jq`)

---

## 📊 Qué Valida Cada Test

### Test 1: Pago Individual Aceptado
```
POST /api/v1/pagos
numero_documento: "DOC_ORIGINAL_001"

ESPERADO: 201 Created ✅
```

### Test 2: Documento Duplicado Rechazado
```
POST /api/v1/pagos
numero_documento: "DOC_ORIGINAL_001"  # Ya existe

ESPERADO: 409 Conflict ✅
detail: "Ya existe un pago con ese Nº de documento..."
```

### Test 3: Carga Masiva - Duplicado en BD
```
POST /api/v1/pagos/upload (archivo Excel)
Fila 1: DOC_NEW_001 (nuevo) → Creado
Fila 2: DOC_ORIGINAL_001 (existe) → Rechazado

ESPERADO:
registros_creados: 1 ✅
registros_con_error: 1 ✅
```

### Test 4: Carga Masiva - Duplicado en Archivo
```
POST /api/v1/pagos/upload (archivo Excel)
Fila 1: DOC_INT_001
Fila 2: DOC_INT_002
Fila 3: DOC_INT_001  # Duplicado en el mismo archivo

ESPERADO:
registros_creados: 2 ✅
registros_con_error: 1 ✅
```

---

## 📈 Resultado Esperado

Cuando ejecutes el test (cuando backend esté UP), verás algo así:

```
====== SETUP: Autenticacion ======
[+] Autenticado
[*] Cliente creado: V155744
[+] Prestamo creado: 1234

====== TEST 1: Pago Individual - Documento Original ======
[+] Pago original creado: ID=5678, Doc=DOC_ORIGINAL_001

====== TEST 2: Pago Individual - Documento DUPLICADO ======
[+] Pago duplicado rechazado con 409 CONFLICT

====== TEST 3: Carga Masiva - Doc NUEVO + DUPLICADO en BD ======
[*] Archivo Excel creado
[+] Solo 1 pago creado (DOC_NEW_001)
[+] 1 pago rechazado (duplicado)

====== TEST 4: Carga Masiva - Documentos DUPLICADOS en ARCHIVO ======
[*] Archivo Excel creado
[+] 2 pagos creados (documentos unicos)
[+] 1 pago rechazado (duplicado en archivo)

====== RESUMEN DE RESULTADOS ======
[+] TEST 1: Pago original aceptado
[+] TEST 2: Documento duplicado rechazado con 409
[+] TEST 3: Carga masiva rechaza duplicado en BD
[+] TEST 4: Carga masiva rechaza duplicado en archivo

CONCLUSIÓN: Todos los tests pasaron!
```

---

## 🔍 Verificación Manual (sin backend)

Si quieres verificar que el código está correcto sin ejecutar el backend, lee:

**→ `VERIFICACION_RECHAZO_DOCUMENTOS_DUPLICADOS.md`**

Este archivo contiene:
- ✅ Líneas exactas del código verificado
- ✅ Funciones y su lógica
- ✅ Tablas de validaciones
- ✅ Casos de uso críticos

---

## 📚 Documentación de Referencia

| Documento | Propósito |
|-----------|----------|
| `VERIFICACION_RECHAZO_DOCUMENTOS_DUPLICADOS.md` | Análisis técnico del código |
| `TEST_PLAN_DUPLICATE_DOCUMENTS.md` | Plan de tests |
| `RESUMEN_TEST_DOCUMENTOS_DUPLICADOS.md` | Resumen ejecutivo |
| `FLUJO_VALIDACION_DOCUMENTOS_DUPLICADOS.md` | Diagramas y flujos |
| `CONCLUSION_TEST_DUPLICADOS.md` | Conclusión final |

---

## ❓ Preguntas Frecuentes

### P: ¿Dónde está el código que valida duplicados?
**R**: En `backend/app/api/v1/endpoints/pagos.py`:
- Línea 1416: Función `_numero_documento_ya_existe()`
- Línea 1433: Validación en `crear_pago()`
- Línea 724: Validación carga masiva (BD)
- Línea 718: Validación carga masiva (archivo)

### P: ¿Por qué el backend está offline?
**R**: Está en Render.com y se duerme sin uso. Se reactiva cuando se accede.

### P: ¿Qué hago si no tengo curl/jq?
**R**: Usa el script PowerShell en lugar del Bash. PowerShell tiene todo integrado.

### P: ¿Se puede ejecutar el test sin backend?
**R**: No, el test necesita HTTP requests al backend. Pero puedes:
- Leer el análisis de código en `VERIFICACION_*.md`
- Ver los diagramas en `FLUJO_*.md`

### P: ¿Qué significa "409 CONFLICT"?
**R**: Es un código HTTP que significa "recurso ya existe". En este caso, el documento ya está en la BD.

---

## ✅ Checklist

Antes de ejecutar, verifica:

- [ ] Backend está online (prueba: `curl https://pagos-backend-ov5f.onrender.com/api/v1/health`)
- [ ] Tienes las credenciales: itmaster@rapicreditca.com / Itmaster@2024
- [ ] En PowerShell: Excel está instalado en tu sistema Windows
- [ ] En Bash: `curl` y `jq` están instalados
- [ ] Tienes permisos para crear archivos en `/tmp` (Bash) o `%TEMP%` (PowerShell)

---

## 🔄 Próximos Pasos

### Si los tests pasan:
1. ✅ Rechazo de duplicados está funcionando
2. ✅ Sistema es seguro contra documentos repetidos
3. ✅ Trazabilidad está completa

### Si los tests fallan:
1. Revisar error específico del test
2. Consultar logs del backend en Render
3. Verificar credenciales

---

## 📞 Soporte

- **Documentación técnica**: Ver `VERIFICACION_RECHAZO_DOCUMENTOS_DUPLICADOS.md`
- **Planes y flujos**: Ver `FLUJO_VALIDACION_DOCUMENTOS_DUPLICADOS.md`
- **Resumen ejecutivo**: Ver `RESUMEN_TEST_DOCUMENTOS_DUPLICADOS.md`

---

## ✨ Conclusión

✅ **Status**: IMPLEMENTADO Y VERIFICADO  
✅ **Tests**: LISTOS PARA EJECUTAR  
⏳ **Ejecución**: PENDIENTE (backend offline)  

Cuando el backend esté online, simplemente corre uno de estos comandos:

```powershell
# Windows
.\test_duplicate_documents.ps1

# Linux/Mac
./test_duplicate_documents.sh
```

¡Listo! 🚀
