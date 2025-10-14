# 👥 Módulo de Gestión de Usuarios

## 📋 **DESCRIPCIÓN**

Módulo completo de gestión de usuarios del sistema RapiCredit, integrado en la sección de Configuración.

---

## 🎯 **CARACTERÍSTICAS**

### **✅ CRUD Completo:**
- ✅ **Crear** usuarios con validación de datos
- ✅ **Leer** lista de usuarios con filtros y búsqueda
- ✅ **Actualizar** información de usuarios existentes
- ✅ **Eliminar** usuarios del sistema
- ✅ **Ver** detalles completos de cada usuario

### **🔍 Filtros y Búsqueda:**
- 🔎 Búsqueda por nombre, email o rol
- 🟢 Filtro por usuarios activos
- 🔴 Filtro por usuarios inactivos
- 📊 Vista de todos los usuarios

### **👤 Información de Usuario:**
- Email (único)
- Nombre y apellido
- Rol con permisos específicos
- Estado (activo/inactivo)
- Fecha de creación
- Último acceso al sistema

---

## 🎭 **ROLES DEL SISTEMA**

### **1. 👑 ADMIN - Administrador**
**Descripción:** Acceso total al sistema
**Permisos:**
- ✅ Gestión completa de usuarios
- ✅ Gestión completa de clientes
- ✅ Modificar/anular pagos sin aprobación
- ✅ Generar todos los reportes
- ✅ Configurar parámetros del sistema
- ✅ Aprobar/rechazar todas las solicitudes
- ✅ Realizar carga masiva
- ✅ Ver logs completos del sistema
- ✅ Dashboard administrativo completo

### **2. 📊 GERENTE**
**Descripción:** Supervisión y aprobaciones
**Permisos:**
- ✅ Ver todos los clientes
- ✅ Aprobar préstamos hasta cierto monto
- ✅ Ver reportes de su área
- ✅ Supervisar asesores
- ⚠️ No puede eliminar usuarios

### **3. 🎯 DIRECTOR**
**Descripción:** Decisiones estratégicas
**Permisos:**
- ✅ Aprobar préstamos de alto monto
- ✅ Ver KPIs globales
- ✅ Acceso a reportes estratégicos
- ✅ Revisar rendimiento general

### **4. 💰 COBRANZAS**
**Descripción:** Gestión de cobros
**Permisos:**
- ✅ Ver clientes con mora
- ✅ Registrar pagos
- ✅ Enviar notificaciones de cobranza
- ✅ Gestionar calendario de pagos
- ⚠️ No puede aprobar préstamos

### **5. 🤝 COMERCIAL**
**Descripción:** Ventas y clientes
**Permisos:**
- ✅ Crear clientes
- ✅ Solicitar préstamos
- ✅ Ver cartera asignada
- ✅ Ver reportes de ventas

### **6. 👔 ASESOR**
**Descripción:** Atención al cliente
**Permisos:**
- ✅ Ver clientes asignados
- ✅ Actualizar información de clientes
- ✅ Registrar interacciones
- ⚠️ No puede aprobar préstamos

### **7. 📈 CONTADOR**
**Descripción:** Gestión financiera
**Permisos:**
- ✅ Ver todos los pagos
- ✅ Generar reportes financieros
- ✅ Realizar conciliaciones
- ✅ Ver estados de cuenta

### **8. 🏛️ COMITE**
**Descripción:** Revisión de casos especiales
**Permisos:**
- ✅ Revisar casos especiales
- ✅ Aprobar préstamos complejos
- ✅ Decisiones colegiadas

---

## 🖥️ **INTERFAZ DE USUARIO**

### **Dashboard de Usuarios:**
```
┌─────────────────────────────────────────────────────────┐
│ 👥 Gestión de Usuarios          [+ Nuevo Usuario]      │
├─────────────────────────────────────────────────────────┤
│ 🔍 [Buscar...] [Todos] [Activos] [Inactivos] [↻]      │
├─────────────────────────────────────────────────────────┤
│ Usuario          │ Rol          │ Estado  │ Acciones   │
├──────────────────┼──────────────┼─────────┼────────────┤
│ JD Juan Díaz     │ 👑 Admin     │ ✅ Activo│ 👁️ ✏️ 🗑️   │
│ admin@...        │              │         │            │
├──────────────────┼──────────────┼─────────┼────────────┤
│ MP María Pérez   │ 👔 Asesor    │ ✅ Activo│ 👁️ ✏️ 🗑️   │
│ maria@...        │              │         │            │
└─────────────────────────────────────────────────────────┘
```

