# 📋 Normas de Calidad Verificadas en CI/CD

Este documento detalla todas las herramientas y normas de calidad que se ejecutan automáticamente en cada commit del proyecto.

## 🚀 Workflow Principal: `ci-cd.yml`

Se ejecuta en cada commit a `main` y `develop`, y en cada Pull Request.

---

## 🔍 **JOB: Análisis de Calidad de Código (Backend)**

### 1. **Flake8** - Linting y Análisis Estático

**Herramienta:** `flake8`

**Configuración:** `.flake8`
- **Longitud máxima de líneas:** 120 caracteres
- **Errores críticos verificados:** `E9, F63, F7, F82` (sintaxis, funciones no definidas, etc.)
- **Análisis completo:**
  - Complejidad máxima: 10
  - Longitud de línea: 127
  - Modo no bloqueante (`--exit-zero`)

**Qué verifica:**
- ✅ Errores de sintaxis
- ✅ Funciones no definidas
- ✅ Imports no utilizados (excepto en `__init__.py` y tests)
- ✅ Complejidad ciclomática
- ✅ Longitud de líneas
- ✅ Estilo de código PEP 8

**Archivos excluidos:**
- `migrations/`
- `alembic/versions/`
- `__pycache__/`
- `*.pyc`
- `.git/`, `venv/`, `.venv/`, `node_modules/`
- `backend/tests/`

---

### 2. **Black** - Formateo de Código

**Herramienta:** `black`

**Configuración:** Default (perfil estándar)

**Qué verifica:**
- ✅ Formato consistente de código Python
- ✅ Espaciado y indentación
- ✅ Líneas largas (auto-wrap)
- ✅ Comillas consistentes
- ✅ Organización de expresiones

**Comportamiento:**
- **Verificación:** `black --check --diff` (no bloquea)
- **Aplicación automática:** Si hay cambios, Black los aplica automáticamente y crea un commit con `[skip ci]`

---

### 3. **Isort** - Ordenamiento de Imports

**Herramienta:** `isort`

**Configuración:** `.isort.cfg`
- **Perfil:** `black` (compatible con Black)
- **Longitud de línea:** 127 caracteres
- **Output multi-línea:** Tipo 3
- **Trailing comma:** Incluido
- **Parentheses:** Habilitado
- **Newline antes de comentarios:** Requerido

**Qué verifica:**
- ✅ Orden alfabético de imports
- ✅ Agrupación correcta: stdlib → third-party → local
- ✅ Separación entre grupos con líneas en blanco
- ✅ Formato compatible con Black

**Archivos excluidos:**
- `*/migrations/*`
- `*/alembic/*`

---

### 4. **Mypy** - Verificación de Tipos

**Herramienta:** `mypy`

**Configuración:** `--ignore-missing-imports`

**Qué verifica:**
- ✅ Tipado estático de Python
- ✅ Coincidencia de tipos en funciones
- ✅ Anotaciones de tipo correctas
- ✅ Tipos de retorno

**Modo:** No bloqueante (`|| true`)

---

## 🔍 **JOB: Pruebas Frontend**

### 5. **ESLint** - Linting TypeScript/JavaScript

**Herramienta:** `eslint`

**Script:** `npm run lint`

**Qué verifica:**
- ✅ Sintaxis correcta
- ✅ Reglas de estilo
- ✅ Buenas prácticas
- ✅ Warnings deshabilitados (max-warnings: 0)

**Archivos:** `.ts`, `.tsx`, `.js`, `.jsx`

---

### 6. **Prettier** - Formateo de Código Frontend

**Herramienta:** `prettier`

**Script:** `npm run format:check`

**Qué verifica:**
- ✅ Formato consistente de TypeScript/JavaScript
- ✅ Formato de JSON, CSS, Markdown
- ✅ Indentación y espaciado
- ✅ Longitud de líneas

**Archivos:** `src/**/*.{ts,tsx,js,jsx,json,css,md}`

---

### 7. **TypeScript Type Check** - Verificación de Tipos

**Herramienta:** `tsc` (TypeScript Compiler)

**Script:** `npm run type-check`

**Qué verifica:**
- ✅ Tipos correctos en TypeScript
- ✅ Compatibilidad de tipos
- ✅ Errores de compilación
- ✅ Tipos faltantes o incorrectos

