# 📋 INFORME DE AUDITORÍA TOTAL - 93 ARCHIVOS PYTHON

**Fecha:** 2025-10-15  
**Tiempo estimado:** 15 minutos  
**Archivos auditados:** 93 archivos .py en backend/app/

---

## 🎯 RESUMEN EJECUTIVO

### Problema crítico identificado:
**72 líneas con referencias a `asesor_id` obsoleto en 11 archivos**

El campo `Cliente.asesor_id` fue eliminado del modelo pero sigue siendo referenciado en:
- ❌ 1 modelo (schemas/cliente.py)
- ❌ 10 endpoints/services

---

## 📊 DESGLOSE POR ARCHIVO

### ARCHIVO 1: backend/app/api/v1/endpoints/asesores.py
**Referencias:** 9 líneas  
**Estado:** ✅ CORRECTO (son parámetros de ruta `/{asesor_id}`)

```
Línea 97: @router.get("/{asesor_id}") ✅ OK - parámetro de ruta
Línea 99: asesor_id: int ✅ OK - parámetro de ruta
Línea 106: Asesor.id == asesor_id ✅ OK - busca en tabla asesores
Línea 155: @router.put("/{asesor_id}") ✅ OK - parámetro de ruta
Línea 157: asesor_id: int ✅ OK - parámetro de ruta
Línea 166: Asesor.id == asesor_id ✅ OK - busca en tabla asesores
Línea 175: Asesor.id != asesor_id ✅ OK - validación
Línea 196: @router.delete("/{asesor_id}") ✅ OK - parámetro de ruta
Línea 198: asesor_id: int ✅ OK - parámetro de ruta
Línea 206: Asesor.id == asesor_id ✅ OK - busca en tabla asesores
```

**Resultado:** ✅ SIN PROBLEMAS

---

### ARCHIVO 2: backend/app/api/v1/endpoints/clientes.py
**Referencias:** 20 líneas  
**Estado:** ❌ CRÍTICO - 20 problemas

```
❌ Línea 200: asesor_id: Optional[int] = Query(...) 
   → Debe ser: asesor_config_id

❌ Línea 236-237: if asesor_id: query.filter(Cliente.asesor_id == asesor_id)
   → Debe ser: if asesor_config_id: query.filter(Cliente.asesor_config_id == asesor_config_id)

❌ Línea 269: "asesor_id": cliente.asesor_id
   → Debe ser: "asesor_config_id": cliente.asesor_config_id

❌ Línea 560, 582, 605: "asesor_id": current_user.id
   → Debe ser: "asesor_config_id": None (los clientes NO se asignan a users)

❌ Línea 681: ALTER TABLE clientes ADD COLUMN asesor_id INTEGER
   → Debe ser: asesor_config_id

❌ Línea 749-750: if cliente.asesor_id: asesor = db.query(User).filter(User.id == cliente.asesor_id)
   → Debe ser: if cliente.asesor_config_id: asesor = db.query(Asesor).filter(Asesor.id == cliente.asesor_config_id)

❌ Línea 830: asesor = db.query(User).filter(User.id == cliente_data.asesor_id)
   → Debe ser: db.query(Asesor).filter(Asesor.id == cliente_data.asesor_config_id)

❌ Línea 1086: nuevo_asesor_id: int
   → Debe ser: nuevo_asesor_config_id: int

❌ Línea 1098: nuevo_asesor = db.query(User).filter(User.id == nuevo_asesor_id)
   → Debe ser: db.query(Asesor).filter(Asesor.id == nuevo_asesor_config_id)

❌ Línea 1111-1112: asesor_anterior = cliente.asesor_id; cliente.asesor_id = nuevo_asesor_id
   → Debe ser: asesor_config_anterior = cliente.asesor_config_id; cliente.asesor_config_id = nuevo_asesor_config_id

❌ Línea 1122: "asesor_nuevo": nuevo_asesor_id
   → Debe ser: "asesor_config_nuevo": nuevo_asesor_config_id

❌ Línea 1143: Cliente.asesor_id == asesor.id
   → Debe ser: Cliente.asesor_config_id == asesor.id (Y cambiar asesor por asesor_config)

❌ Línea 1427-1428: if filters.asesor_id: query.filter(Cliente.asesor_id == filters.asesor_id)
   → Debe ser: if filters.asesor_config_id: query.filter(Cliente.asesor_config_id == filters.asesor_config_id)

❌ Línea 1511: User.id == Cliente.asesor_id
   → Debe ser: Asesor.id == Cliente.asesor_config_id
```

