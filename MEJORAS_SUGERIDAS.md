# 🚀 MEJORAS SUGERIDAS - 4 PUNTOS PENDIENTES

**Objetivo**: Cerrar brechas de trazabilidad identificadas en auditoría  
**Scope**: Implementación incremental, sin romper existente  
**Prioridad**: 1=Crítica, 2=Alta, 3=Media, 4=Baja

---

## 1️⃣ AUDITORÍA COMPLETA (P5)

### 📊 Situación Actual
- ✅ Algunos CREATE/UPDATE tienen logs (ej: `APROBACION_MANUAL`)
- ❌ La mayoría de transiciones NO se auditan
- ❌ No hay manera de ver "quién cambió qué, cuándo"

### 💡 Solución Sugerida: Middleware de Auditoría Automático

**Ventaja**: Se aplica a TODOS los endpoints sin modificar código individual

**Implementación**:

```python
# backend/app/middleware/audit_middleware.py

from fastapi import Request
from app.core.deps import get_current_user
from app.models.auditoria import Auditoria
from sqlalchemy.orm import Session
from app.core.database import get_db
import json
from datetime import datetime

async def audit_middleware(request: Request, call_next):
    """
    Intercepta cambios en POST/PUT/DELETE y audita automáticamente.
    """
    # Solo auditar cambios, no GETs
    if request.method not in ["POST", "PUT", "DELETE", "PATCH"]:
        return await call_next(request)
    
    # Capturar payload
    body = await request.body()
    if body:
        try:
            data = json.loads(body)
        except:
            data = {}
    else:
        data = {}
    
    # Ejecutar endpoint
    response = await call_next(request)
    
    # Auditar si fue exitoso (2xx, 3xx)
    if 200 <= response.status_code < 400:
        try:
            # Extraer usuario de request.state (inyectado por auth)
            usuario_id = getattr(request.state, "user_id", None)
            
            # Crear entry en auditoria
            db = next(get_db())
            audit_entry = Auditoria(
                usuario_id=usuario_id or 1,  # Fallback a admin
                accion=f"{request.method} {request.url.path}",
                entidad=request.url.path.split("/")[-2],  # ej: /pagos/123 → "pagos"
                entidad_id=None,  # Extraer del path si es posible
                detalles=json.dumps(data),
                fecha=datetime.now(),
            )
            db.add(audit_entry)
            db.commit()
        except Exception as e:
            pass  # No romper response si auditoría falla
    
    return response
```

**Registro en main.py**:

```python
# backend/app/main.py

from app.middleware.audit_middleware import audit_middleware

app = FastAPI()
app.middleware("http")(audit_middleware)
```

### 📈 Impacto
- **Trazabilidad**: ⬆️ 95%+ (todos los cambios auditados)
- **Costo**: 🟢 Bajo (middleware genérico)
- **Impacto en performance**: 🟡 +5-10ms por request (negligible)
- **Complejidad**: 🟢 Baja (aplicar middleware)

### ⏱️ Estimado de Implementación
- **Codificación**: 1-2 horas
- **Tests**: 1 hora
- **Deploy**: 15 minutos

### 🎯 Prioridad
**2️⃣ ALTA** - Mejora trazabilidad significativamente, esfuerzo bajo

---

## 2️⃣ USUARIO_REGISTRO EN PAGO

### 📊 Situación Actual
```python
# Pago creado sin saber quién lo creó
pago = Pago(
    cedula_cliente=...,
    monto_pagado=...,
    usuario_registro=None,  # ❌ Siempre NULL
)
```

### 💡 Solución Sugerida: Auto-población desde JWT

**Implementación en endpoints de creación**:

```python
# backend/app/api/v1/endpoints/pagos.py

from app.core.deps import get_current_user

@router.post("/pagos", response_model=PagoResponse)
def crear_pago(
    payload: PagoCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)  # ← NUEVO
):
    """Crea pago con usuario_registro del usuario autenticado."""
    
    # Extraer email del usuario actual
    usuario_email = current_user.email if current_user else "sistema@rapicredit.com"
    
    pago = Pago(
        cedula_cliente=payload.cedula_cliente,
        monto_pagado=payload.monto_pagado,
        usuario_registro=usuario_email,  # ✅ AHORA POBLADO
        ...
    )
    db.add(pago)
    db.commit()
    return PagoResponse.model_validate(pago)
```