**Modo:** `--noEmit` (solo verificación, sin generar archivos)

---

## 🔒 **Workflow: Security Scanning** (`security.yml`)

Se ejecuta en cada commit y PR, además de cada lunes a las 2 AM.

### 8. **Safety** - Vulnerabilidades de Dependencias Python

**Herramienta:** `safety check`

**Qué verifica:**
- ✅ Vulnerabilidades conocidas en dependencias Python
- ✅ Versiones inseguras de paquetes
- ✅ CVEs reportados

**Output:** JSON report

---

### 9. **Bandit** - Análisis de Seguridad Python

**Herramienta:** `bandit`

**Qué verifica:**
- ✅ Contraseñas hardcodeadas
- ✅ Uso inseguro de funciones
- ✅ Problemas de criptografía
- ✅ SQL injection potencial
- ✅ XSS vulnerabilities

**Nivel:** `-ll` (low, medium, high)

---

### 10. **Semgrep** - Análisis Estático de Seguridad

**Herramienta:** `semgrep`

**Configuración:** `--config=auto` (reglas automáticas)

**Qué verifica:**
- ✅ Patrones de código inseguros
- ✅ Vulnerabilidades comunes (OWASP Top 10)
- ✅ Anti-patrones de seguridad
- ✅ Problemas de autenticación/autorización

---

### 11. **NPM Audit** - Vulnerabilidades Frontend

**Herramienta:** `npm audit`

**Qué verifica:**
- ✅ Vulnerabilidades en dependencias npm
- ✅ Paquetes con CVEs
- ✅ Dependencias desactualizadas

---

### 12. **Snyk** - Análisis de Seguridad Frontend

**Herramienta:** `snyk`

**Configuración:** `--severity-threshold=high`

**Qué verifica:**
- ✅ Vulnerabilidades de alto impacto
- ✅ Dependencias con licencias restrictivas
- ✅ Problemas de seguridad en el código

**Requiere:** `SNYK_TOKEN` en secrets

---

### 13. **TruffleHog** - Detección de Secretos

**Herramienta:** `trufflesecurity/trufflehog`

**Qué verifica:**
- ✅ API keys expuestas
- ✅ Tokens de acceso
- ✅ Credenciales en el código
- ✅ Secretos en el historial de Git

**Modo:** `--only-verified` (solo secretos verificados)

---

### 14. **GitLeaks** - Detección de Secretos en Git

**Herramienta:** `gitleaks/gitleaks-action`

**Qué verifica:**
- ✅ Secretos en commits
- ✅ Credenciales en el historial
- ✅ Información sensible en repositorio

---

## 📊 **Workflow: Dependency Review** (`dependency-review.yml`)

Solo en Pull Requests.

### 15. **Dependency Review Action**

**Herramienta:** `actions/dependency-review-action`

**Configuración:**
- **Fail on severity:** `moderate`
- **Licencias permitidas:** MIT, Apache-2.0, BSD-3-Clause, ISC, Python-2.0
- **Licencias denegadas:** GPL-2.0, GPL-3.0, AGPL-3.0

**Qué verifica:**
- ✅ Nuevas vulnerabilidades en PRs
- ✅ Licencias de dependencias
- ✅ Cambios en dependencias

---

## 📊 **Workflow: Performance Testing** (`performance.yml`)

Se ejecuta en commits a `main` y PRs, además de cada domingo a las 3 AM.

### 16. **Locust** - Pruebas de Carga Backend

**Herramienta:** `locust`

**Qué verifica:**
- ✅ Tiempo de respuesta bajo carga
- ✅ Throughput del API
- ✅ Comportamiento con múltiples usuarios concurrentes

**Configuración de prueba:**
- Usuarios: 10
- Spawn rate: 2
- Duración: 2 minutos

---

### 17. **Pytest Benchmark** - Benchmarks de Performance

**Herramienta:** `pytest-benchmark`

**Qué verifica:**
- ✅ Tiempo de ejecución de funciones críticas
- ✅ Performance de endpoints específicos
- ✅ Comparación con ejecuciones anteriores

**Objetivos:**
- Health check: < 100ms
- Lista de clientes: < 500ms

---