### **Modal Crear/Editar Usuario:**
```
┌─────────────────────────────────────────┐
│ ➕ Nuevo Usuario                    [✕] │
├─────────────────────────────────────────┤
│ Email *                                 │
│ [usuario@ejemplo.com]                   │
│                                         │
│ Nombre *          Apellido *            │
│ [Nombre]          [Apellido]            │
│                                         │
│ Rol *                                   │
│ [👔 Asesor - Atención al cliente ▼]     │
│                                         │
│ Contraseña *                            │
│ [••••••••] (Mínimo 8 caracteres)        │
│                                         │
│ ☑ Usuario activo                        │
│                                         │
│           [Cancelar] [💾 Crear Usuario]  │
└─────────────────────────────────────────┘
```

### **Modal Ver Detalles:**
```
┌─────────────────────────────────────────┐
│ 👁️ Detalles del Usuario             [✕] │
├─────────────────────────────────────────┤
│         ┌────┐                          │
│         │ JD │ Juan Díaz                │
│         └────┘ juan@ejemplo.com         │
├─────────────────────────────────────────┤
│ Rol:              👑 Administrador      │
│ Estado:           ✅ Activo              │
│ Fecha creación:   15 de enero, 2025    │
│ Último acceso:    14 de octubre, 2025  │
│                   10:30 AM              │
├─────────────────────────────────────────┤
│ 🛡️ Permisos de Administrador            │
│ Este usuario tiene acceso completo a    │
│ todas las funcionalidades del sistema   │
│                                         │
│                   [Cerrar] [✏️ Editar]   │
└─────────────────────────────────────────┘
```

---

## 🔐 **VALIDACIONES Y SEGURIDAD**

### **Validaciones de Creación:**
- ✅ Email único en el sistema
- ✅ Formato de email válido
- ✅ Contraseña mínimo 8 caracteres
- ✅ Contraseña con mayúsculas, minúsculas y números
- ✅ Nombre y apellido requeridos
- ✅ Rol válido del sistema

### **Validaciones de Actualización:**
- ✅ Email único (si se cambia)
- ✅ Contraseña opcional (solo si se proporciona)
- ✅ No permitir eliminar el último administrador activo

### **Seguridad:**
- 🔐 Solo usuarios **ADMIN** pueden acceder al módulo
- 🔒 Contraseñas hasheadas con bcrypt
- 🛡️ Validación de permisos en backend
- 📝 Registro en auditoría de cambios

---

## 📡 **ENDPOINTS DEL BACKEND**

### **GET /api/v1/users/**
Lista usuarios con paginación y filtros
```json
Params:
- page: número de página (default: 1)
- page_size: tamaño de página (default: 10, max: 100)
- is_active: filtrar por estado (true/false/undefined)

Response:
{
  "users": [...],
  "total": 50,
  "page": 1,
  "page_size": 10
}
```

### **GET /api/v1/users/{user_id}**
Obtener un usuario específico

### **POST /api/v1/users/**
Crear nuevo usuario
```json
Body:
{
  "email": "nuevo@ejemplo.com",
  "nombre": "Juan",
  "apellido": "Pérez",
  "rol": "ASESOR",
  "password": "Password123!",
  "is_active": true
}
```

### **PUT /api/v1/users/{user_id}**
Actualizar usuario existente
```json
Body:
{
  "email": "actualizado@ejemplo.com",
  "nombre": "Juan Carlos",
  "apellido": "Pérez",
  "rol": "GERENTE",
  "password": "NuevaPassword123!", // opcional
  "is_active": true
}
```

### **DELETE /api/v1/users/{user_id}**
Eliminar usuario

### **GET /api/v1/users/verificar-admin**
Verificar estado de administradores en el sistema

---

## 🔄 **FLUJO DE TRABAJO**

### **Crear Usuario:**
```
1. Admin accede a Configuración > Usuarios
2. Click en "Nuevo Usuario"
3. Llena formulario con datos
4. Selecciona rol apropiado
5. Define contraseña segura
6. Guarda el usuario
7. Sistema valida y crea usuario
8. Lista se actualiza automáticamente
```

### **Editar Usuario:**
```
1. Busca usuario en la lista
2. Click en icono de editar (✏️)
3. Modifica campos necesarios
4. Opcionalmente cambia contraseña
5. Guarda cambios
6. Sistema valida y actualiza
```