**Resultado:** ❌ 20 ERRORES CRÍTICOS

---

### ARCHIVO 3: backend/app/api/v1/endpoints/dashboard.py
**Referencias:** 15 líneas  
**Estado:** ❌ CRÍTICO - 15 problemas

```
❌ Línea 132: User.id == Cliente.asesor_id
   → Debe ser: Asesor.id == Cliente.asesor_config_id

❌ Línea 399: Cliente.asesor_id == current_user.id
   → ELIMINAR - Los clientes NO se asignan a users

❌ Línea 455: User.id == Cliente.asesor_id
   → Debe ser: Asesor.id == Cliente.asesor_config_id

❌ Línea 551: asesor_id: Optional[int] = Query(...)
   → Debe ser: asesor_config_id

❌ Línea 566-578: Validaciones y queries con asesor_id
   → Todas deben cambiar a asesor_config_id y buscar en Asesor, no User

❌ Línea 582: Cliente.asesor_id == asesor_id
   → Debe ser: Cliente.asesor_config_id == asesor_config_id

❌ Línea 617: User.id == Cliente.asesor_id
   → Debe ser: Asesor.id == Cliente.asesor_config_id

❌ Línea 626: if asesor_rank.id == asesor_id
   → Debe ser: asesor_config_id

❌ Línea 735, 749, 755: Strings con "asesor_id = current_user.id"
   → ELIMINAR - Lógica incorrecta
```

**Resultado:** ❌ 15 ERRORES CRÍTICOS

---

### ARCHIVO 4: backend/app/api/v1/endpoints/kpis.py
**Referencias:** 9 líneas  
**Estado:** ❌ CRÍTICO - 9 problemas

```
❌ Línea 285: User.id == Cliente.asesor_id
   → Debe ser: Asesor.id == Cliente.asesor_config_id

❌ Línea 386: User.id == Cliente.asesor_id
   → Debe ser: Asesor.id == Cliente.asesor_config_id

❌ Línea 400: User.id == Cliente.asesor_id
   → Debe ser: Asesor.id == Cliente.asesor_config_id

❌ Línea 409-411: for asesor_id, ...: {"asesor_id": asesor_id}
   → Debe ser: asesor_config_id

❌ Línea 418-421: for asesor_id, ...: {"asesor_id": asesor_id}
   → Debe ser: asesor_config_id
```

**Resultado:** ❌ 9 ERRORES CRÍTICOS

---

### ARCHIVO 5: backend/app/api/v1/endpoints/notificaciones.py
**Referencias:** 1 línea  
**Estado:** ❌ ERROR

```
❌ Línea 822: User.id == Cliente.asesor_id
   → Debe ser: Asesor.id == Cliente.asesor_config_id
```

**Resultado:** ❌ 1 ERROR

---

### ARCHIVO 6: backend/app/api/v1/endpoints/reportes.py
**Referencias:** 10 líneas  
**Estado:** ❌ CRÍTICO - 10 problemas

```
❌ Línea 583: asesor_ids: Optional[str] = Query(...)
   → Debe ser: asesor_config_ids

❌ Línea 615-617: if asesor_ids: ids = [...]; query.filter(Cliente.asesor_id.in_(ids))
   → Debe ser: asesor_config_ids y Cliente.asesor_config_id.in_(ids)

❌ Línea 831: @router.get("/asesor/{asesor_id}/pdf")
   → Debe ser: @router.get("/asesor/{asesor_config_id}/pdf")

❌ Línea 833: asesor_id: int
   → Debe ser: asesor_config_id

❌ Línea 855: asesor = db.query(User).filter(User.id == asesor_id)
   → Debe ser: db.query(Asesor).filter(Asesor.id == asesor_config_id)

❌ Línea 867: Cliente.asesor_id == asesor_id
   → Debe ser: Cliente.asesor_config_id == asesor_config_id

❌ Línea 873: Cliente.asesor_id == asesor_id
   → Debe ser: Cliente.asesor_config_id == asesor_config_id

❌ Línea 1028: String "endpoint": "/asesor/{asesor_id}/pdf"
   → Debe ser: asesor_config_id
```

