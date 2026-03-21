# Guía Rápida de Refactorización

## 🎯 Checklist Rápido

### Estado Actual del Proyecto
```
Total de archivos > 1000 líneas: 10
Críticos (>2000 líneas):
  ✗ pagos.py (2337)
  ✗ prestamos.py (2002)

Altos (1300-2000 líneas):
  ✗ Comunicaciones.tsx (1437)
  ✗ notificaciones.py (1396)
  ✗ PlantillasNotificaciones.tsx (1380)
  ✗ PagosList.tsx (1223)
  ✗ useExcelUploadPagos.ts (1234)

Medios (1000-1300 líneas):
  ✗ DashboardMenu.tsx (1111)
  ✗ whatsapp_service.py (1062)
  ✗ cobros.py (1020)
```

---

## 📋 Prioridades por Fase

### 🔴 FASE 1 - CRÍTICO (Semana 1-2)
**Impacto:** Alto | **Complejidad:** Alta | **Duración:** 5-10 días

#### 1.1 `pagos.py` → Refactorizar a servicios
```bash
# Crear estructura
mkdir -p backend/app/services/pagos

# Archivos a crear:
backend/app/services/pagos/__init__.py
backend/app/services/pagos/pagos_service.py       (300-400 líneas)
backend/app/services/pagos/pagos_validacion.py    (200-300 líneas)
backend/app/services/pagos/pagos_calculo.py       (150-200 líneas)
backend/app/services/pagos/pagos_reportes.py      (200-300 líneas)
backend/app/services/pagos/pagos_excepciones.py   (50-100 líneas)

# Refactorizar endpoint
backend/app/api/v1/endpoints/pagos.py (reduce de 2337 a 300-400 líneas)

# Crear tests
tests/unit/services/pagos/test_pagos_service.py
tests/unit/services/pagos/test_pagos_validacion.py
tests/unit/services/pagos/test_pagos_calculo.py
```

**Tiempo estimado:** 4-5 días

---

#### 1.2 `prestamos.py` → Dividir en servicios + endpoints
```bash
# Crear servicios
mkdir -p backend/app/services/prestamos

backend/app/services/prestamos/__init__.py
backend/app/services/prestamos/prestamos_service.py
backend/app/services/prestamos/amortizacion_service.py
backend/app/services/prestamos/prestamos_validacion.py
backend/app/services/prestamos/prestamos_calculo.py

# Dividir endpoints
backend/app/api/v1/endpoints/prestamos_base.py        (CRUD)
backend/app/api/v1/endpoints/prestamos_amortizacion.py (Amortización)
backend/app/api/v1/endpoints/prestamos_reportes.py    (Reportes)

# Tests
tests/unit/services/prestamos/...
```

**Tiempo estimado:** 4-5 días

---

#### 1.3 `useExcelUploadPagos.ts` → Dividir en servicios + hooks
```bash
# Crear servicios
mkdir -p frontend/src/services/excel

frontend/src/services/excel/excelParsingService.ts
frontend/src/services/excel/excelValidationService.ts
frontend/src/services/excel/excelProcessingService.ts
frontend/src/services/excel/excelMappingService.ts

# Crear hooks
frontend/src/hooks/useExcelUpload.ts
frontend/src/hooks/useExcelValidation.ts
frontend/src/hooks/useExcelProcessing.ts

# Tests
tests/unit/services/excel/...
tests/unit/hooks/useExcel...
```

**Tiempo estimado:** 3-4 días

**⚠️ NOTA IMPORTANTE:** Archivo de 3.8 MB es anormal. Investigar si contiene:
- Datos embebidos
- Archivos binarios
- Errores en estructura

---

### 🟠 FASE 2 - ALTO (Semana 3-4)
**Impacto:** Medio-Alto | **Complejidad:** Media | **Duración:** 5-8 días

