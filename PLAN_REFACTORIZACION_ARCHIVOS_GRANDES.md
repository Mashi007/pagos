# Plan de Refactorización - Archivos Grandes

## 📊 Resumen Ejecutivo

Se han identificado **10 archivos críticos** en el proyecto que superan las **1000 líneas** de código, excediendo significativamente los límites recomendados de mantenibilidad.

| Archivo | Líneas | Tamaño | Prioridad | Acción |
|---------|--------|--------|-----------|--------|
| `backend/app/api/v1/endpoints/pagos.py` | 2337 | 112.8 KB | 🔴 CRÍTICO | Crear servicios especializados |
| `backend/app/api/v1/endpoints/prestamos.py` | 2002 | 95 KB | 🔴 CRÍTICO | Crear capa de servicios |
| `frontend/src/hooks/useExcelUploadPagos.ts` | 1234 | 3.8 MB | 🔴 CRÍTICO | Extraer servicios y hooks |
| `frontend/src/components/comunicaciones/Comunicaciones.tsx` | 1437 | 65.9 KB | 🟠 ALTO | Dividir en componentes |
| `backend/app/api/v1/endpoints/notificaciones.py` | 1396 | 65.6 KB | 🟠 ALTO | Servicios por canal |
| `frontend/src/components/notificaciones/PlantillasNotificaciones.tsx` | 1380 | 69 KB | 🟠 ALTO | Separar plantillas |
| `frontend/src/components/pagos/PagosList.tsx` | 1223 | 72.5 KB | 🟠 ALTO | Dividir en subcomponentes |
| `frontend/src/pages/DashboardMenu.tsx` | 1111 | 62.7 KB | 🟡 MEDIO | Refactorizar layout |
| `backend/app/services/whatsapp_service.py` | 1062 | 60.8 KB | 🟠 ALTO | Dividir responsabilidades |
| `backend/app/api/v1/endpoints/cobros.py` | 1020 | 75.7 KB | 🟡 MEDIO | Servicios adicionales |

---

## 🔴 CRÍTICO - Fase 1 (Impacto Máximo)

### 1. `backend/app/api/v1/endpoints/pagos.py` (2337 líneas)

**Problema:** Endpoint monolítico que concentra toda la lógica de gestión de pagos.

**Estructura Actual (Probable):**
```
- GET/POST/PUT/DELETE pagos
- Validaciones complejas
- Cálculos de intereses/multas
- Generación de reportes
- Filtros y búsquedas
- Lógica de aprobación
```

**Plan de Refactorización:**

#### Paso 1: Crear estructura de servicios
```
backend/app/services/pagos/
├── __init__.py
├── pagos_service.py          # Lógica principal (CRUD, estados)
├── pagos_validacion.py       # Validaciones específicas
├── pagos_calculo.py          # Cálculos (intereses, multas)
├── pagos_reportes.py         # Generación de reportes
└── pagos_excepciones.py      # Excepciones específicas
```

#### Paso 2: Refactorizar endpoints
```python
# router pagos.py - Reducido a 300-400 líneas
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.services.pagos import PagosService

router = APIRouter(prefix="/pagos", tags=["pagos"])

@router.get("/{pago_id}")
async def get_pago(pago_id: int, db: Session = Depends(get_db)):
    service = PagosService(db)
    return await service.obtener_pago(pago_id)

# ... endpoints principales delegando a servicios
```

#### Paso 3: Refactorización incremental
1. Crear `PagosService` con métodos básicos
2. Mover validaciones a `PagosValidacion`
3. Extraer cálculos a `PagosCalculo`
4. Separar reportes a `PagosReportes`
5. Actualizar endpoints para usar servicios
6. Escribir tests unitarios por servicio

**Beneficios:**
- ✅ Lógica testeable e independiente
- ✅ Reutilización de código
- ✅ Fácil mantenimiento
- ✅ Responsabilidades claras

---

### 2. `backend/app/api/v1/endpoints/prestamos.py` (2002 líneas)