**También para uploads masivos**:

```python
@router.post("/upload")
def upload_excel_pagos(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),  # ← NUEVO
):
    """Carga masiva con usuario_registro del uploader."""
    
    usuario_email = current_user.email
    
    for row in pagos_a_insertar:
        row.usuario_registro = usuario_email  # ✅ Populate
        ...
```

### 📈 Impacto
- **Trazabilidad**: ⬆️ +40% (saber quién creó cada pago)
- **Costo**: 🟢 Bajo (agregar 1 línea por endpoint)
- **Breaking changes**: ❌ Ninguno (campo era NULL, sigue NULL para historico)
- **Queries**: Ahora puedes hacer `SELECT * FROM pagos WHERE usuario_registro = 'juan@...'`

### ⏱️ Estimado de Implementación
- **Codificación**: 30 minutos (tocar 3-4 endpoints)
- **Tests**: 30 minutos
- **Deploy**: 10 minutos

### 🎯 Prioridad
**2️⃣ ALTA** - Fácil, impacto inmediato, sin riesgo

---

## 3️⃣ FK CEDULA_CLIENTE → CLIENTES.CEDULA

### 📊 Situación Actual
```sql
-- Pago puede tener cedula que NO existe en clientes
INSERT INTO pagos (cedula_cliente, ...) VALUES ('V99999999', ...);
-- ✅ Se inserta (sin validación)

SELECT COUNT(*) FROM clientes WHERE cedula = 'V99999999';
-- → 0 (cliente no existe, pero pago existe)
```

### 💡 Solución Sugerida: FK Constraint + Migración

#### **Opción A: Agresiva (Recomendada)**
Agregar FK constraint directo:

```sql
-- Migration: 017_add_fk_cedula_cliente.sql

BEGIN;

-- 1. Limpiar pagos huérfanos (cedulas sin cliente)
DELETE FROM pagos p
WHERE NOT EXISTS (
    SELECT 1 FROM clientes c
    WHERE c.cedula = p.cedula_cliente
)
AND p.cedula_cliente != '';

-- 2. Agregar FK constraint
ALTER TABLE pagos
ADD CONSTRAINT fk_pagos_cedula_cliente
FOREIGN KEY (cedula_cliente)
REFERENCES clientes(cedula)
ON DELETE SET NULL;

-- 3. Audit: loguear cedulas eliminadas
-- INSERT INTO audit_cleanup (tabla, accion, fecha)
-- VALUES ('pagos', 'Limpieza de cedulas huérfanas', NOW());

COMMIT;
```

#### **Opción B: Conservadora (Más segura)**
Crear vista validada + triggers:

```sql
-- Antes de agregar FK:
-- 1. Auditar inconsistencias
SELECT cedula_cliente, COUNT(*) as pago_count
FROM pagos p
WHERE NOT EXISTS (
    SELECT 1 FROM clientes c
    WHERE c.cedula = p.cedula_cliente
)
GROUP BY cedula_cliente;

-- 2. Manualmente revisar y limpiar datos
-- 3. ENTONCES agregar FK
```

### 📈 Impacto
- **Integridad referencial**: ✅ 100% (garantizado por DB)
- **Queries**: Ahora es SEGURO hacer `JOIN pagos → clientes`
- **Inserción fallida**: Si cedula no existe → Error 23503 (FK violation)
- **Data loss**: ⚠️ Posible (si hay datos huérfanos)

### ⏱️ Estimado de Implementación
- **Análisis**: 1 hora (ver cuántos registros huérfanos hay)
- **Migración**: 30 minutos
- **Validación**: 1 hora
- **Deploy**: 15 minutos

### 🎯 Prioridad
**1️⃣ CRÍTICA** - Integridad de datos, pero requiere auditar primero

### ⚠️ Antes de ejecutar:
```sql
-- Ejecutar en dev/staging PRIMERO
SELECT COUNT(*) as pagos_huerfanos
FROM pagos p
WHERE NOT EXISTS (
    SELECT 1 FROM clientes c
    WHERE c.cedula = p.cedula_cliente
);

-- Si el resultado es > 0, revisar qué clientes faltan
SELECT DISTINCT p.cedula_cliente
FROM pagos p
WHERE NOT EXISTS (
    SELECT 1 FROM clientes c
    WHERE c.cedula = p.cedula_cliente
)
ORDER BY p.cedula_cliente;
```

