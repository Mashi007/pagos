# 🚀 Comandos para Render Dashboard - Frontend

## Comandos Correctos para Frontend

### ✅ Build Command
```
npm install && npm run build
```

### ✅ Start Command
```
node server.js
```

## Explicación

### Build Command
- `npm install`: Instala todas las dependencias del proyecto
- `npm run build`: Ejecuta Vite para compilar el proyecto React y generar los archivos en `dist/`

### Start Command
- `node server.js`: Inicia el servidor Express que sirve los archivos estáticos desde `dist/`

## Estructura Esperada Después del Build

Después del build, deberías tener:
```
frontend/
├── dist/
│   ├── index.html
│   ├── assets/
│   │   ├── index-[hash].js
│   │   └── index-[hash].css
│   └── vite.svg
└── server.js
```

## Verificación en Logs

Después del deploy, deberías ver en los logs:

### Build:
```
added X packages
> vite build
✓ built in Xms
dist/index.html                   X kB
dist/assets/index-[hash].js       X kB
dist/assets/index-[hash].css     X kB
```

### Start:
```
========================================
🚀 Servidor iniciado correctamente
📦 Puerto: [número]
📁 Directorio dist: [ruta]
✅ Dist existe: true
🌐 Aplicación disponible en: http://localhost:[puerto]
💚 Health check: http://localhost:[puerto]/health
========================================
✅ index.html encontrado
```

## Variables de Entorno Recomendadas

En Render Dashboard, configura estas variables de entorno:

```
NODE_VERSION=20.11.0
NODE_ENV=production
VITE_API_URL=https://pagos-f2qf.onrender.com
```

## Troubleshooting

### Error: "npm: command not found"
**Solución**: Verifica que `NODE_VERSION` esté configurado en las variables de entorno

### Error: "dist directory not found"
**Solución**: Verifica que el build se ejecutó correctamente revisando los logs del build

### Error: "Cannot find module 'express'"
**Solución**: Verifica que `npm install` se ejecutó correctamente y que `express` está en `package.json`

### Error: "EADDRINUSE: address already in use"
**Solución**: Render maneja esto automáticamente, pero si persiste, verifica que no haya otro proceso usando el puerto

---

*Documento creado el 2026-02-01*
