# 🚀 Comandos Completos para Deploy del Frontend

## 📋 Información del Proyecto

- **Servicio Render**: `rapicredit-frontend`
- **Branch**: `main`
- **Auto Deploy**: ✅ Habilitado
- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Start Command**: `npm run render-start`

---

## ✅ OPCIÓN 1: Deploy Automático (Recomendado)

Si tienes `autoDeploy: true` configurado, solo necesitas hacer commit y push:

### Paso 1: Verificar cambios
```bash
# Ver qué archivos fueron modificados
git status

# Ver los cambios específicos
git diff frontend/src/components/dashboard/DashboardFiltrosPanel.tsx
```

### Paso 2: Agregar cambios al staging
```bash
# Agregar todos los cambios
git add .

# O agregar archivos específicos
git add frontend/src/components/dashboard/DashboardFiltrosPanel.tsx
git add frontend/src/pages/DashboardMenu.tsx
git add frontend/src/hooks/useDashboardFiltros.ts
```

### Paso 3: Hacer commit
```bash
git commit -m "feat: Agregar botón 'Aplicar Filtros' al panel de filtros del dashboard

- Implementar estado temporal de filtros (filtrosTemporales)
- Agregar botones 'Aplicar Filtros' y 'Cancelar'
- Los filtros solo se aplican al hacer clic en 'Aplicar Filtros'
- Cerrar popover automáticamente después de aplicar/cancelar
- Incluir período en queryKey de todas las queries para reactividad"
```

### Paso 4: Push a main (dispara deploy automático)
```bash
git push origin main
```

### Paso 5: Monitorear el deploy
1. Ve a: https://dashboard.render.com
2. Selecciona el servicio `rapicredit-frontend`
3. Ve a la pestaña **"Events"** o **"Logs"**
4. Espera a que termine el build (verás mensajes como):
   ```
   ==> Building...
   ==> npm install && npm run build
   ==> Build successful
   ==> Starting...
   ==> npm run render-start
   ```

---

## 🔧 OPCIÓN 2: Deploy Manual desde Render Dashboard

Si prefieres hacer deploy manual o el auto-deploy no funciona:

### Paso 1: Verificar que los cambios están en el repositorio
```bash
# Verificar que el commit está en main
git log origin/main --oneline -5

# Deberías ver tu commit reciente
```

### Paso 2: Ir al Dashboard de Render
1. Abre: https://dashboard.render.com
2. Inicia sesión
3. Selecciona el servicio `rapicredit-frontend`

### Paso 3: Forzar Deploy Manual
1. Ve a la pestaña **"Events"** o **"Deploys"**
2. Haz clic en **"Manual Deploy"**
3. Selecciona **"Deploy latest commit"**
4. Confirma el deploy

### Paso 4: Monitorear el deploy
- Ve a la pestaña **"Logs"** para ver el progreso
- Espera a que termine el build y el servicio inicie

---

## 🛠️ OPCIÓN 3: Build Local y Verificación

Si quieres verificar que el build funciona localmente antes de deployar:

### Paso 1: Navegar al directorio del frontend
```bash
cd frontend
```

### Paso 2: Instalar dependencias (si no están instaladas)
```bash
npm install
```

### Paso 3: Ejecutar type-check (verificar TypeScript)
```bash
npm run type-check
```

### Paso 4: Ejecutar build local
```bash
npm run build
```

### Paso 5: Verificar que se generó la carpeta dist
```bash
# En Windows PowerShell
dir dist

# En Linux/Mac
ls -la dist
```

### Paso 6: Preview local (opcional)
```bash
npm run preview
```

Luego abre: http://localhost:4173

---

## 🔍 Verificación Post-Deploy

### 1. Verificar que el servicio está activo
```bash
# Verificar health check
curl https://rapicredit.onrender.com/health

# Debería responder: OK o similar
```

### 2. Verificar en el navegador
1. Abre: https://rapicredit.onrender.com
2. Inicia sesión
3. Ve al Dashboard
4. Abre el panel de filtros
5. **Verifica que aparece el botón "Aplicar Filtros"** al final del panel

### 3. Probar funcionalidad
1. Abre el panel de filtros
2. Cambia algún filtro (analista, concesionario, modelo, fechas)
3. **Verifica que NO se aplican automáticamente** (no deberían aparecer peticiones HTTP)
4. Haz clic en **"Aplicar Filtros"**
5. **Verifica que ahora SÍ se aplican** (deberían aparecer peticiones HTTP)
6. Verifica que el popover se cierra automáticamente

---

## 🚨 Troubleshooting

### Problema: El deploy falla en el build

**Solución:**
```bash
# Limpiar node_modules y reinstalar
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

Si funciona localmente, el problema puede ser:
- Variables de entorno faltantes en Render
- Versión de Node.js incorrecta
- Cache corrupto en Render

**Solución en Render:**
1. Ve a Settings → Clear Build Cache
2. Haz Manual Deploy nuevamente

### Problema: El servicio no inicia

**Verificar logs en Render:**
1. Ve a la pestaña **"Logs"**
2. Busca errores como:
   - `Error: Cannot find module`
   - `EADDRINUSE` (puerto ocupado)
   - `ENOENT` (archivo no encontrado)

**Solución común:**
- Verificar que `server.js` existe en `frontend/`
- Verificar que `dist/` se generó correctamente
- Verificar variables de entorno

### Problema: Los cambios no aparecen después del deploy

**Posibles causas:**
1. **Cache del navegador**: 
   - Presiona `Ctrl + Shift + R` (hard refresh)
   - O abre en modo incógnito

2. **CDN/Cache de Render**:
   - Espera 1-2 minutos
   - O limpia cache en Render Settings

3. **El commit no está en main**:
   ```bash
   git log origin/main --oneline -5
   # Verifica que tu commit está ahí
   ```

---

## 📝 Comandos Rápidos (Resumen)

```bash
# 1. Verificar cambios
git status

# 2. Agregar cambios
git add .

# 3. Commit
git commit -m "feat: Agregar botón 'Aplicar Filtros' al panel de filtros"

# 4. Push (dispara deploy automático)
git push origin main

# 5. Monitorear (en otra terminal o en Render Dashboard)
# Ve a: https://dashboard.render.com → rapicredit-frontend → Logs
```

---

## ✅ Checklist Pre-Deploy

- [ ] Cambios guardados en archivos
- [ ] `git status` muestra los archivos correctos
- [ ] Build local funciona (`npm run build`)
- [ ] Type-check pasa (`npm run type-check`)
- [ ] Commit hecho con mensaje descriptivo
- [ ] Push a `main` realizado
- [ ] Deploy monitoreado en Render Dashboard
- [ ] Servicio iniciado correctamente (ver logs)
- [ ] Funcionalidad verificada en producción

---

## 🔗 Enlaces Útiles

- **Render Dashboard**: https://dashboard.render.com
- **Servicio Frontend**: https://dashboard.render.com/web/rapicredit-frontend
- **URL Producción**: https://rapicredit.onrender.com
- **Health Check**: https://rapicredit.onrender.com/health

---

## 📌 Notas Importantes

1. **Auto Deploy**: Si está habilitado, cada push a `main` dispara un deploy automático
2. **Tiempo de Build**: El build puede tardar 2-5 minutos
3. **Tiempo de Inicio**: El servicio puede tardar 30-60 segundos en iniciar
4. **Cache**: Los cambios pueden tardar 1-2 minutos en aparecer debido a cache
5. **Variables de Entorno**: Ya están configuradas en Render, no necesitas cambiarlas

---

**¡Listo! Con estos comandos puedes hacer el deploy completo del frontend.** 🚀

