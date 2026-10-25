# SQL

Scripts SQL **manuales** (DBeaver / ops). El esquema de producción lo gestiona **Alembic** (`backend/alembic/versions/`).

## Contenido

- `migrations/` — SQL auxiliares / vistas / columnas puntuales (no sustituyen Alembic).

## Ops relacionados

- Backup: `scripts/backup_bd_opcion_a.py`
- Health: `scripts/verificar-backend.sh`
- Runtime scripts: `backend/scripts/`
