# Configuración de GitHub para el proyecto

## 🔧 Secrets Requeridos

### Render.com
- `RENDER_SERVICE_ID`: ID del servicio principal
- `RENDER_STAGING_SERVICE_ID`: ID del servicio staging
- `RENDER_API_KEY`: API Key de Render
- `RENDER_SERVICE_URL`: URL del servicio principal
- `RENDER_STAGING_URL`: URL del servicio staging

### Notificaciones
- `SLACK_WEBHOOK_URL`: Webhook de Slack para notificaciones

### Seguridad (Opcional)
- `SNYK_TOKEN`: Token de Snyk para análisis de vulnerabilidades

## 📋 Configuración de Branches

### Branch Protection Rules
- `main`: Requiere PR, requiere tests, requiere reviews
- `develop`: Requiere PR, requiere tests

### Environments
- `production`: Requiere aprobación manual
- `staging`: Despliegue automático

## 🔔 Configuración de Notificaciones

### Slack
1. Crear webhook en Slack
2. Configurar canal de notificaciones
3. Agregar `SLACK_WEBHOOK_URL` a secrets

### Teams (Opcional)
1. Configurar webhook de Teams
2. Agregar `TEAMS_WEBHOOK_URL` a secrets

## 📊 Configuración de Codecov

1. Conectar repositorio con Codecov
2. Configurar umbrales de cobertura
3. Habilitar comentarios en PRs

## 🔒 Configuración de Seguridad

### Dependabot
1. Habilitar Dependabot alerts
2. Configurar auto-merge para patches
3. Configurar schedule de updates

### Code Scanning
1. Habilitar CodeQL
2. Configurar análisis automático
3. Configurar alertas de seguridad
