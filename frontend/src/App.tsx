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
const Login = lazy(() => import('@/pages/Login').then(module => ({ default: module.Login })))
const Dashboard = lazy(() => import('@/pages/Dashboard').then(module => ({ default: module.Dashboard })))
const Clientes = lazy(() => import('@/pages/Clientes').then(module => ({ default: module.Clientes })))
const Prestamos = lazy(() => import('@/pages/Prestamos').then(module => ({ default: module.Prestamos })))
const Pagos = lazy(() => import('@/pages/Pagos').then(module => ({ default: module.Pagos })))
const NuevoPago = lazy(() => import('@/pages/NuevoPago').then(module => ({ default: module.NuevoPago })))
const ConciliacionBancaria = lazy(() => import('@/pages/ConciliacionBancaria').then(module => ({ default: module.ConciliacionBancaria })))
const Amortizacion = lazy(() => import('@/pages/Amortizacion').then(module => ({ default: module.Amortizacion })))
const Reportes = lazy(() => import('@/pages/Reportes').then(module => ({ default: module.Reportes })))
const Aprobaciones = lazy(() => import('@/pages/Aprobaciones').then(module => ({ default: module.Aprobaciones })))
const Auditoria = lazy(() => import('@/pages/Auditoria').then(module => ({ default: module.Auditoria })))
const Notificaciones = lazy(() => import('@/pages/Notificaciones').then(module => ({ default: module.Notificaciones })))
const Programador = lazy(() => import('@/pages/Programador').then(module => ({ default: module.Programador })))
const Configuracion = lazy(() => import('@/pages/Configuracion').then(module => ({ default: module.Configuracion })))
const PrestamosPage = lazy(() => import('@/pages/PrestamosPage').then(module => ({ default: module.PrestamosPage })))
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
        {/* Ruta de login */}
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
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
          {/* Dashboard */}
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />

          {/* Clientes */}
          <Route path="clientes" element={<Clientes />} />
          <Route path="clientes/nuevo" element={<Clientes />} />
          <Route path="clientes/:id" element={<Clientes />} />

          {/* Préstamos */}
          <Route
            path="prestamos"
            element={<PrestamosPage />}
          />

          {/* Pagos */}
          <Route path="pagos" element={<Pagos />} />
          <Route path="pagos/nuevo" element={<NuevoPago />} />
          <Route path="pagos/conciliacion" element={<ConciliacionBancaria />} />
          <Route path="pagos/:id" element={<Pagos />} />
          <Route path="pagos/:id/editar" element={<NuevoPago />} />

          {/* Amortización */}
          <Route path="amortizacion" element={<AmortizacionPage />} />

          {/* Conciliación */}

          {/* Reportes */}
          <Route
            path="reportes"
            element={<ReportesPage />}
          />


          {/* Aprobaciones */}
          <Route
            path="aprobaciones"
            element={<Aprobaciones />}
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

          {/* Notificaciones */}
          <Route path="notificaciones" element={<Notificaciones />} />

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

          {/* Asesores */}
          <Route
            path="analistaes"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Analistas />
              </SimpleProtectedRoute>
            }
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

        {/* Redirect root to dashboard if authenticated, login if not */}
        <Route
          path="/"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
      </Suspense>
    </AnimatePresence>
  )
}

export default App
