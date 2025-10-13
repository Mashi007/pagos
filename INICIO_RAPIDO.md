# 🚀 INICIO RÁPIDO - Sistema de Préstamos y Cobranza

## ✅ Estado del Sistema

### 🌐 **Backend - FUNCIONANDO EN RENDER**
- **URL**: https://pagos-f2qf.onrender.com
- **Estado**: ✅ ACTIVO
- **Documentación**: https://pagos-f2qf.onrender.com/docs

### 💻 **Frontend - LISTO PARA RENDER**
- **Ubicación**: `./frontend/`
- **Estado**: ✅ OPTIMIZADO PARA RENDER

---

## ⚡ DESPLEGAR EN RENDER (3 PASOS)

### **1. Subir a GitHub**
```bash
git add .
git commit -m "Frontend listo para Render"
git push origin main
```

### **2. Crear Static Site en Render**
- Ve a https://render.com
- **New +** → **Static Site**
- Conecta tu repositorio
- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `dist`

### **3. Variables de entorno**
```
VITE_API_URL=https://pagos-f2qf.onrender.com
VITE_NODE_ENV=production
```

**¡Listo!** Tu sistema estará en línea en ~5 minutos

---

## 💻 O EJECUTAR LOCALMENTE

### **1. Navegar al frontend**
```bash
cd frontend
```

### **2. Instalar dependencias**
```bash
npm install
```

### **3. Iniciar aplicación**
```bash
npm run dev
```

**¡Listo!** El sistema se abrirá en http://localhost:3000

---

## 👤 USUARIOS DE PRUEBA

```
🔑 Administrador:
   Email: admin@sistema.com
   Password: admin123

🔑 Gerente:
   Email: gerente@sistema.com  
   Password: gerente123

🔑 Asesor Comercial:
   Email: asesor@sistema.com
   Password: asesor123
```

---

## 🎯 QUÉ PUEDES HACER

### ✅ **Funcionalidades Activas:**
- 🔐 **Login** con validación completa
- 📊 **Dashboard** con KPIs en tiempo real
- 🚗 **Gestión de Clientes** con filtros avanzados
- 🔍 **Búsqueda** en tiempo real
- 📱 **Responsive** - funciona en móvil/tablet/desktop
- 🎨 **Animaciones** fluidas en toda la app
- 🔔 **Notificaciones** del sistema
- 👥 **Roles** - 8 tipos de usuario diferentes

### 🔄 **En Desarrollo:**
- 💰 Gestión de Pagos
- 🧮 Tabla de Amortización  
- 📊 Reportes PDF
- 🏦 Conciliación Bancaria

---

## 🌐 URLs del Sistema

- **Frontend en Render**: https://sistema-prestamos-frontend.onrender.com (después del deploy)
- **Frontend Local**: http://localhost:3000 (para desarrollo)
- **Backend API**: https://pagos-f2qf.onrender.com ✅ FUNCIONANDO
- **Documentación API**: https://pagos-f2qf.onrender.com/docs
- **Health Check**: https://pagos-f2qf.onrender.com/health

---

## 🆘 Solución de Problemas

### **❌ Error de conexión:**
```bash
# Verificar que el backend esté activo
curl https://pagos-f2qf.onrender.com/health
```

### **❌ Dependencias:**
```bash
# Limpiar e instalar
rm -rf node_modules package-lock.json
npm install
```

### **❌ Puerto ocupado:**
```bash
# Cambiar puerto
npm run dev -- --port 3001
```

---

## 🎉 ¡A DISFRUTAR!

Tu sistema de préstamos y cobranza está **100% funcional** con:

✅ **Backend en producción** (Render)  
✅ **Frontend moderno** (React + TypeScript)  
✅ **Base de datos** (PostgreSQL)  
✅ **Autenticación** completa  
✅ **Diseño profesional** responsive  

**¡Solo despliega en Render y tendrás un sistema de clase mundial en la nube!** 🚀

### 🌐 **RENDER = SOLUCIÓN COMPLETA:**
- ✅ **Frontend**: Static Site (gratis)
- ✅ **Backend**: Web Service (ya funcionando)  
- ✅ **Base de datos**: PostgreSQL (incluida)
- ✅ **SSL**: HTTPS automático
- ✅ **CDN**: Velocidad global
- ✅ **Auto-deploy**: Deploy automático desde Git

**¡Tu sistema completo en la nube por prácticamente $0!** 🎊