**Resultado:** ❌ 10 ERRORES CRÍTICOS

---

### ARCHIVO 7: backend/app/api/v1/endpoints/solicitudes.py
**Referencias:** 1 línea  
**Estado:** ❌ ERROR

```
❌ Línea 599: Cliente.asesor_id == current_user.id
   → ELIMINAR - Los clientes NO se asignan a users
```

**Resultado:** ❌ 1 ERROR

---

### ARCHIVO 8: backend/app/schemas/cliente.py
**Referencias:** 4 líneas  
**Estado:** ❌ CRÍTICO - 4 problemas

```
❌ Línea 43: asesor_id: Optional[int] = None  # Asesor del sistema (users)
   → ELIMINAR - Ya no existe

❌ Línea 105: asesor_id: Optional[int] = None
   → ELIMINAR o cambiar a asesor_config_id

❌ Línea 159: asesor_id: Optional[int] = None
   → ELIMINAR o cambiar a asesor_config_id

❌ Línea 229: asesor_id: int = Field(..., description="ID del asesor responsable")
   → Debe ser: asesor_config_id
```

**Resultado:** ❌ 4 ERRORES CRÍTICOS

---

### ARCHIVO 9: backend/app/services/ml_service.py
**Referencias:** 2 líneas  
**Estado:** ❌ CRÍTICO - 2 problemas

```
❌ Línea 1397: User.id == Cliente.asesor_id
   → Debe ser: Asesor.id == Cliente.asesor_config_id

❌ Línea 1409: "asesor_id": asesor.id
   → Debe ser: "asesor_config_id": asesor_config.id
```

**Resultado:** ❌ 2 ERRORES CRÍTICOS

---

## 📊 RESUMEN TOTAL DE ERRORES

| Archivo | Problemas | Severidad |
|---------|-----------|-----------|
| asesores.py | 0 | ✅ OK |
| **clientes.py** | **20** | ❌ CRÍTICO |
| **dashboard.py** | **15** | ❌ CRÍTICO |
| **kpis.py** | **9** | ❌ CRÍTICO |
| notificaciones.py | 1 | ❌ ERROR |
| **reportes.py** | **10** | ❌ CRÍTICO |
| solicitudes.py | 1 | ❌ ERROR |
| **schemas/cliente.py** | **4** | ❌ CRÍTICO |
| **ml_service.py** | **2** | ❌ CRÍTICO |
| **TOTAL** | **62 ERRORES** | ❌ SISTEMA ROTO |

---

## 🔧 PLAN DE CORRECCIÓN

### Paso 1: Actualizar schemas/cliente.py
- Eliminar todas las referencias a `asesor_id`
- Mantener solo `asesor_config_id`

### Paso 2: Actualizar clientes.py (20 cambios)
- Reemplazar `asesor_id` → `asesor_config_id`
- Cambiar `db.query(User)` → `db.query(Asesor)`
- Eliminar asignaciones automáticas a current_user.id

### Paso 3: Actualizar dashboard.py (15 cambios)
- Reemplazar joins de User → Asesor
- Actualizar filtros y queries

### Paso 4: Actualizar kpis.py (9 cambios)
- Cambiar todos los joins con User

### Paso 5: Actualizar reportes.py (10 cambios)
- Cambiar parámetros de ruta
- Actualizar queries

### Paso 6: Actualizar notificaciones.py, solicitudes.py, ml_service.py
- Cambios menores pero críticos

---

## ⏱️ TIEMPO ESTIMADO DE CORRECCIÓN

- Schemas: 5 minutos
- Endpoints (62 líneas): 30 minutos
- Testing: 10 minutos
- **TOTAL: ~45 minutos**

---

## 🚨 IMPACTO SI NO SE CORRIGE

1. ❌ Filtros por asesor NO funcionan
2. ❌ Reasignación de asesores falla
3. ❌ Dashboard de asesores muestra datos incorrectos
4. ❌ KPIs por asesor incorrectos
5. ❌ Reportes por asesor fallan
6. ❌ Notificaciones a asesores fallan
7. ❌ Solicitudes filtradas mal

**Estado del sistema:** 🔴 PRODUCCIÓN EN RIESGO