**Problema:** Router de préstamos con lógica de amortización y cálculos integrados.

**Estructura Actual (Probable):**
```
- CRUD préstamos
- Generación de tablas de amortización
- Cálculos de cuotas
- Validaciones complejas
- Reportes
```

**Plan de Refactorización:**

#### Crear servicios de dominio
```
backend/app/services/prestamos/
├── __init__.py
├── prestamos_service.py       # Gestión básica
├── amortizacion_service.py    # Tabla de amortización
├── prestamos_calculo.py       # Cálculos financieros
├── prestamos_validacion.py    # Validaciones
└── prestamos_reportes.py      # Reportes
```

#### Dividir endpoints
```
backend/app/api/v1/endpoints/
├── prestamos_base.py          # CRUD básico (< 300 líneas)
├── prestamos_amortizacion.py  # Amortización (< 300 líneas)
└── prestamos_reportes.py      # Reportes (< 300 líneas)
```

#### Estructura recomendada
```python
# prestamos_base.py
from fastapi import APIRouter, Depends
from app.services.prestamos.prestamos_service import PrestamosService

router = APIRouter(prefix="/prestamos", tags=["prestamos"])

@router.post("/")
async def crear_prestamo(data: PrestamoCreadoSchema, db: Session = Depends(get_db)):
    service = PrestamosService(db)
    return await service.crear_prestamo(data)

# prestamos_amortizacion.py
router_amortizacion = APIRouter(prefix="/prestamos/amortizacion", tags=["amortizacion"])

@router_amortizacion.get("/{prestamo_id}/tabla")
async def obtener_tabla_amortizacion(prestamo_id: int, db: Session = Depends(get_db)):
    service = AmortizacionService(db)
    return await service.generar_tabla(prestamo_id)
```

---

### 3. `frontend/src/hooks/useExcelUploadPagos.ts` (1234 líneas, 3.8 MB)

**Problema:** Hook extremadamente grande (3.8 MB es anormal - probablemente contiene datos).

**Plan de Refactorización:**

#### Crear servicios de Excel
```
frontend/src/services/excel/
├── excelParsingService.ts      # Lectura y parseo
├── excelValidationService.ts   # Validaciones
├── excelProcessingService.ts   # Procesamiento de datos
└── excelMappingService.ts      # Mapeo de columnas
```

#### Crear hooks especializados
```
frontend/src/hooks/
├── useExcelUpload.ts           # Gestión de carga (< 200 líneas)
├── useExcelValidation.ts       # Validaciones (< 200 líneas)
├── useExcelProcessing.ts       # Procesamiento (< 200 líneas)
└── useExcelState.ts            # Estado compartido (< 150 líneas)
```

#### Estructura del hook refactorizado
```typescript
// useExcelUpload.ts - Hook principal (< 200 líneas)
import { useExcelValidation } from './useExcelValidation';
import { useExcelProcessing } from './useExcelProcessing';
import { ExcelParsingService } from '../services/excel/excelParsingService';

export const useExcelUpload = () => {
  const [state, setState] = useState<ExcelUploadState>({
    status: 'idle',
    progress: 0,
    errors: [],
  });

  const { validate } = useExcelValidation();
  const { process } = useExcelProcessing();

  const handleUpload = async (file: File) => {
    setState(prev => ({ ...prev, status: 'loading' }));
    
    try {
      const data = await ExcelParsingService.parse(file);
      const validation = await validate(data);
      
      if (!validation.isValid) {
        setState(prev => ({ 
          ...prev, 
          status: 'error',
          errors: validation.errors 
        }));
        return;
      }

      const processed = await process(data);
      setState(prev => ({ ...prev, status: 'success', data: processed }));
    } catch (error) {
      setState(prev => ({ ...prev, status: 'error', errors: [error.message] }));
    }
  };

  return { state, handleUpload };
};
```

---

## 🟠 ALTO - Fase 2 (Alta Importancia)

### 4. `frontend/src/components/comunicaciones/Comunicaciones.tsx` (1437 líneas)