### **Eliminar Usuario:**
```
1. Click en icono de eliminar (🗑️)
2. Confirma la acción
3. Sistema verifica que no sea el último admin
4. Elimina usuario
5. Lista se actualiza
```

---

## 📊 **CASOS DE USO**

### **Caso 1: Nuevo Empleado**
```
Situación: Contratan un nuevo asesor comercial
Acción:
1. Admin crea usuario con rol "ASESOR"
2. Asigna email corporativo
3. Genera contraseña temporal
4. Usuario recibe credenciales
5. Cambia contraseña en primer acceso
```

### **Caso 2: Promoción de Empleado**
```
Situación: Asesor es promovido a Gerente
Acción:
1. Admin edita usuario
2. Cambia rol de "ASESOR" a "GERENTE"
3. Sistema actualiza permisos automáticamente
4. Usuario ahora tiene acceso a funciones de gerente
```

### **Caso 3: Empleado Inactivo**
```
Situación: Empleado sale de vacaciones o renuncia
Acción:
1. Admin edita usuario
2. Desmarca "Usuario activo"
3. Usuario no puede iniciar sesión
4. Se mantiene histórico de actividades
```

---

## 🎨 **CARACTERÍSTICAS VISUALES**

### **Estados:**
- 🟢 **Activo:** Badge verde con ícono ✓
- 🔴 **Inactivo:** Badge rojo con ícono ✗

### **Avatares:**
- Círculo con iniciales del usuario
- Color de fondo basado en rol
- Tamaño adaptable

### **Iconos por Rol:**
- 👑 Admin
- 📊 Gerente
- 🎯 Director
- 💰 Cobranzas
- 🤝 Comercial
- 👔 Asesor
- 📈 Contador
- 🏛️ Comité

---

## ⚙️ **CONFIGURACIÓN TÉCNICA**

### **Frontend:**
- **Archivo:** `frontend/src/components/configuracion/UsuariosConfig.tsx`
- **Servicio:** `frontend/src/services/userService.ts`
- **Framework:** React + TypeScript
- **Estilos:** Tailwind CSS
- **Iconos:** Lucide React

### **Backend:**
- **Archivo:** `backend/app/api/v1/endpoints/users.py`
- **Modelos:** `backend/app/models/user.py`
- **Schemas:** `backend/app/schemas/user.py`
- **Permisos:** `backend/app/core/permissions.py`

---

## 🚀 **PRÓXIMAS MEJORAS**

### **Fase 2:**
- [ ] Cambio de contraseña desde el perfil del usuario
- [ ] Recuperación de contraseña por email
- [ ] Autenticación de dos factores (2FA)
- [ ] Historial de actividades por usuario
- [ ] Exportar lista de usuarios a Excel/PDF

### **Fase 3:**
- [ ] Permisos granulares personalizados
- [ ] Grupos de usuarios
- [ ] Delegación temporal de permisos
- [ ] Notificaciones de login sospechoso
- [ ] Sesiones activas y cierre remoto

---

## 📝 **NOTAS IMPORTANTES**

⚠️ **Advertencias:**
- No eliminar el último usuario ADMIN activo
- Cambiar contraseña por defecto inmediatamente
- Revisar permisos antes de asignar roles
- Mantener actualizada la lista de usuarios activos

✅ **Buenas Prácticas:**
- Usar emails corporativos
- Asignar el rol mínimo necesario
- Desactivar usuarios en lugar de eliminarlos
- Revisar logs de auditoría regularmente
- Cambiar contraseñas periódicamente

---

## 🆘 **SOPORTE**

### **Problemas Comunes:**

**"Email ya está registrado"**
- Verificar que el email sea único
- Revisar usuarios inactivos con ese email

**"Error al crear usuario"**
- Verificar formato de email
- Verificar longitud de contraseña
- Revisar permisos del usuario actual

**"No se pueden cargar usuarios"**
- Verificar conexión al backend
- Verificar que el usuario sea ADMIN
- Revisar logs del servidor

---

## 📊 **ESTADÍSTICAS**

- **Roles disponibles:** 8
- **Campos por usuario:** 7
- **Filtros disponibles:** 3
- **Acciones por usuario:** 3 (ver, editar, eliminar)
- **Validaciones:** 6
- **Endpoints:** 5

**Módulo completo y listo para producción** ✅

