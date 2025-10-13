# Configuración específica para Render - RAPICREDIT

## 🚀 DESPLIEGUE EN RENDER - CONFIGURACIÓN CORRECTA

### **📋 OPCIÓN 1: Static Site (Recomendado)**

1. **Ve a**: https://dashboard.render.com
2. **Click**: "New +" → "Static Site"
3. **Conecta**: Tu repositorio GitHub
4. **Configura**:
   ```
   Name: rapicredit-frontend
   Branch: main
   Root Directory: frontend
   Build Command: npm install && npm run build
   Publish Directory: dist
   ```

5. **Variables de Entorno**:
   ```
   VITE_API_URL=https://pagos-f2qf.onrender.com
   VITE_NODE_ENV=production
   VITE_APP_NAME=RAPICREDIT - Sistema de Préstamos y Cobranza
   VITE_APP_VERSION=1.0.0
   ```

### **📋 OPCIÓN 2: Web Service (Si Static Site falla)**

1. **Ve a**: https://dashboard.render.com
2. **Click**: "New +" → "Web Service"
3. **Conecta**: Tu repositorio GitHub
4. **Configura**:
   ```
   Name: rapicredit-frontend
   Environment: Node
   Region: Oregon (US West)
   Branch: main
   Root Directory: frontend
   Build Command: npm install && npm run build
   Start Command: npm run serve
   ```

5. **Variables de Entorno**:
   ```
   PORT=10000
   VITE_API_URL=https://pagos-f2qf.onrender.com
   VITE_NODE_ENV=production
   NODE_ENV=production
   ```

### **🔍 VERIFICACIÓN DEL BUILD:**

Para verificar que el build funciona localmente:

```bash
cd frontend
npm install
npm run build
```

Si el build es exitoso, deberías ver:
- Carpeta `dist` creada
- Archivos estáticos generados
- Sin errores en la consola

### **🆘 SOLUCIÓN DE PROBLEMAS COMUNES:**

#### **❌ Error: "Build failed"**
- Verificar que `Root Directory` sea exactamente: `frontend`
- Verificar que `Build Command` sea: `npm install && npm run build`
- Verificar que `Publish Directory` sea: `dist`

#### **❌ Error: "Module not found"**
- Verificar que todas las dependencias estén en `package.json`
- Verificar que no haya errores de TypeScript

#### **❌ Error: "404 Not Found"**
- Verificar que el servicio esté desplegado correctamente
- Verificar que la URL sea correcta
- Verificar los logs en Render Dashboard

### **📊 LOGS IMPORTANTES A REVISAR:**

En Render Dashboard → Logs, busca:
- ✅ "Build completed successfully"
- ✅ "Static files generated"
- ✅ "Service deployed"
- ❌ Cualquier error de build o dependencias

### **🎯 RESULTADO ESPERADO:**

Después del despliegue exitoso:
- **URL**: https://rapicredit-frontend.onrender.com
- **Estado**: ✅ Live
- **Build**: ✅ Successful
- **Frontend**: ✅ Funcionando

### **🚀 PRÓXIMOS PASOS:**

1. **Crear/Recrear** el servicio en Render
2. **Verificar** la configuración
3. **Revisar** los logs durante el build
4. **Probar** la URL una vez desplegado

¡El frontend de RAPICREDIT debería funcionar perfectamente una vez configurado correctamente!