**Plan de Refactorización:**

```
frontend/src/components/comunicaciones/
├── Comunicaciones.tsx          # Contenedor principal (< 300 líneas)
├── EmailSection.tsx            # Gestión de email (< 350 líneas)
├── SMSSection.tsx              # Gestión de SMS (< 350 líneas)
├── WhatsAppSection.tsx         # Gestión de WhatsApp (< 350 líneas)
├── hooks/
│   └── useComunicacionesState.ts  # Hook de estado
└── services/
    └── comunicacionesService.ts   # Lógica compartida
```

**Componente principal refactorizado:**
```typescript
// Comunicaciones.tsx (< 300 líneas)
import { EmailSection } from './EmailSection';
import { SMSSection } from './SMSSection';
import { WhatsAppSection } from './WhatsAppSection';
import { useComunicacionesState } from './hooks/useComunicacionesState';

export const Comunicaciones = () => {
  const { activeTab, setActiveTab, state } = useComunicacionesState();

  return (
    <div className="comunicaciones-container">
      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tab label="Email">
          <EmailSection state={state} />
        </Tab>
        <Tab label="SMS">
          <SMSSection state={state} />
        </Tab>
        <Tab label="WhatsApp">
          <WhatsAppSection state={state} />
        </Tab>
      </Tabs>
    </div>
  );
};
```

---

### 5. `backend/app/api/v1/endpoints/notificaciones.py` (1396 líneas)

**Plan de Refactorización:**

```
backend/app/services/notificaciones/
├── __init__.py
├── notificaciones_base.py      # Clase base
├── email_service.py            # Servicio de email
├── sms_service.py              # Servicio de SMS
├── whatsapp_service.py (mejorado)
└── plantillas_service.py       # Gestión de plantillas

backend/app/api/v1/endpoints/
├── notificaciones.py           # Endpoints API (< 400 líneas)
└── notificaciones_plantillas.py # CRUD plantillas (< 300 líneas)
```

---

### 6. `frontend/src/components/notificaciones/PlantillasNotificaciones.tsx` (1380 líneas)

**Plan de Refactorización:**

```
frontend/src/components/notificaciones/
├── PlantillasNotificaciones.tsx    # Contenedor (< 300 líneas)
├── TemplatesList.tsx               # Listado (< 300 líneas)
├── TemplateEditor.tsx              # Editor (< 400 líneas)
├── TemplatePreview.tsx             # Preview (< 250 líneas)
└── hooks/
    └── useTemplateManagement.ts    # Gestión de estado
```

---

### 7. `frontend/src/components/pagos/PagosList.tsx` (1223 líneas)

**Plan de Refactorización:**

```
frontend/src/components/pagos/
├── PagosList.tsx               # Contenedor (< 300 líneas)
├── PagosTable.tsx              # Tabla (< 300 líneas)
├── PagosFilters.tsx            # Filtros (< 250 líneas)
├── PagosActions.tsx            # Acciones (< 200 líneas)
└── hooks/
    ├── usePagosFiltering.ts    # Filtros
    ├── usePagosExport.ts       # Exportación
    └── usePagosTable.ts        # Tabla
```

---

### 8. `backend/app/services/whatsapp_service.py` (1062 líneas)

**Plan de Refactorización:**

```
backend/app/services/whatsapp/
├── __init__.py
├── whatsapp_base.py            # Clase base (< 250 líneas)
├── whatsapp_mensajes.py        # Envío de mensajes (< 350 líneas)
├── whatsapp_plantillas.py      # Gestión de plantillas (< 300 líneas)
├── whatsapp_media.py           # Manejo de media (< 250 líneas)
├── whatsapp_webhooks.py        # Webhooks (< 250 líneas)
└── whatsapp_excepciones.py     # Excepciones
```

---

## 🟡 MEDIO - Fase 3

### 9. `frontend/src/pages/DashboardMenu.tsx` (1111 líneas)

**Solución:** Refactorizar como contenedor de sub-componentes

