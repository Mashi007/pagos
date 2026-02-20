# INDICADORES VISUALES DE REVISIÓN MANUAL EN LISTA DE PRÉSTAMOS

## 📍 Ubicación
**Página**: `/pagos/prestamos` (Lista de Préstamos)  
**Columna**: Acciones (derecha)

---

## 🎯 INDICADORES Y ACCIONES

### **1. ⚠️ TRIÁNGULO NARANJA** - Estado: `pendiente`
- **Significado**: Préstamo no ha sido revisado aún
- **Color**: Naranja (#FF9500)
- **Icono**: `AlertTriangle`
- **Acción**: Click → Navega a `/revision-manual`
- **Tooltip**: "No revisado - Click para revisar"

### **2. ❓ PREGUNTA AMARILLA** - Estado: `revisando`
- **Significado**: Préstamo está en proceso de revisión
- **Color**: Amarillo (#EAB308)
- **Icono**: `HelpCircle`
- **Acción**: Click → Navega a `/revision-manual/editar/{prestamoId}`
- **Tooltip**: "En revisión - Click para continuar"

### **3. ✅ CHECKMARK VERDE** - Estado: `revisado`
- **Significado**: Préstamo ha sido completamente revisado y confirmado
- **Color**: Verde (#22C55E)
- **Icono**: `CheckCircle2`
- **Acción**: No clickeable (solo indicador)
- **Tooltip**: "Revisión completada"

### **4. Vacío (sin icono)** - Estado: `null` (no existe registro)
- **Significado**: Préstamo no está en revisión manual
- **Acción**: Ninguna
- **Nota**: No aparece ningún indicador

---

## 🔄 FLUJO DE USUARIO

```
Lista de Préstamos (/pagos/prestamos)
│
├─ Préstamo NO revisado (⚠️)
│  └─ Click en triángulo
│     └─ Navega a /revision-manual
│        └─ Usuario ve lista de revisión con botones ¿Sí? ¿No?
│
├─ Préstamo EN REVISIÓN (❓)
│  └─ Click en pregunta
│     └─ Navega a /revision-manual/editar/{prestamoId}
│        └─ Usuario continúa editando
│
└─ Préstamo REVISADO (✅)
   └─ Sin acción
   └─ Indica que está completado
```

---

## 💾 DATOS ENVIADOS

### Backend (FastAPI)
**Endpoint**: `GET /prestamos` (listar)

**Cambios en Response**:
```python
# Schema actualizado (app/schemas/prestamo.py)
class PrestamoListResponse(PrestamoResponse):
    revision_manual_estado: Optional[str] = None
    # Valores posibles: "pendiente" | "revisando" | "revisado" | None
```

**SQL Query** (en endpoint):
```python
# JOIN con tabla revision_manual_prestamos
revision_manual_estados = {}
if prestamo_ids:
    rev_q = select(
        RevisionManualPrestamo.prestamo_id, 
        RevisionManualPrestamo.estado_revision
    ).where(RevisionManualPrestamo.prestamo_id.in_(prestamo_ids))
    
    for pid, estado in db.execute(rev_q).all():
        revision_manual_estados[pid] = estado
```

### Frontend (React)
**Componente**: `PrestamosList.tsx`

**Renderizado**:
```typescript
{prestamo.revision_manual_estado === 'pendiente' && (
  <Button onClick={() => navigate(`/revision-manual`)}>
    <AlertTriangle /> {/* ⚠️ */}
  </Button>
)}

{prestamo.revision_manual_estado === 'revisando' && (
  <Button onClick={() => navigate(`/revision-manual/editar/${prestamo.id}`)}>
    <HelpCircle /> {/* ❓ */}
  </Button>
)}

{prestamo.revision_manual_estado === 'revisado' && (
  <CheckCircle2 /> {/* ✅ */}
)}
```

---

## 📊 EJEMPLOS VISUALES

### Tabla de Préstamos:

| Cliente | Cédula | Monto | Modalidad | Cuotas | Estado | Fecha | Acciones |
|---------|--------|-------|-----------|--------|--------|-------|----------|
| Lucas | V123 | $850.21 | Mensual | 12 | Aprobado | 31/10 | **⚠️** 👁️ ✎ 🗑️ |
| María | V456 | $500 | Mensual | 6 | Desembolsado | 25/10 | **❓** 👁️ ✎ 🗑️ |
| Juan | V789 | $1000 | Quincenal | 24 | Aprobado | 20/10 | **✅** 👁️ ✎ 🗑️ |

---

## 🔐 Conexión a BD

### Tabla: `revision_manual_prestamos`
```sql
SELECT prestamo_id, estado_revision 
FROM revision_manual_prestamos 
WHERE prestamo_id IN (...)
```

**Campos relevantes**:
- `prestamo_id` → FK a tabla prestamos
- `estado_revision` → 'pendiente' | 'revisando' | 'revisado'

### Performance
- ✅ Query optimizada con `WHERE IN (...)`
- ✅ Índice en `revision_manual_prestamos.prestamo_id`
- ✅ Sin N+1 queries (bulk fetch)

---

## 🎨 ESTILOS Y COLORES

| Estado | Color | Hex | Icono | Clase CSS |
|--------|-------|-----|-------|-----------|
| Pendiente | Naranja | #FF9500 | AlertTriangle | `text-orange-600 hover:bg-orange-50` |
| Revisando | Amarillo | #EAB308 | HelpCircle | `text-yellow-600 hover:bg-yellow-50` |
| Revisado | Verde | #22C55E | CheckCircle2 | `text-green-600` |

---

## 🔗 NAVEGACIÓN

| Icono | Destino | Parámetros | Acción |
|-------|---------|-----------|--------|
| ⚠️ | `/revision-manual` | - | Abre lista de revisión |
| ❓ | `/revision-manual/editar/{prestamoId}` | prestamoId | Abre editor específico |
| ✅ | - | - | Solo indicador (no nav) |

---

## 📋 CHECKLIST

- ✅ Backend devuelve `revision_manual_estado` en listado
- ✅ Frontend renderiza iconos según estado
- ✅ Iconos son clickeables y navegan correctamente
- ✅ Tooltips informativos en cada icono
- ✅ Colores diferenciados por estado
- ✅ Sin datos stubs (conexión real a BD)
- ✅ Performance optimizada (JOIN único)
- ✅ Responsive (funciona en mobile)

---

## 🚀 Resumen

**Sistema de indicadores visuales implementado:**
- ✅ Muestra estado de revisión directamente en lista
- ✅ Permite navegar a revisión desde la lista
- ✅ Iconos intuitivos y diferenciados
- ✅ Conectado a base de datos real
- ✅ Sin degradación de performance

Documento: INDICADORES_VISUALES_REVISION_MANUAL.md  
Fecha: 2026-02-20
