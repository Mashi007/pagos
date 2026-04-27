# Frontend - Sistema de Pagos

Aplicación frontend construida con React y Vite.

## Desarrollo Local

```bash
npm install
npm run dev
```

## Build para Producción

```bash
npm run build
```

El build se genera en la carpeta `dist/`.

## Configuración en Render.com

- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `dist`
- **Node Version**: 20.11.0 (o superior)

## Runbooks operativos

- **Incidentes 502 del proxy (`rapicredit` -> `pagos`)**: [docs/runbook-502-proxy.md](docs/runbook-502-proxy.md)
