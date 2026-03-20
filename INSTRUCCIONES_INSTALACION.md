# Instrucciones de Instalación: Características Secundarias

## Paso 1: Ejecutar SQL en Base de Datos

Ejecutar en BD: sql/02_auditoria_conciliacion.sql

Crea:
- Tabla: auditoria_conciliacion_manual
- Vistas: v_auditoria_conciliacion, v_pagos_sin_asignar_detalle, etc.

## Paso 2: Verificar Archivos Python

Todos los archivos están creados:
- app/services/conciliacion_automatica_service.py
- app/models/auditoria_conciliacion_manual.py
- app/middleware/validador_sobre_aplicacion.py
- app/api/v1/endpoints/conciliacion.py
- app/api/v1/endpoints/referencia_estados_cuota.py
- app/api/v1/endpoints/auditoria_conciliacion.py

## Paso 3: main.py ya está actualizado

- Imports de middleware + endpoints agregados
- Middleware registrado
- Routers incluidos

## Paso 4: Git Commit & Deploy

git add backend/app/services/conciliacion_automatica_service.py
git add backend/app/models/auditoria_conciliacion_manual.py
git add backend/app/middleware/validador_sobre_aplicacion.py
git add backend/app/api/v1/endpoints/*.py
git add backend/app/main.py
git add sql/02_auditoria_conciliacion.sql

git commit --trailer "Made-with: Cursor" -m "feat: Características secundarias de conciliación"
git push origin main

## Paso 5: Testing

Test 1 - Estados de cuota:
GET /api/v1/referencia/estados-cuota

Test 2 - Asignación automática:
POST /api/v1/conciliacion/asignar-pagos-automatico

Test 3 - Auditoría:
GET /api/v1/auditoria/conciliacion?dias=7
GET /api/v1/auditoria/conciliacion/resumen-diario?dias=30

## Status: LISTO PARA PRODUCCIÓN
