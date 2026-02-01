import { useEffect, useState, lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

// Layout
import { Layout } from './components/layout/Layout'

// Auth
import { SimpleProtectedRoute } from './components/auth/SimpleProtectedRoute'
import { useSimpleAuth } from './store/simpleAuthStore'

// Helper: ante fallo de carga de chunk (404 tras deploy), recargar página para obtener assets actualizados
function lazyWithRetry<T>(
  factory: () => Promise<{ default: React.ComponentType<T> }>
): React.LazyExoticComponent<React.ComponentType<T>> {
  return lazy(() =>
    factory().catch((err: unknown) => {
      const msg = (err && typeof (err as Error).message === 'string'
        ? (err as Error).message
        : err != null ? String(err) : ''
      ).toLowerCase()
      const isChunkLoadError =
        msg.indexOf('dynamically imported module') !== -1 ||
        msg.indexOf('error loading dynamically imported') !== -1 ||
        msg.indexOf('failed to fetch') !== -1 ||
        msg.indexOf('error loading') !== -1 ||
        msg.indexOf('loading dynamically imported') !== -1 ||
        msg.indexOf('imported module') !== -1 ||
        msg.indexOf('/assets/') !== -1 ||
        (msg.indexOf('chunk') !== -1 && msg.indexOf('load') !== -1)
      if (isChunkLoadError && typeof window !== 'undefined') {
        const base = window.location.pathname + window.location.search
        const sep = base.indexOf('?') !== -1 ? '&' : '?'
        window.location.replace(base + sep + '_=' + Date.now())
        return new Promise(() => {}) // no resolver para no renderizar estado roto
      }
      throw err
    })
  )
}

// Constantes de configuración
const ANIMATION_DURATION = 0.3
const NOT_FOUND_TEXT_SIZE_LARGE = 6
const NOT_FOUND_TEXT_SIZE_MEDIUM = 2
const SPACING_SMALL = 4
const SPACING_MEDIUM = 6
const SPACING_LARGE = 12
const SPACING_XL = 6
const SPINNER_SIZE = 12
const BORDER_WIDTH = 2

// Pages - Lazy loading con retry ante 404 de chunks (cache desactualizado tras deploy)
const Welcome = lazyWithRetry(() => import('./pages/Welcome').then(module => ({ default: module.Welcome })))
const Login = lazyWithRetry(() => import('./pages/Login').then(module => ({ default: module.Login })))
// ✅ DashboardMenu importado normalmente (no lazy) para asegurar que React esté disponible
// Los componentes UI que usa (Radix UI) requieren React como namespace y fallan con lazy loading
import { DashboardMenu } from './pages/DashboardMenu'
const Clientes = lazyWithRetry(() => import('./pages/Clientes').then(module => ({ default: module.Clientes })))
const Prestamos = lazyWithRetry(() => import('./pages/Prestamos').then(module => ({ default: module.Prestamos })))
const Amortizacion = lazyWithRetry(() => import('./pages/Amortizacion').then(module => ({ default: module.Amortizacion })))
const Reportes = lazyWithRetry(() => import('./pages/Reportes').then(module => ({ default: module.Reportes })))
const Cobranzas = lazyWithRetry(() => import('./pages/Cobranzas').then(module => ({ default: module.Cobranzas })))
const Auditoria = lazyWithRetry(() => import('./pages/Auditoria').then(module => ({ default: module.Auditoria })))
const ChatAI = lazyWithRetry(() => import('./pages/ChatAI').then(module => ({ default: module.ChatAI })))
const Notificaciones = lazyWithRetry(() => import('./pages/Notificaciones').then(module => ({ default: module.Notificaciones })))
const Programador = lazyWithRetry(() => import('./pages/Programador').then(module => ({ default: module.Programador })))
const Plantillas = lazyWithRetry(() => import('./pages/Plantillas').then(module => ({ default: module.Plantillas })))
const Configuracion = lazyWithRetry(() => import('./pages/Configuracion').then(module => ({ default: module.Configuracion })))
const Analistas = lazyWithRetry(() => import('./pages/Analistas').then(module => ({ default: module.Analistas })))
const PagosPage = lazyWithRetry(() => import('./pages/PagosPage').then(module => ({ default: module.default })))
const AmortizacionPage = lazyWithRetry(() => import('./pages/AmortizacionPage').then(module => ({ default: module.AmortizacionPage })))
const ReportesPage = lazyWithRetry(() => import('./pages/ReportesPage').then(module => ({ default: module.ReportesPage })))
const VisualizacionBD = lazyWithRetry(() => import('./pages/VisualizacionBD').then(module => ({ default: module.VisualizacionBD })))
const Validadores = lazyWithRetry(() => import('./pages/Validadores').then(module => ({ default: module.Validadores })))
const Concesionarios = lazyWithRetry(() => import('./pages/Concesionarios').then(module => ({ default: module.Concesionarios })))
const ModelosVehiculos = lazyWithRetry(() => import('./pages/ModelosVehiculos').then(module => ({ default: module.ModelosVehiculos })))
const Usuarios = lazyWithRetry(() => import('./pages/Usuarios').then(module => ({ default: module.Usuarios })))
const Solicitudes = lazyWithRetry(() => import('./pages/Solicitudes').then(module => ({ default: module.Solicitudes })))
const EmbudoClientes = lazyWithRetry(() => import('./pages/EmbudoClientes').then(module => ({ default: module.EmbudoClientes })))
const TicketsAtencion = lazyWithRetry(() => import('./pages/TicketsAtencion').then(module => ({ default: module.TicketsAtencion })))
const EmbudoConcesionarios = lazyWithRetry(() => import('./pages/EmbudoConcesionarios').then(module => ({ default: module.EmbudoConcesionarios })))
const Ventas = lazyWithRetry(() => import('./pages/Ventas').then(module => ({ default: module.Ventas })))
const ConversacionesWhatsAppPage = lazyWithRetry(() => import('./pages/ConversacionesWhatsApp').then(module => ({ default: module.ConversacionesWhatsAppPage })))
const ComunicacionesPage = lazyWithRetry(() => import('./pages/Comunicaciones').then(module => ({ default: module.ComunicacionesPage })))

// Todas las páginas ahora están importadas desde archivos reales

const NotFound = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center">
      <h1 className={`text-${NOT_FOUND_TEXT_SIZE_LARGE}xl font-bold text-gray-300 mb-${SPACING_SMALL}`}>404</h1>
      <h2 className={`text-${NOT_FOUND_TEXT_SIZE_MEDIUM}xl font-semibold text-gray-700 mb-${SPACING_SMALL}`}>
        Página no encontrada
      </h2>
      <p className={`text-gray-500 mb-${SPACING_MEDIUM}`}>
        La página que buscas no existe o ha sido movida.
      </p>
      <button
        onClick={() => window.history.back()}
        className="bg-primary text-primary-foreground px-6 py-2 rounded-lg hover:bg-primary/90 transition-colors"
      >
        Volver atrás
      </button>
    </div>
  </div>
)

