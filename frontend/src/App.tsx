import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

// Layout
import { Layout } from '@/components/layout/Layout'

// Auth
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { useAuth } from '@/store/authStore'
import { useAuthPersistence } from '@/hooks/useAuthPersistence'

// Pages
import { Login } from '@/pages/Login'
import { Dashboard } from '@/pages/Dashboard'
import { Clientes } from '@/pages/Clientes'
import { Prestamos } from '@/pages/Prestamos'
import { Pagos } from '@/pages/Pagos'
import { Amortizacion } from '@/pages/Amortizacion'
import { Conciliacion } from '@/pages/Conciliacion'
import { Reportes } from '@/pages/Reportes'
import { Aprobaciones } from '@/pages/Aprobaciones'
import { Auditoria } from '@/pages/Auditoria'
import { Notificaciones } from '@/pages/Notificaciones'
import { Programador } from '@/pages/Programador'
import { Configuracion } from '@/pages/Configuracion'
import { CargaMasiva } from '@/pages/CargaMasiva'
import { VisualizacionBD } from '@/pages/VisualizacionBD'

// Todas las páginas ahora están importadas desde archivos reales

const NotFound = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center">
      <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
      <h2 className="text-2xl font-semibold text-gray-700 mb-2">
        Página no encontrada
      </h2>
      <p className="text-gray-500 mb-6">
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

function App() {
  const { isAuthenticated } = useAuth()
  
  // Hook para manejar la persistencia de autenticación
  const { isInitialized } = useAuthPersistence()

  // Mostrar loading screen mientras se inicializa la autenticación
  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/5 to-accent/5">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Cargando...</p>
        </div>
      </div>
    )
  }

  return (
    <AnimatePresence mode="wait">
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
                transition={{ duration: 0.3 }}
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
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          {/* Dashboard */}
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />

          {/* Clientes */}
          <Route path="clientes" element={<Clientes />} />
          <Route path="clientes/nuevo" element={<Clientes />} />
          <Route path="clientes/:id" element={<Clientes />} />

          {/* Carga Masiva */}
          <Route
            path="carga-masiva"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE']}>
                <CargaMasiva />
              </ProtectedRoute>
            }
          />

          {/* Préstamos */}
          <Route
            path="prestamos"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'ASESOR_COMERCIAL']}>
                <Prestamos />
              </ProtectedRoute>
            }
          />

          {/* Pagos */}
          <Route path="pagos" element={<Pagos />} />
          <Route path="pagos/nuevo" element={<Pagos />} />

          {/* Amortización */}
          <Route path="amortizacion" element={<Amortizacion />} />

          {/* Conciliación */}
          <Route
            path="conciliacion"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'CONTADOR']}>
                <Conciliacion />
              </ProtectedRoute>
            }
          />

          {/* Reportes */}
          <Route
            path="reportes"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'DIRECTOR', 'CONTADOR', 'AUDITOR']}>
                <Reportes />
              </ProtectedRoute>
            }
          />


          {/* Aprobaciones */}
          <Route
            path="aprobaciones"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'ASESOR_COMERCIAL']}>
                <Aprobaciones />
              </ProtectedRoute>
            }
          />

          {/* Auditoría */}
          <Route
            path="auditoria"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'AUDITOR']}>
                <Auditoria />
              </ProtectedRoute>
            }
          />

          {/* Notificaciones */}
          <Route path="notificaciones" element={<Notificaciones />} />

          {/* Scheduler */}
          <Route
            path="scheduler"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE']}>
                <Programador />
              </ProtectedRoute>
            }
          />

          {/* Configuración */}
          <Route
            path="configuracion"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE']}>
                <Configuracion />
              </ProtectedRoute>
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
    </AnimatePresence>
  )
}

export default App