```
frontend/src/pages/DashboardMenu/
├── DashboardMenu.tsx           # Contenedor (< 200 líneas)
├── sections/
│   ├── KPISection.tsx
│   ├── ChartsSection.tsx
│   ├── TablesSection.tsx
│   └── ActionsSection.tsx
└── hooks/
    └── useDashboardData.ts
```

---

### 10. `backend/app/api/v1/endpoints/cobros.py` (1020 líneas)

**Solución:** Crear servicios adicionales

```
backend/app/services/cobros/
├── cobros_service.py
├── cobros_calculo.py
└── cobros_reportes.py
```

---

## 📋 Checklist de Implementación

### Fase 1 - CRÍTICO (Semanas 1-2)

- [ ] **pagos.py**
  - [ ] Crear estructura de servicios
  - [ ] Extraer `PagosService`
  - [ ] Extraer `PagosValidacion`
  - [ ] Extraer `PagosCalculo`
  - [ ] Actualizar endpoints
  - [ ] Tests unitarios

- [ ] **prestamos.py**
  - [ ] Crear estructura de servicios
  - [ ] Extraer `AmortizacionService`
  - [ ] Dividir endpoints en 3 archivos
  - [ ] Tests unitarios

- [ ] **useExcelUploadPagos.ts**
  - [ ] Investigar y limpiar datos grandes
  - [ ] Crear servicios de Excel
  - [ ] Dividir en 3 hooks
  - [ ] Tests

### Fase 2 - ALTO (Semanas 3-4)

- [ ] **Comunicaciones.tsx**
  - [ ] Crear sub-componentes
  - [ ] Hook `useComunicacionesState`
  - [ ] Tests

- [ ] **notificaciones.py**
  - [ ] Servicios por canal
  - [ ] Dividir endpoints
  - [ ] Tests

- [ ] **PlantillasNotificaciones.tsx**
  - [ ] Separar componentes
  - [ ] Hook de gestión
  - [ ] Tests

- [ ] **PagosList.tsx**
  - [ ] Dividir en subcomponentes
  - [ ] Hooks especializados
  - [ ] Tests

- [ ] **whatsapp_service.py**
  - [ ] Dividir en módulos
  - [ ] Tests

### Fase 3 - MEDIO (Semana 5)

- [ ] **DashboardMenu.tsx**
  - [ ] Refactorizar layout
  - [ ] Crear sub-componentes

- [ ] **cobros.py**
  - [ ] Crear servicios
  - [ ] Tests

---

## 🧪 Estrategia de Testing

```python
# tests/unit/services/pagos/test_pagos_service.py
def test_crear_pago():
    service = PagosService(mock_db)
    resultado = service.crear_pago(pago_data)
    assert resultado.id > 0
    
def test_validar_pago_sin_cliente():
    service = PagosValidacion(mock_db)
    resultado = service.validar(pago_sin_cliente)
    assert not resultado.isValid
    assert "cliente_id" in resultado.errors
```

---

## 📈 Métricas de Éxito

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Archivos > 2000 líneas | 2 | 0 |
| Archivos > 1500 líneas | 3 | 0 |
| Archivos > 1000 líneas | 10 | 0 |
| Cobertura de tests | ~30% | >80% |
| Complejidad ciclomática promedio | Alto | Bajo |

---

## ⚠️ Riesgos y Mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|--------|-----------|
| Regresiones en producción | Media | Alto | Tests exhaustivos, QA manual |
| Cambios rotos en dependencias | Alta | Medio | Refactorizar por módulos, pruebas de integración |
| Falta de tiempo | Media | Medio | Priorizar fase 1, hacer en iteraciones |
| Documentación desactualizada | Alta | Bajo | Documentar cambios en el PR |

---

## 📚 Recursos y Referencias

- [Python PEP 20 - The Zen of Python](https://pep20.org/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Clean Code - Robert C. Martin](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)
- [React Patterns](https://reactpatterns.com/)

---

**Última actualización:** Marzo 2026
**Responsable:** Equipo de Desarrollo
**Estado:** En Planificación