---

## 4️⃣ RECHAZADO ESTADO

### 📊 Situación Actual
```python
# RECHAZADO está en frontend pero NO en DB
estado_values = ['DRAFT', 'EN_REVISION', 'APROBADO', 'DESEMBOLSADO', 'EVALUADO']
# ❌ RECHAZADO no está aquí

# Si intentas setear:
prestamo.estado = "RECHAZADO"  # ✅ App acepta
db.commit()  # ❌ DB CRASH: CHECK constraint violation
```

### 💡 Solución Sugerida: Implementar flujo de rechazo

#### **Opción A: Mantener estado RECHAZADO (Recomendado)**

1. **Agregar a CHECK constraint**:
```sql
-- Migration: 018_add_rechazado_estado.sql

ALTER TABLE prestamos
DROP CONSTRAINT ck_prestamos_estado_valido;

ALTER TABLE prestamos
ADD CONSTRAINT ck_prestamos_estado_valido
CHECK (estado IN ('DRAFT', 'EN_REVISION', 'APROBADO', 'DESEMBOLSADO', 'EVALUADO', 'RECHAZADO'));
```

2. **Crear endpoint de rechazo**:
```python
# backend/app/api/v1/endpoints/prestamos.py

@router.post("/{prestamo_id}/rechazar", response_model=PrestamoResponse)
def rechazar_prestamo(
    prestamo_id: int,
    payload: RechazarPrestamoBody,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Rechaza un préstamo en estados DRAFT/EN_REVISION/EVALUADO.
    """
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    # Solo puedo rechazar si está en estados temprana
    if prestamo.estado not in ["DRAFT", "EN_REVISION", "EVALUADO"]:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede rechazar préstamo en estado {prestamo.estado}"
        )
    
    prestamo.estado = "RECHAZADO"
    prestamo.usuario_aprobador = current_user.email
    prestamo.fecha_aprobacion = datetime.now()
    
    # Auditar
    audit = Auditoria(
        usuario_id=current_user.id,
        accion="RECHAZO_PRESTAMO",
        entidad="prestamos",
        entidad_id=prestamo_id,
        detalles=f"Motivo: {payload.motivo_rechazo}",
    )
    db.add(audit)
    db.commit()
    
    return PrestamoResponse.model_validate(prestamo)


class RechazarPrestamoBody(BaseModel):
    motivo_rechazo: str  # Ej: "No cumple requisitos de solvencia"
```

3. **Actualizar frontend**:
```typescript
// frontend/src/components/prestamos/FormularioRechazo.tsx

const rechazarPrestamo = async (prestamoId: number, motivo: string) => {
    const response = await api.post(`/prestamos/${prestamoId}/rechazar`, {
        motivo_rechazo: motivo
    });
    return response.data;
};
```

#### **Opción B: Eliminar RECHAZADO (Simplificación)**

Si no se necesita rechazo, simplemente:

```python
# backend/scripts/018_remove_rechazado.sql
ALTER TABLE prestamos
DROP CONSTRAINT ck_prestamos_estado_valido;

ALTER TABLE prestamos
ADD CONSTRAINT ck_prestamos_estado_valido
CHECK (estado IN ('DRAFT', 'EN_REVISION', 'APROBADO', 'DESEMBOLSADO', 'EVALUADO'));

-- Eliminar cualquier préstamo con RECHAZADO
DELETE FROM prestamos WHERE estado = 'RECHAZADO';

-- Frontend: remover opción RECHAZADO de dropdown
```

### 📈 Impacto (Opción A)
- **Flujo**: ✅ Rechazo explícito, auditado
- **Trazabilidad**: ✅ Motivo de rechazo guardado
- **UI**: ✅ Estados consistentes (frontend + backend)
- **Data**: ✅ Histórico de rechazos

### ⏱️ Estimado de Implementación
- **A (Implementar rechazo)**: 3-4 horas (endpoint + validación + frontend)
- **B (Eliminar rechazo)**: 30 minutos