#### 2.1 `Comunicaciones.tsx` → Dividir en componentes
```bash
frontend/src/components/comunicaciones/
├── Comunicaciones.tsx                    (Contenedor, < 300 líneas)
├── EmailSection.tsx                      (< 350 líneas)
├── SMSSection.tsx                        (< 350 líneas)
├── WhatsAppSection.tsx                   (< 350 líneas)
├── hooks/useComunicacionesState.ts       (< 200 líneas)
├── services/comunicacionesService.ts
└── tests/...

# Reducción: 1437 → 300 (contenedor) + 3×350 (secciones)
```

**Tiempo estimado:** 2-3 días

---

#### 2.2 `notificaciones.py` → Servicios por canal
```bash
backend/app/services/notificaciones/
├── __init__.py
├── notificaciones_base.py
├── email_service.py
├── sms_service.py
├── whatsapp_service.py (mejorado)
└── plantillas_service.py

backend/app/api/v1/endpoints/
├── notificaciones.py                     (< 400 líneas)
└── notificaciones_plantillas.py          (< 300 líneas)
```

**Tiempo estimado:** 3-4 días

---

#### 2.3 `PlantillasNotificaciones.tsx` → Separar plantillas
```bash
frontend/src/components/notificaciones/
├── PlantillasNotificaciones.tsx          (Contenedor)
├── TemplatesList.tsx                     (< 300 líneas)
├── TemplateEditor.tsx                    (< 400 líneas)
├── TemplatePreview.tsx                   (< 250 líneas)
├── hooks/useTemplateManagement.ts
└── services/...
```

**Tiempo estimado:** 2-3 días

---

#### 2.4 `PagosList.tsx` → Dividir en subcomponentes
```bash
frontend/src/components/pagos/
├── PagosList.tsx                         (Contenedor, < 300 líneas)
├── PagosTable.tsx                        (< 300 líneas)
├── PagosFilters.tsx                      (< 250 líneas)
├── PagosActions.tsx                      (< 200 líneas)
├── hooks/
│   ├── usePagosFiltering.ts
│   ├── usePagosExport.ts
│   └── usePagosTable.ts
└── services/...
```

**Tiempo estimado:** 2-3 días

---

#### 2.5 `whatsapp_service.py` → Dividir responsabilidades
```bash
backend/app/services/whatsapp/
├── __init__.py
├── whatsapp_base.py
├── whatsapp_mensajes.py
├── whatsapp_plantillas.py
├── whatsapp_media.py
├── whatsapp_webhooks.py
└── whatsapp_excepciones.py
```

**Tiempo estimado:** 2-3 días

---

### 🟡 FASE 3 - MEDIO (Semana 5)
**Impacto:** Bajo-Medio | **Complejidad:** Baja-Media | **Duración:** 2-3 días

#### 3.1 `DashboardMenu.tsx` → Refactorizar layout
```bash
frontend/src/pages/DashboardMenu/
├── DashboardMenu.tsx                     (Contenedor)
├── sections/
│   ├── KPISection.tsx
│   ├── ChartsSection.tsx
│   ├── TablesSection.tsx
│   └── ActionsSection.tsx
└── hooks/...
```

**Tiempo estimado:** 1-2 días

---

#### 3.2 `cobros.py` → Servicios adicionales
```bash
backend/app/services/cobros/
├── cobros_service.py
├── cobros_calculo.py
└── cobros_reportes.py

# Refactorizar endpoint
backend/app/api/v1/endpoints/cobros.py (< 400 líneas)
```

**Tiempo estimado:** 1-2 días

---

## 📊 Roadmap Visual

```
SEMANA 1-2 (CRÍTICO)
├─ Lunes-Miércoles:   pagos.py
├─ Jueves-Viernes:    prestamos.py (Parte 1)
└─ Lunes-Miércoles:   prestamos.py (Parte 2) + useExcelUploadPagos.ts

SEMANA 3-4 (ALTO)
├─ Lunes-Martes:      Comunicaciones.tsx
├─ Miércoles-Jueves:  notificaciones.py
├─ Viernes:           PlantillasNotificaciones.tsx (Parte 1)
└─ Lunes-Miércoles:   PlantillasNotificaciones.tsx (Parte 2)
                      + PagosList.tsx + whatsapp_service.py

SEMANA 5 (MEDIO)
├─ Lunes-Miércoles:   DashboardMenu.tsx
└─ Jueves-Viernes:    cobros.py + Testing final
```

