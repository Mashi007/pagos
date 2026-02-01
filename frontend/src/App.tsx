import { useEffect, useState, lazy, Suspense } from 'react'
import { Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

// Layout
import { Layout } from './components/layout/Layout'

// Auth
import { SimpleProtectedRoute } from './components/auth/SimpleProtectedRoute'
import { useSimpleAuth } from './store/simpleAuthStore'

/** En rutas públicas (/, /login) solo muestra el Outlet. En el resto muestra Layout con Outlet para que el dashboard y demás carguen. */
function RootLayoutWrapper() {
  const location = useLocation()
  const { isAuthenticated } = useSimpleAuth()
  const isPublic = location.pathname === '/' || location.pathname === '/login'
  if (isPublic) return <Outlet />
  return (
    <SimpleProtectedRoute>
      <Layout />
    </SimpleProtectedRoute>
  )
}

// Helper: ante fallo de carga de chunk (404 tras deploy), recargar página para obtener assets actualizados.
// Tipado explícito para evitar TS2322: ComponentType<never> no asignable a ComponentType<unknown>.
function lazyWithRetry(
  factory: () => Promise<{ default: React.ComponentType<unknown> }>
): React.LazyExoticComponent<React.ComponentType<unknown>> {
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
        return new Promise<{ default: React.ComponentType<unknown> }>(() => {}) // no resolver para no renderizar estado roto
      }
      throw err
    })
  ) as React.LazyExoticComponent<React.ComponentType<unknown>>
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

// Pages - Welcome y Login siguen lazy (pantallas pre-auth). Resto import directo para evitar 404 de chunks en Render.
// Aserción de tipo para evitar ComponentType<never> en build estricto (Render).
const Welcome = lazyWithRetry(() =>
  import('./pages/Welcome').then(m => ({ default: m.Welcome as React.ComponentType<unknown> }))
)
const Login = lazyWithRetry(() =>
  import('./pages/Login').then(m => ({ default: m.Login as React.ComponentType<unknown> }))
)
import DashboardMenu from './pages/DashboardMenu'
import Configuracion from './pages/Configuracion'
import Plantillas from './pages/Plantillas'
import Programador from './pages/Programador'
import Clientes from './pages/Clientes'
import Prestamos from './pages/Prestamos'
import Amortizacion from './pages/Amortizacion'
import Reportes from './pages/Reportes'
import Cobranzas from './pages/Cobranzas'
import Auditoria from './pages/Auditoria'
import ChatAI from './pages/ChatAI'
import Notificaciones from './pages/Notificaciones'
import Analistas from './pages/Analistas'
import PagosPage from './pages/PagosPage'
import AmortizacionPage from './pages/AmortizacionPage'
import ReportesPage from './pages/ReportesPage'
import VisualizacionBD from './pages/VisualizacionBD'
import Validadores from './pages/Validadores'
import Concesionarios from './pages/Concesionarios'
import ModelosVehiculos from './pages/ModelosVehiculos'
import Usuarios from './pages/Usuarios'
import Solicitudes from './pages/Solicitudes'
import EmbudoClientes from './pages/EmbudoClientes'
import TicketsAtencion from './pages/TicketsAtencion'
import EmbudoConcesionarios from './pages/EmbudoConcesionarios'
import Ventas from './pages/Ventas'
import ConversacionesWhatsAppPage from './pages/ConversacionesWhatsApp'
import ComunicacionesPage from './pages/Comunicaciones'

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
        {/* Una sola raíz path="/" para que Layout reciba correctamente las rutas hijas (dashboard, clientes, etc.) */}
        <Route path="/" element={<RootLayoutWrapper />}>
          {/* Página de bienvenida (index) */}
          <Route
            index
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

          {/* Login */}
          <Route
            path="login"
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

          {/* Dashboard - ruta más específica primero */}
          <Route path="dashboard/menu" element={<DashboardMenu />} />
          <Route path="dashboard" element={<Navigate to="/dashboard/menu" replace />} />

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
