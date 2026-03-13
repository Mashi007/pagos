# Pagos – RapiCredit

Sistema de gestión de pagos, préstamos, notificaciones de cobranza y reportes (RapiCredit).

- **Backend**: FastAPI (Python), PostgreSQL, SQLAlchemy, Alembic.
- **Frontend**: React, TypeScript, Vite.

## Requisitos

- Python 3.x (backend)
- Node.js ≥ 20 (frontend)
- PostgreSQL
- Variables de entorno: ver `backend/.env.example` y `backend/.env.ejemplo`.

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

- **Auditorías y mejoras**: [docs/AUDITORIA_INTEGRAL_Y_MEJORAS.md](docs/AUDITORIA_INTEGRAL_Y_MEJORAS.md)
- **Variables de plantillas (email/PDF)**: [docs/AUDITORIA_VARIABLES_PLANTILLAS_BD.md](docs/AUDITORIA_VARIABLES_PLANTILLAS_BD.md)
- **Despliegue**: ver `QUICK_START_DEPLOY.md`, `CHECKLIST_DEPLOY.md` y `backend/RENDER_CONFIGURACION.md` si aplica.
- **Tests**: `INSTRUCCIONES_EJECUTAR_TESTS.md`

## Estructura principal

- `backend/app/` – API, modelos, servicios, core (config, BD, auth).
- `frontend/src/` – Componentes, páginas, servicios, hooks.
- `docs/` – Auditorías, guías y documentación técnica.
