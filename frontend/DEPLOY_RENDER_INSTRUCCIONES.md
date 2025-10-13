# RAPICREDIT - Configuración de Despliegue en Render

## 🚀 INSTRUCCIONES PASO A PASO

### **📋 OPCIÓN 1: Usar render.yaml (Automático)**

1. **Ve a**: https://dashboard.render.com
2. **Click**: "New +" → "Blueprint"
3. **Conecta**: Tu repositorio GitHub
4. **Render detectará automáticamente** el archivo `render.yaml`
5. **Click**: "Apply" para crear el servicio

### **📋 OPCIÓN 2: Crear Manualmente (Si Blueprint falla)**

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

### **🔍 VERIFICACIÓN DEL DESPLIEGUE:**

#### **✅ Logs Exitosos:**
```
✅ Installing dependencies...
✅ Building application...
✅ Static files generated successfully
✅ Service deployed at https://rapicredit-frontend.onrender.com
```

#### **❌ Logs de Error Comunes:**
```
❌ Module not found: Can't resolve...
❌ Build failed with exit code 1
❌ No files found in dist directory
```

### **🆘 SOLUCIÓN DE PROBLEMAS:**

#### **❌ Error: "Build failed"**
- Verificar que `Root Directory` sea exactamente: `frontend`
- Verificar que `Build Command` sea: `npm install && npm run build`
- Verificar que `Publish Directory` sea: `dist`

#### **❌ Error: "404 Not Found"**
- Verificar que el servicio esté desplegado
- Verificar que la URL sea correcta
- Verificar los logs en Render Dashboard

#### **❌ Error: "Module not found"**
- Verificar que todas las dependencias estén en `package.json`
- Verificar que no haya errores de TypeScript

### **🎯 RESULTADO ESPERADO:**

Después del despliegue exitoso:
- **URL**: https://rapicredit-frontend.onrender.com
- **Estado**: ✅ Live
- **Build**: ✅ Successful
- **Frontend**: ✅ Funcionando con RAPICREDIT

### **🚀 PRÓXIMOS PASOS:**

1. **Crear/Recrear** el servicio en Render usando las instrucciones
2. **Verificar** que el build sea exitoso
3. **Probar** la URL una vez desplegado
4. **Verificar** que el login funcione correctamente

¡El frontend de RAPICREDIT debería funcionar perfectamente!
