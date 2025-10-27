# 📋 TEMPLATE ANALISTAS - Perfil Completo

## 🗂️ **ESTRUCTURA DE BASE DE DATOS**

### Tabla: `analistas`

| Campo | Tipo | Nullable | Default | Descripción |
|-------|------|----------|---------|-------------|
| `id` | INTEGER | NO | AUTO_INCREMENT | Identificador único (PK) |
| `nombre` | VARCHAR(255) | NO | - | Nombre completo del analista |
| `activo` | BOOLEAN | NO | `true` | Estado del analista (True/False o 1/0) |
| `created_at` | TIMESTAMP WITH TIME ZONE | YES | `datetime.utcnow()` | Fecha de creación |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NO | `datetime.utcnow()` (auto-update) | Fecha de última actualización |

---

## 📝 **FORMULARIO DE CREACIÓN/EDICIÓN**

### **Campo: Nombre** (Obligatorio)

**Validaciones:**
- ✅ Mínimo: **2 palabras**
- ✅ Máximo: **4 palabras**
- ✅ Cada palabra: mínimo 2 caracteres
- ✅ Capitalización: Primera letra de cada palabra en mayúscula automática

**Ejemplos válidos:**
- `"Juan Pérez"` ✅
- `"Juan Carlos Pérez"` ✅
- `"Juan Carlos Pérez García"` ✅

**Ejemplos inválidos:**
- `"Juan"` ❌ (solo 1 palabra)
- `"Juan Carlos Pérez García Rodriguez"` ❌ (5 palabras, máximo 4)
- `"A B"` ❌ (muy corto)

---

### **Campo: Estado** (Obligatorio en edición)

**Valores:**
- `1` o `true` = **Activo** (aparece en listas)
- `2` o `false` = **Inactivo** (no aparece en listas)

**Comportamiento:**
- Al crear: Siempre se crea como **Activo** (no se puede cambiar en creación)
- Al editar: Se puede cambiar a **Inactivo** manualmente
- Se guarda en BD como: `Boolean` (True/False) o `Integer` (1/0)

**Ejemplo en BD:**
```sql
INSERT INTO analistas (nombre, activo) VALUES ('Juan Pérez', true);
-- o
INSERT INTO analistas (nombre, activo) VALUES ('Juan Pérez', 1);
```

---

## 📅 **FECHAS AUTOMÁTICAS**

### **created_at** (Fecha de Creación)

**Cuándo se asigna:**
- ✅ Automáticamente cuando se crea un nuevo analista
- ✅ Fecha: `datetime.utcnow()`
- ✅ Formato BD: `2025-10-26 15:30:45.123456+00`
- ✅ Formato Frontend: `DD/MM/YYYY` (ej: `26/10/2025`)

**Ejemplo:**
```python
# Se asigna automáticamente al crear
analista = Analista(nombre="Juan Pérez", activo=True)
db.add(analista)
db.commit()  # ← Se asigna created_at aquí
```

---

### **updated_at** (Fecha de Actualización)

**Cuándo se asigna:**
- ✅ Automáticamente cada vez que se edita el analista
- ✅ Se actualiza manualmente en el endpoint de actualización
- ✅ Fecha: `datetime.utcnow()`
- ✅ Formato BD: `2025-10-26 15:30:45.123456+00`
- ✅ Formato Frontend: `DD/MM/YYYY` (ej: `26/10/2025`)

**Ejemplo:**
```python
# Al editar
analista.nombre = "Juan Carlos Pérez"
analista.updated_at = datetime.utcnow()  # ← Se actualiza manualmente
db.commit()
```

---

## 🎯 **ENDPOINTS API**

### **GET /api/v1/analistas**
**Función:** Listar TODOS los analistas (activos + inactivos)
**Orden:** Por ID ascendente
**Límite:** 1000 registros

**Ejemplo respuesta:**
```json
{
  "items": [
    {
      "id": 1,
      "nombre": "Juan Pérez",
      "activo": true,
      "created_at": "2025-10-01T00:00:00+00:00",
      "updated_at": "2025-10-26T15:30:45+00:00"
    }
  ],
  "total": 17,
  "page": 1,
  "size": 1000,
  "pages": 1
}
```

---

### **GET /api/v1/analistas/{id}**
**Función:** Obtener un analista específico por ID

---

### **POST /api/v1/analistas**
**Función:** Crear nuevo analista

**Body:**
```json
{
  "nombre": "Juan Pérez",
  "activo": true
}
```

**Automatico:**
- `created_at` ← Se asigna automáticamente
- `updated_at` ← Se asigna automáticamente
- `activo` ← Siempre `true` por defecto