// Componente de loading para Suspense
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center">
      <div className={`animate-spin rounded-full h-${SPINNER_SIZE} w-${SPINNER_SIZE} border-b-${BORDER_WIDTH} border-blue-600 mx-auto mb-${SPACING_SMALL}`}></div>
      <p className="text-gray-600">Cargando página...</p>
    </div>
  </div>
)

function App() {
  const { isAuthenticated, isLoading, initializeAuth } = useSimpleAuth()

  useEffect(() => {
    // Inicializar autenticación desde almacenamiento seguro CON VERIFICACIÓN AUTOMÁTICA
    initializeAuth()
  }, [initializeAuth])

  // Mostrar loader solo si está cargando Y hay datos de auth (para evitar flash)
  // Si no hay datos de auth, isLoading será false desde el inicio
  if (isLoading) {
    return <PageLoader />
  }

  return (
    <AnimatePresence mode="wait">
      <Suspense fallback={<PageLoader />}>
        <Routes>
        {/* Ruta de bienvenida - página por defecto */}
        <Route
          path="/"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard/menu" replace />
            ) : (
              <motion.div
                key="welcome"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: ANIMATION_DURATION }}
              >
                <Welcome />
              </motion.div>
            )
          }
        />

        {/* Ruta de login */}
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard/menu" replace />
            ) : (
              <motion.div
                key="login"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: ANIMATION_DURATION }}
              >
                <Login />
              </motion.div>
            )
          }
        />

        {/* Rutas protegidas */}
        <Route
          path="/*"
          element={
            <SimpleProtectedRoute>
              <Layout />
            </SimpleProtectedRoute>
          }
        >
          {/* Dashboard - DashboardMenu es el componente principal */}
          {/* Redirigir /dashboard a /dashboard/menu */}
          <Route path="dashboard" element={<Navigate to="/dashboard/menu" replace />} />
          <Route path="dashboard/menu" element={<DashboardMenu />} />

          {/* Clientes */}
          <Route path="clientes" element={<Clientes />} />
          <Route path="clientes/nuevo" element={<Clientes />} />
          <Route path="clientes/:id" element={<Clientes />} />

          {/* Préstamos */}
          <Route
            path="prestamos"
            element={<Prestamos />}
          />

          {/* Pagos */}
          <Route path="pagos" element={<PagosPage />} />
          <Route path="pagos/:id" element={<PagosPage />} />

          {/* Amortización */}
          <Route path="amortizacion" element={<AmortizacionPage />} />

          {/* Conciliación */}

          {/* Reportes */}
          <Route
            path="reportes"
            element={<Reportes />}
          />

          {/* Cobranzas */}
          <Route
            path="cobranzas"
            element={<Cobranzas />}
          />

          {/* Notificaciones */}
          <Route path="notificaciones" element={<Notificaciones />} />

          {/* Comunicaciones (Unificado WhatsApp y Email) */}
          <Route path="comunicaciones" element={<ComunicacionesPage />} />
          {/* Conversaciones WhatsApp (Legacy - mantener por compatibilidad) */}
          <Route path="conversaciones-whatsapp" element={<ConversacionesWhatsAppPage />} />

          {/* Herramientas: Plantillas (solo admin) */}
          <Route
            path="herramientas/plantillas"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Plantillas />
              </SimpleProtectedRoute>
            }
          />

          {/* Scheduler */}
          <Route
            path="scheduler"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Programador />
              </SimpleProtectedRoute>
            }
          />

          {/* Configuración */}
          <Route
            path="configuracion"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Configuracion />
              </SimpleProtectedRoute>
            }
          />

          {/* Analistas */}
          <Route
            path="analistas"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Analistas />
              </SimpleProtectedRoute>
            }
          />

          {/* Validadores */}
          <Route
            path="validadores"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Validadores />
              </SimpleProtectedRoute>
            }
          />

          {/* Analistas (ruta alternativa - redirige a /analistas) */}
          <Route
            path="analistaes"
            element={<Navigate to="/analistas" replace />}
          />

          {/* Concesionarios */}
          <Route
            path="concesionarios"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Concesionarios />
              </SimpleProtectedRoute>
            }
          />

          {/* Modelos de Vehículos */}
          <Route
            path="modelos-vehiculos"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <ModelosVehiculos />
              </SimpleProtectedRoute>
            }
          />

          {/* Auditoría */}
          <Route
            path="auditoria"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Auditoria />
              </SimpleProtectedRoute>
            }
          />

          {/* Chat AI */}
          <Route
            path="chat-ai"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <ChatAI />
              </SimpleProtectedRoute>
            }
          />

          {/* Usuarios */}
          <Route
            path="usuarios"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Usuarios />
              </SimpleProtectedRoute>
            }
          />

          {/* Solicitudes */}
          <Route
            path="solicitudes"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Solicitudes />
              </SimpleProtectedRoute>
            }
          />

          {/* Ventas */}
          <Route path="ventas" element={<Ventas />} />

          {/* CRM */}
          <Route path="crm/embudo-clientes" element={<EmbudoClientes />} />
          <Route path="crm/tickets" element={<TicketsAtencion />} />
          <Route path="crm/embudo-concesionarios" element={<EmbudoConcesionarios />} />

          {/* 404 para rutas no encontradas */}
          <Route path="*" element={<NotFound />} />
        </Route>

      </Routes>
      </Suspense>
    </AnimatePresence>
  )
}

export default App
