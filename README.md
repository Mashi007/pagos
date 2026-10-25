# Pagos – RapiCredit

Sistema de gestión de pagos, préstamos, notificaciones de cobranza y reportes (RapiCredit).

- **Backend**: FastAPI (Python), PostgreSQL, SQLAlchemy, Alembic.
- **Frontend**: React, TypeScript, Vite.

## Requisitos

- Python 3.x (backend)
- Node.js ≥ 20 (frontend)
- PostgreSQL
- Variables de entorno: ver `backend/.env.example` / `backend/.env.ejemplo` y [`docs/env/ENV_VARIABLES_DEPLOY.md`](docs/env/ENV_VARIABLES_DEPLOY.md).

## Desarrollo rápido

### Backend

```bash
cd backend
# Crear venv, instalar dependencias (pip/uv)
# Configurar .env con DATABASE_URL, SECRET_KEY, etc.
uvicorn app.main:app --reload
```

API: `http://localhost:8000`, docs: `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Documentación

Índice canónico: **[`docs/README.md`](docs/README.md)** (deploy, email, scheduler, reglas, arquitectura).