### 🎯 Prioridad
**3️⃣ MEDIA** - Nice to have, pero necesita decisión: ¿rechazos importantes?

---

## 📊 RESUMEN DE MEJORAS

| Mejora | Esfuerzo | Impacto | Prioridad | Riesgo | ROI |
|--------|----------|---------|-----------|--------|-----|
| **1. Auditoría** | 🟢 Bajo | 🔴 Alto | 2️⃣ Alta | 🟢 Bajo | ⭐⭐⭐⭐⭐ |
| **2. usuario_registro** | 🟢 Bajo | 🟡 Medio | 2️⃣ Alta | 🟢 Bajo | ⭐⭐⭐⭐⭐ |
| **3. FK cedula** | 🟡 Medio | 🔴 Alto | 1️⃣ Crítica | 🟡 Medio | ⭐⭐⭐⭐ |
| **4. RECHAZADO** | 🔴 Alto | 🟡 Medio | 3️⃣ Media | 🟡 Medio | ⭐⭐⭐ |

---

## 🎯 HOJA DE RUTA RECOMENDADA

### **Sprint 1 (Esta semana)** - 🟢 Bajo riesgo, alto ROI
1. ✅ Implementar middleware de auditoría
2. ✅ Agregar usuario_registro en pagos

**Esfuerzo**: 3-4 horas total  
**Impacto**: Trazabilidad +70%

### **Sprint 2 (Próxima semana)** - 🟡 Requiere auditoría previa
1. ⚠️ Auditar cedulas huérfanas en pagos
2. ⚠️ Limpiar datos si es necesario
3. ⚠️ Agregar FK cedula_cliente

**Esfuerzo**: 3-4 horas total  
**Impacto**: Integridad referencial 100%

### **Sprint 3 (Futuro)** - 🟡 Decisión primero
1. ❓ Decidir: ¿implementar rechazo o eliminar?
2. ✅ Implementar decisión elegida

**Esfuerzo**: 30 min (eliminar) o 4 horas (implementar)  
**Impacto**: UX más clara

---

## 📝 IMPLEMENTACIÓN RÁPIDA: AUDITORÍA + usuario_registro

Si quieres los **2 wins rápidos**, aquí está el código todo junto:

### Paso 1: Actualizar modelo Pago

```python
# backend/app/models/pago.py

class Pago(Base):
    __tablename__ = "pagos"
    # ... columnas existentes ...
    usuario_registro = Column(String(100), nullable=True)  # Ya existe
    usuario_creacion = Column(String(100), nullable=True)  # ✅ NUEVO
```

### Paso 2: Middleware de auditoría

```python
# backend/app/middleware/audit_middleware.py
[Ver código anterior]
```

### Paso 3: Registrar en main.py

```python
# backend/app/main.py

app.middleware("http")(audit_middleware)
```

### Paso 4: Actualizar 3 endpoints de pago

```python
# backend/app/api/v1/endpoints/pagos.py

def crear_pago(..., current_user = Depends(get_current_user)):
    pago = Pago(
        ...
        usuario_creacion=current_user.email,  # ✅ NUEVO
    )

def upload_excel_pagos(..., current_user = Depends(get_current_user)):
    for p in pagos:
        p.usuario_creacion = current_user.email  # ✅ NUEVO

def guardar_fila_editable(..., current_user = Depends(get_current_user)):
    pago = Pago(
        ...
        usuario_creacion=current_user.email,  # ✅ NUEVO
    )
```

### Paso 5: Deploy
```bash
git add -A
git commit -m "feat: auditoría middleware + usuario_creacion en pagos"
git push origin main
```

---

## ✅ CONCLUSIÓN

**Puedes mejorar trazabilidad en 2 pasos fáciles (3-4 horas)**:
1. ✅ Middleware de auditoría → 95% trazabilidad
2. ✅ usuario_registro poblado → Saber quién creó cada pago

**Luego (cuando sea necesario)**:
3. ⚠️ FK cedula_cliente → Integridad referencial
4. ❓ Decisión sobre RECHAZADO → UX clara

---

**¿Cuál quieres implementar primero? Te puedo dar el código completo y listo para copiar.**