### 18. **Lighthouse CI** - Performance Frontend

**Herramienta:** `lighthouse-ci`

**Qué verifica:**
- ✅ Performance score
- ✅ Accessibility
- ✅ Best practices
- ✅ SEO

**Objetivo:** Score > 90

---

### 19. **Bundle Analyzer** - Análisis de Tamaño Frontend

**Herramienta:** `webpack-bundle-analyzer`

**Qué verifica:**
- ✅ Tamaño del bundle JavaScript
- ✅ Análisis de dependencias
- ✅ Oportunidades de optimización

**Objetivo:** Bundle < 1MB

---

## 🧪 **Pruebas Unitarias e Integración**

### Backend

- **Framework:** `pytest`
- **Cobertura:** `pytest-cov`
- **Tests asíncronos:** `pytest-asyncio`
- **Reportes:** XML, HTML

**Ejecuta:**
- Pruebas unitarias: `tests/unit/`
- Pruebas de integración: `tests/integration/`
- Cobertura de código

### Frontend

- **Framework:** `vitest`
- **Scripts:**
  - `npm run test:unit` - Pruebas unitarias
  - `npm run test:integration` - Pruebas de integración
  - `npm run test:coverage` - Reporte de cobertura

---

## 📋 **Resumen de Herramientas por Categoría**

### ✅ **Linting y Estilo (Backend)**
1. Flake8 - Análisis estático
2. Black - Formateo automático
3. Isort - Orden de imports

### ✅ **Linting y Estilo (Frontend)**
4. ESLint - Análisis estático
5. Prettier - Formateo automático
6. TypeScript - Verificación de tipos

### ✅ **Verificación de Tipos**
7. Mypy - Tipos Python
8. TypeScript - Tipos Frontend

### ✅ **Seguridad**
9. Safety - Vulnerabilidades Python
10. Bandit - Análisis de seguridad Python
11. Semgrep - Análisis estático de seguridad
12. NPM Audit - Vulnerabilidades npm
13. Snyk - Análisis de seguridad Frontend
14. TruffleHog - Detección de secretos
15. GitLeaks - Secretos en Git
16. Dependency Review - Revisión de dependencias en PRs

### ✅ **Performance**
17. Locust - Pruebas de carga
18. Pytest Benchmark - Benchmarks
19. Lighthouse CI - Performance frontend
20. Bundle Analyzer - Análisis de tamaño

### ✅ **Testing**
21. Pytest - Pruebas backend
22. Vitest - Pruebas frontend

---

## 🚨 **Comportamiento de Fallos**

### Bloquean el pipeline:
- ❌ Errores críticos de Flake8 (E9, F63, F7, F82)
- ❌ TypeScript compilation errors
- ❌ Falla en pruebas unitarias/integración
- ❌ Fallo en build del frontend
- ❌ Vulnerabilidades críticas de seguridad (moderate+)
- ❌ Dependency review falla (en PRs)

### No bloquean (solo warnings):
- ⚠️ Flake8 análisis completo (complejidad, estilo)
- ⚠️ Black format check (se aplica automáticamente)
- ⚠️ Isort check (se reporta pero no bloquea)
- ⚠️ Mypy (modo informativo)
- ⚠️ Performance tests (informativos)

---

## 📊 **Artefactos Generados**

Cada workflow genera logs y reportes descargables:

- `flake8-critical.log` - Errores críticos
- `flake8-full.log` - Análisis completo
- `black.log` - Cambios de formato
- `isort.log` - Cambios de imports
- `mypy.log` - Errores de tipos
- `safety-report.json` - Vulnerabilidades Python
- `bandit-report.json` - Problemas de seguridad
- `semgrep-report.json` - Análisis estático
- `npm-audit-report.json` - Vulnerabilidades npm
- `performance-report.html` - Reporte de carga
- `bundle-report.html` - Análisis de bundle

**Retención:** 90 días

---

## 🔧 **Configuración Local**

Para ejecutar las mismas verificaciones localmente:

```powershell
# Backend
cd backend
py -m flake8 app/
py -m black app/
py -m isort app/
py -m mypy app/

# Frontend
cd frontend
npm run lint
npm run format:check
npm run type-check
```

---

**Última actualización:** 2025-01-30

