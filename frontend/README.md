# Sistema de Préstamos y Cobranza - Frontend

Frontend moderno desarrollado con React, TypeScript y Vite para el sistema de préstamos y cobranza.

## 🚀 Características

- **React 18** con TypeScript para desarrollo type-safe
- **Vite** para desarrollo rápido y builds optimizados
- **Tailwind CSS** + **Shadcn/ui** para diseño profesional
- **Zustand** para manejo de estado global
- **TanStack Query** para manejo de estado del servidor
- **React Hook Form** + **Zod** para formularios y validación
- **Framer Motion** para animaciones fluidas
- **React Router** para navegación
- **Responsive Design** adaptativo a todos los dispositivos

## 📦 Instalación

```bash
# Instalar dependencias
npm install

# Configurar variables de entorno
cp .env.example .env

# Iniciar servidor de desarrollo
npm run dev
```

## 🛠️ Scripts Disponibles

```bash
npm run dev          # Servidor de desarrollo
npm run build        # Build de producción
npm run preview      # Preview del build
npm run lint         # Linting con ESLint
npm run type-check   # Verificación de tipos
```

## 🏗️ Estructura del Proyecto

```
src/
├── components/          # Componentes React
│   ├── ui/             # Componentes base (Button, Input, etc.)
│   ├── layout/         # Layout principal (Header, Sidebar, Footer)
│   ├── auth/           # Componentes de autenticación
│   ├── dashboard/      # Componentes del dashboard
│   ├── clientes/       # Componentes de gestión de clientes
│   ├── pagos/          # Componentes de gestión de pagos
│   └── ...
├── pages/              # Páginas principales
├── hooks/              # Custom React hooks
├── services/           # Servicios de API
├── store/              # Estado global (Zustand)
├── types/              # Tipos TypeScript
├── utils/              # Utilidades y helpers
└── styles/             # Estilos globales
```

## 🎨 Sistema de Diseño

### Colores Principales
- **Primary**: Azul corporativo (#3B82F6)
- **Success**: Verde (#10B981)
- **Warning**: Amarillo (#F59E0B)
- **Error**: Rojo (#EF4444)
- **Info**: Azul claro (#06B6D4)

### Tipografía
- **Font Family**: Inter, system fonts
- **Sizes**: 12px, 14px, 16px, 18px, 20px, 24px, 30px, 36px

## 🔐 Sistema de Autenticación

### Roles de Usuario
- **ADMIN**: Acceso completo al sistema
- **GERENTE**: Gestión operativa completa
- **DIRECTOR**: Vista ejecutiva y reportes
- **ASESOR_COMERCIAL**: Ventas y clientes
- **COBRADOR**: Cobranza y seguimiento
- **CONTADOR**: Contabilidad y reportes
- **AUDITOR**: Solo lectura y auditoría
- **USUARIO**: Acceso básico

### Protección de Rutas
```tsx
// Proteger ruta por autenticación
<ProtectedRoute>
  <Component />
</ProtectedRoute>

// Proteger ruta por roles
<ProtectedRoute requiredRoles={['ADMIN', 'GERENTE']}>
  <Component />
</ProtectedRoute>
```

## 📱 Responsive Design

### Breakpoints
- **Mobile**: < 768px
- **Tablet**: 768px - 1023px
- **Desktop**: ≥ 1024px

### Navegación Adaptativa
- **Desktop**: Sidebar fijo
- **Tablet**: Sidebar colapsable
- **Mobile**: Bottom navigation + drawer

## 🔧 Configuración de Desarrollo

### Variables de Entorno
```env
VITE_API_URL=http://localhost:8080
VITE_NODE_ENV=development
VITE_APP_NAME="Sistema de Préstamos y Cobranza"
VITE_APP_VERSION="1.0.0"
```

### Proxy de Desarrollo
El servidor de desarrollo incluye un proxy automático para `/api` que redirige al backend en `localhost:8080`.

## 🚀 Despliegue

### Build de Producción
```bash
npm run build
```

### Preview Local
```bash
npm run preview
```

### Variables de Entorno de Producción
```env
VITE_API_URL=https://api.tudominio.com
VITE_NODE_ENV=production
```

## 📊 Funcionalidades Principales

### Dashboard Adaptativo
- KPIs en tiempo real
- Gráficos interactivos
- Alertas y notificaciones
- Acciones rápidas

### Gestión de Clientes
- CRUD completo
- Búsqueda avanzada
- Filtros múltiples
- Historial de pagos

### Sistema de Pagos
- Registro de pagos
- Distribución automática
- Comprobantes PDF
- Historial completo

### Tabla de Amortización
- 3 sistemas de amortización
- Cálculos automáticos
- Visualización interactiva
- Exportación Excel/PDF

### Reportes
- 5 reportes profesionales
- Filtros avanzados
- Exportación múltiple
- Visualización PDF

### Conciliación Bancaria
- Carga masiva de archivos
- Matching automático
- Revisión manual
- Resultados detallados

## 🔍 Testing

```bash
# Ejecutar tests (cuando estén implementados)
npm run test

# Coverage
npm run test:coverage
```

## 📝 Convenciones de Código

### Naming
- **Componentes**: PascalCase (`UserProfile.tsx`)
- **Hooks**: camelCase con prefijo `use` (`useAuth.ts`)
- **Utilidades**: camelCase (`formatCurrency.ts`)
- **Tipos**: PascalCase (`User`, `ApiResponse`)

### Estructura de Componentes
```tsx
// 1. Imports
import React from 'react'
import { ... } from '...'

// 2. Types/Interfaces
interface ComponentProps {
  // ...
}

// 3. Component
export function Component({ prop }: ComponentProps) {
  // 4. Hooks
  const [state, setState] = useState()
  
  // 5. Handlers
  const handleClick = () => {
    // ...
  }
  
  // 6. Render
  return (
    <div>
      {/* ... */}
    </div>
  )
}
```

## 🤝 Contribución

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto es privado y confidencial.

## 🆘 Soporte

Para soporte técnico, contactar al equipo de desarrollo.

---

**Sistema de Préstamos y Cobranza v1.0**  
© 2024 - Todos los derechos reservados