---

## 🛠️ Herramientas y Comandos

### Python (Backend)
```bash
# Analizar complejidad
python -m py_compile backend/app/api/v1/endpoints/pagos.py

# Tests
pytest tests/unit/services/pagos/
pytest -v --cov=backend/app/services/pagos/

# Linting
flake8 backend/app/services/
black backend/app/services/
```

### TypeScript (Frontend)
```bash
# Analizar
npx eslint frontend/src/hooks/useExcelUploadPagos.ts

# Tests
npm test -- frontend/src/hooks/useExcelUpload.ts
npm test -- --coverage

# Build
npm run build

# Type checking
npx tsc --noEmit
```

---

## ✅ Criterios de Aceptación

Para cada refactorización considere:

### Backend (Python)
- [ ] Archivo principal < 400 líneas
- [ ] Máximo 3 responsabilidades por clase
- [ ] 80% de cobertura de tests
- [ ] Documentación en docstrings
- [ ] Sin cambios en API pública
- [ ] Performance igual o mejor
- [ ] Linting sin errores (flake8, black)

### Frontend (TypeScript)
- [ ] Componente principal < 300 líneas
- [ ] Componentes sección < 400 líneas
- [ ] Hooks < 200 líneas
- [ ] 70% de cobertura de tests
- [ ] TypeScript sin errores
- [ ] Sin cambios visuales
- [ ] Linting sin errores (eslint, prettier)

---

## 🔄 Proceso de Refactorización

### Para cada archivo/componente:

1. **Análisis** (1 día)
   - Entender la lógica actual
   - Identificar responsabilidades
   - Planificar divisiones

2. **Planificación** (0.5 días)
   - Crear estructura de directorios
   - Diseñar servicios/componentes
   - Documentar cambios

3. **Implementación** (2-3 días)
   - Crear servicios/componentes
   - Mover lógica
   - Actualizar referencias
   - Agregar tipos (TypeScript)

4. **Testing** (1-2 días)
   - Tests unitarios
   - Tests de integración
   - QA manual

5. **Revisión** (0.5 días)
   - Code review
   - Verificar criterios
   - Merge

**Total por archivo: 5-7 días en promedio**

---

## 📈 Métricas a Monitorear

```
ANTES:
- 10 archivos > 1000 líneas
- 2 archivos > 2000 líneas
- Complejidad ciclomática: ALTA
- Tests coverage: ~30%

DESPUÉS (Objetivo):
- 0 archivos > 1500 líneas
- 0 archivos > 2000 líneas
- Complejidad ciclomática: BAJA
- Tests coverage: >80%
```

---

## 🚨 Riesgos y Mitigación

| Riesgo | Mitigación |
|--------|-----------|
| Bugs en producción | Tests exhaustivos antes de deploy |
| Cambios rotos | Refactorizar por módulos pequeños |
| Performance degradada | Benchmarking antes/después |
| Falta de tiempo | Priorizar fase 1, parallelizar cuando sea posible |
| Documentación desactualizada | Documentar cambios en PRs |

---

## 📞 Contacto y Soporte

- Documentos de referencia:
  - `PLAN_REFACTORIZACION_ARCHIVOS_GRANDES.md`
  - `EJEMPLOS_REFACTORIZACION.md`
  - `ANALISIS_ARCHIVOS_GRANDES.txt`

- Preguntas frecuentes en: `docs/FAQ_REFACTORIZACION.md` (crear si es necesario)

---

**Última actualización:** Marzo 2026
**Versión:** 1.0
**Estado:** Listo para implementación
