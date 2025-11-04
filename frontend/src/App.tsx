import { useEffect, useState, lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

// Layout
import { Layout } from '@/components/layout/Layout'

// Auth
import { SimpleProtectedRoute } from '@/components/auth/SimpleProtectedRoute'
import { useSimpleAuth } from '@/store/simpleAuthStore'


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

// Pages - Lazy loading para optimización
const Welcome = lazy(() => import('@/pages/Welcome').then(module => ({ default: module.Welcome })))
const Login = lazy(() => import('@/pages/Login').then(module => ({ default: module.Login })))
// Componente Dashboard antiguo eliminado - Usar DashboardMenu en su lugar
const DashboardMenu = lazy(() => import('@/pages/DashboardMenu').then(module => ({ default: module.DashboardMenu })))
const Clientes = lazy(() => import('@/pages/Clientes').then(module => ({ default: module.Clientes })))
const Prestamos = lazy(() => import('@/pages/Prestamos').then(module => ({ default: module.Prestamos })))
const Amortizacion = lazy(() => import('@/pages/Amortizacion').then(module => ({ default: module.Amortizacion })))
const Reportes = lazy(() => import('@/pages/Reportes').then(module => ({ default: module.Reportes })))
// const Aprobaciones = lazy(() => import('@/pages/Aprobaciones').then(module => ({ default: module.Aprobaciones })))  // MODULO APROBACIONES DESHABILITADO
const Cobranzas = lazy(() => import('@/pages/Cobranzas').then(module => ({ default: module.Cobranzas })))
const Auditoria = lazy(() => import('@/pages/Auditoria').then(module => ({ default: module.Auditoria })))
const Notificaciones = lazy(() => import('@/pages/Notificaciones').then(module => ({ default: module.Notificaciones })))
const Programador = lazy(() => import('@/pages/Programador').then(module => ({ default: module.Programador })))
const Plantillas = lazy(() => import('@/pages/Plantillas').then(module => ({ default: module.Plantillas })))
const Configuracion = lazy(() => import('@/pages/Configuracion').then(module => ({ default: module.Configuracion })))
const Analistas = lazy(() => import('@/pages/Analistas').then(module => ({ default: module.Analistas })))
const PagosPage = lazy(() => import('@/pages/PagosPage').then(module => ({ default: module.PagosPage })))
const AmortizacionPage = lazy(() => import('@/pages/AmortizacionPage').then(module => ({ default: module.AmortizacionPage })))
const ReportesPage = lazy(() => import('@/pages/ReportesPage').then(module => ({ default: module.ReportesPage })))
const VisualizacionBD = lazy(() => import('@/pages/VisualizacionBD').then(module => ({ default: module.VisualizacionBD })))
const Validadores = lazy(() => import('@/pages/Validadores').then(module => ({ default: module.Validadores })))
const Concesionarios = lazy(() => import('@/pages/Concesionarios').then(module => ({ default: module.Concesionarios })))
const ModelosVehiculos = lazy(() => import('@/pages/ModelosVehiculos').then(module => ({ default: module.ModelosVehiculos })))
const Usuarios = lazy(() => import('@/pages/Usuarios').then(module => ({ default: module.Usuarios })))
const Solicitudes = lazy(() => import('@/pages/Solicitudes').then(module => ({ default: module.Solicitudes })))

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
  const { isAuthenticated, initializeAuth } = useSimpleAuth()

  useEffect(() => {
    // Inicializar autenticación desde almacenamiento seguro CON VERIFICACIÓN AUTOMÁTICA
    initializeAuth()
  }, [initializeAuth])

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
          <Route path="dashboard" element={<DashboardMenu />} />
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

          {/* MODULO APROBACIONES DESHABILITADO */}
          {/* <Route
            path="aprobaciones"
            element={<Aprobaciones />}
          /> */}

          {/* Notificaciones */}
          <Route path="notificaciones" element={<Notificaciones />} />

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

          {/* 404 para rutas no encontradas */}
          <Route path="*" element={<NotFound />} />
        </Route>

      </Routes>
      </Suspense>
    </AnimatePresence>
  )
}

export default App