---

### **PUT /api/v1/analistas/{id}**
**Función:** Actualizar analista existente

**Body:**
```json
{
  "nombre": "Juan Carlos Pérez",
  "activo": false
}
```

**Automatico:**
- `updated_at` ← Se actualiza manualmente con `datetime.utcnow()`

---

### **DELETE /api/v1/analistas/{id}**
**Función:** Eliminar analista permanentemente de la BD

---

## 🏗️ **ESTRUCTURA COMPLETA**

### **Backend (Python)**

**Modelo SQLAlchemy:** `backend/app/models/analista.py`
```python
class Analista(Base):
    __tablename__ = "analistas"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False, index=True)
    activo = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Schemas Pydantic:** `backend/app/schemas/analista.py`
```python
# Para crear
class AnalistaCreate(BaseModel):
    nombre: str
    activo: bool = True

# Para actualizar
class AnalistaUpdate(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None

# Para respuesta
class AnalistaResponse(BaseModel):
    id: int
    nombre: str
    activo: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

---

### **Frontend (TypeScript)**

**Interface:** `frontend/src/services/analistaService.ts`
```typescript
export interface Analista {
  id: number
  nombre: string
  activo: boolean
  created_at: string
  updated_at?: string
}

export interface AnalistaCreate {
  nombre: string
  activo?: boolean
}
```

---

## 💾 **EJEMPLO DE DATOS EN BD**

```sql
-- Tabla analistas
CREATE TABLE analistas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    activo BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ejemplo de registro
INSERT INTO analistas (nombre, activo, created_at) 
VALUES ('Juan Pérez', true, '2025-10-01 00:00:00+00');

-- Resultado
SELECT * FROM analistas;

id  | nombre           | activo | created_at                    | updated_at
----|------------------|--------|-------------------------------|-------------------------------
1   | Juan Pérez       | true   | 2025-10-01 00:00:00+00       | 2025-10-01 00:00:00+00
```

---

## 📊 **KPIs (Indicadores)**

### **Total Analistas**
```typescript
analistas.length
// Muestra: TODOS (activos + inactivos)
```

### **Activos**
```typescript
analistas.filter(a => a.activo === true || a.activo === 1).length
// Muestra: Solo con activo = true o activo = 1
```

### **Inactivos**
```typescript
analistas.filter(a => a.activo === false || a.activo === 2 || a.activo === 0).length
// Muestra: Solo con activo = false, activo = 2 o activo = 0
```

### **Mostrados**
```typescript
filteredAnalistas.length
// Muestra: Resultado de búsqueda
```

---

## ✅ **VALIDACIONES COMPLETAS**

| Validación | Regla |
|------------|-------|
| Nombre vacío | ❌ No permitido |
| Nombre < 2 palabras | ❌ Error: "Debe ingresar al menos 2 palabras" |
| Nombre > 4 palabras | ❌ Error: "Debe ingresar máximo 4 palabras" |
| Cada palabra < 2 caracteres | ❌ Error: "Cada palabra debe tener al menos 2 caracteres" |
| Capitalización | ✅ Automática (primera letra mayúscula por palabra) |

---

## 🔄 **FLUJO DE DATOS**

```
1. Usuario ingresa: "juan pérez"
   ↓
2. Frontend valida: ✅ 2 palabras
   ↓
3. Frontend formatea: "Juan Pérez"
   ↓
4. Backend recibe: "Juan Pérez"
   ↓
5. Base de Datos guarda:
   - nombre: "Juan Pérez"
   - activo: true
   - created_at: 2025-10-26 15:30:45+00
   - updated_at: 2025-10-26 15:30:45+00
   ↓
6. Frontend muestra:
   - En tabla: "Juan Pérez"
   - En badge: "Activo"
   - En KPI: Activos +1
```

---

## 🎯 **RESUMEN FINAL**

### **Campos que se guardan:**
1. `id` - Auto (PK)
2. `nombre` - Usuario (2-4 palabras)
3. `activo` - Sistema (true por defecto al crear, editable al editar)
4. `created_at` - Sistema (automático al crear)
5. `updated_at` - Sistema (automático al editar)

### **Formato de fecha mostrado:**
- Frontend: `DD/MM/YYYY` (ej: `26/10/2025`)
- Base de datos: `YYYY-MM-DD HH:mm:ss+00` (ej: `2025-10-26 15:30:45+00`)

### **Validación de nombre:**
- Mínimo: 2 palabras
- Máximo: 4 palabras
- Capitalización automática

---

✅ **TEMPLATE COMPLETO Y FUNCIONAL**

