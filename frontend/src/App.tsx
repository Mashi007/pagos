import React, { useEffect, Suspense } from 'react'

import { Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom'

import { motion, AnimatePresence } from 'framer-motion'

// Layout

import { Layout } from './components/layout/Layout'

// Auth

import { SimpleProtectedRoute } from './components/auth/SimpleProtectedRoute'

import { useSimpleAuth } from './store/simpleAuthStore'

import { getFiniquitoAccessToken } from './services/finiquitoService'

import { BASE_PATH, STAFF_LOGIN_SEARCH } from './config/env'

import { RUTAS_REPORTE_PAGO_PUBLICO } from './constants/rutasIngresoPago'

import { isAdminRole, isManagerRole, isOperatorRole } from './utils/rol'
import {
  defaultHomePathForRol,
  isDelegatedPathForRol,
} from './config/roleRoutes'

/**
 * Acceso publico SIN login de personal: estas URLs siguen abiertas (formulario cobros, etc.).
 * No se impide entrar a /rapicredit-cobros ni a rapicredit-estadocuenta por URL directa.
 *
 * La raiz pathname '/' (URL real: /pagos o /pagos/) muestra solo enlaces de cliente; el acceso
 * de personal usa la ruta dedicada /acceso-personal (redirige a /login?personal=1).
 *
 * Un usuario en rapicredit-cobros no puede abrir dashboard, clientes, etc. sin autenticarse.
 */
const PUBLIC_PATHS = [
  '/',
  '/login',
  '/acceso-personal',
  '/acceso-limitado',
  ...RUTAS_REPORTE_PAGO_PUBLICO,
  '/rapicredit-estadocuenta',
]

/**
 * En rutas publicas solo muestra el Outlet (sin Layout). En el resto, si no hay token activo, redirige a /login
 * para pedir usuario y clave.
 *
 * Con basename="/pagos", useLocation().pathname ya viene sin el basename del host (p. ej. /pagos/pago-bs
 * para la URL real /pagos/pagos/pago-bs). No quitar BASE_PATH de ese valor para RBAC.
 * Solo normalizamos quitando BASE_PATH duplicado para detectar rutas públicas legacy.
 */

function RootLayoutWrapper() {
  const location = useLocation()

  const { isAuthenticated, isLoading, user } = useSimpleAuth()

  const pathnameFromRouter = (location.pathname || '').replace(/\/$/, '') || '/'

  let pathnameForPublic = pathnameFromRouter

  if (BASE_PATH && pathnameForPublic.startsWith(BASE_PATH)) {
    const rest = pathnameForPublic.slice(BASE_PATH.length)
    if (rest !== '' && rest !== '/') pathnameForPublic = rest
  }

  const isPublic = PUBLIC_PATHS.some(p => pathnameForPublic === p)

  if (isPublic) return <Outlet />

  // Si no está autenticado y NO está en una ruta pública:
  // enviar al login de personal para mostrar el formulario directamente.

  if (!isLoading && !isAuthenticated) {
    return (
      <Navigate
        to={`/login${STAFF_LOGIN_SEARCH}`}
        state={{ from: location }}
        replace
      />
    )
  }

  // Lista blanca por rol (admin: sin filtro). Fuera de rutas delegadas → inicio del rol.
  if (
    !isLoading &&
    isAuthenticated &&
    user &&
    !isAdminRole(user.rol) &&
    !isDelegatedPathForRol(user.rol, pathnameFromRouter)
  ) {
    return <Navigate to={defaultHomePathForRol(user.rol)} replace />
  }

  const esGestionFiniquito = pathnameFromRouter === '/finiquitos/gestion'

  const tokenPortalFiniquito = getFiniquitoAccessToken()?.trim()

  const esAdminPanel = isAuthenticated && isAdminRole(user?.rol)

  const esOperatorPanel = isAuthenticated && isOperatorRole(user?.rol)

  const esManagerPanel = isAuthenticated && isManagerRole(user?.rol)

  const esPanelGestionFiniquitoInterno =
    esAdminPanel || esOperatorPanel || esManagerPanel

  if (esGestionFiniquito && !esPanelGestionFiniquitoInterno) {
    if (tokenPortalFiniquito) {
      return <Outlet />
    }

    if (isLoading) {
      return (
        <div className="flex min-h-[100dvh] items-center justify-center bg-slate-100/80">
          <div
            className="h-10 w-10 animate-spin rounded-full border-2 border-slate-400 border-t-transparent"
            aria-label="Cargando"
            role="status"
          />
        </div>
      )
    }

    return <Navigate to="/finiquitos/acceso" replace />
  }

  return (
    <SimpleProtectedRoute>
      <Layout />
    </SimpleProtectedRoute>
  )
}

// Constantes de configuracin

const ANIMATION_DURATION = 0.3

// Login import estático (envuelto en motion.div aquí); el resto de páginas en chunks lazy para menos JS inicial.

import { Login } from './pages/Login'

import {
  AccesoLimitadoPage,
  ActualizacionesPrestamosDrivePage,
  AdminTasaCambioPage,
  AmortizacionPage,
  Analistas,
  Auditoria,
  ChatAI,
  Clientes,
  CobrosDetallePage,
  CobrosEditarPage,
  CobrosHistoricoPage,
  CobrosPagosReportadosPage,
  ComunicacionesPage,
  Configuracion,
  Concesionarios,
  ConversacionesWhatsAppPage,
  DashboardMenu,
  EditarRevisionManual,
  EmbudoClientes,
  EmbudoConcesionarios,
  EstadoCuentaPublicoPage,
  FiniquitoAccesoPage,
  FiniquitoGestionGatePage,
  FiniquitoRootPage,
  InfopagosPage,
  EscanerInfopagosPage,
  EscanerInfopagosLotePage,
  FechaQAuditoriaTotalPage,
  CuotasVsFechaBaseAdminPage,
  ModelosVehiculos,
  Notificaciones,
  NotificacionesClientesDrive,
  NotificacionesRecibosPage,
  PagoBsPage,
  PagosPage,
  Prestamos,
  Programador,
  PublicBasenameIndexPage,
  ReportePagoPage,
  Reportes,
  RevisionManual,
  Solicitudes,
  TasaCambioPage,
  Usuarios,
  Validadores,
} from './app/routeLazyComponents'

const NotFound = () => (
  <div className="flex min-h-screen items-center justify-center">
    <div className="text-center">
      <h1 className="mb-4 text-6xl font-bold text-gray-300">404</h1>

      <h2 className="mb-4 text-2xl font-semibold text-gray-700">
        Página no encontrada
      </h2>

      <p className="mb-6 text-gray-500">
        La página que buscas no existe o ha sido movida.
      </p>

      <button
        onClick={() => window.history.back()}
        className="rounded-lg bg-primary px-6 py-2 text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Volver atrás
      </button>
    </div>
  </div>
)

// Componente de loading para Suspense

const PageLoader = () => (
  <div className="flex min-h-screen items-center justify-center">
    <div className="text-center">
      <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600"></div>

      <p className="text-gray-600">Cargando página...</p>
    </div>
  </div>
)

// Una sola ejecucin de init auth por sesin (evita doble llamada en StrictMode

// y reduce "demasiadas llamadas a location/history" ? "The operation is insecure")

let _authInitDone = false

function App() {
  const location = useLocation()

  const { isAuthenticated, isLoading, initializeAuth, user } = useSimpleAuth()
  const loginSearch = new URLSearchParams(location.search || '')
  const staffLoginIntent =
    loginSearch.get('personal') === '1' || loginSearch.get('staff') === '1'

  useEffect(() => {
    if (_authInitDone) return

    _authInitDone = true

    initializeAuth()
  }, [initializeAuth])

  // Mostrar loader solo si est cargando Y hay datos de auth (para evitar flash)

  let pathname = (location.pathname || '').replace(/\/$/, '') || '/'

  if (BASE_PATH && pathname.startsWith(BASE_PATH)) {
    const r = pathname.slice(BASE_PATH.length)
    pathname = r === '' ? '/' : r
  }

  const isPublicPath = PUBLIC_PATHS.some((p: string) => pathname === p)

  const colaboradorFiniquitoEnGestion =
    pathname === '/finiquitos/gestion' && !!getFiniquitoAccessToken()?.trim()

  if (isLoading && !isPublicPath && !colaboradorFiniquitoEnGestion) {
    return <PageLoader />
  }

  return (
    <AnimatePresence mode="wait">
      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Una sola raz path="/" para que Layout reciba correctamente las rutas hijas (dashboard, clientes, etc.) */}

          <Route path="/" element={<RootLayoutWrapper />}>
            {/* Raíz /pagos: clientes eligen servicio público; personal usa /login?personal=1 */}

            <Route
              index
              element={
                isAuthenticated ? (
                  <Navigate to={defaultHomePathForRol(user?.rol)} replace />
                ) : (
                  <PublicBasenameIndexPage />
                )
              }
            />

            {/* Formulario publico de reporte de pago (sin login). Link canonico: /rapicredit-cobros */}

            <Route path="rapicredit-cobros" element={<ReportePagoPage />} />

            {/* Alias públicos legacy/amigables para evitar caída a login por rutas antiguas. */}
            <Route
              path="reportar"
              element={<Navigate to="/rapicredit-cobros" replace />}
            />
            <Route
              path="reportar-pago"
              element={<Navigate to="/rapicredit-cobros" replace />}
            />

            {/* Consulta publica de estado de cuenta (sin login). Solo esta consulta, sin acceso a otros servicios. */}

            <Route
              path="rapicredit-estadocuenta"
              element={<EstadoCuentaPublicoPage />}
            />
            <Route
              path="estado-cuenta"
              element={<Navigate to="/rapicredit-estadocuenta" replace />}
            />
            <Route
              path="estado-de-cuenta"
              element={<Navigate to="/rapicredit-estadocuenta" replace />}
            />

            {/* Acceso limitado: ruta pública (p. ej. historial); "Volver a Infopagos" exige login y redirige con state.from */}

            <Route path="acceso-limitado" element={<AccesoLimitadoPage />} />

            {/* Entrada dedicada para personal (evita confusion con /login solo). */}
            <Route
              path="acceso-personal"
              element={
                isAuthenticated ? (
                  <Navigate to={defaultHomePathForRol(user?.rol)} replace />
                ) : (
                  <Navigate to={`/login${STAFF_LOGIN_SEARCH}`} replace />
                )
              }
            />

            {/* Finiquito: portal OTP y gestion comparten URL /finiquitos/gestion (gate); panel redirige */}

            {/* Nota: Rutas de finiquitos han sido movidas a sección protegida (después de login) */}

            {/* Login: misma pantalla que index cuando no autenticado */}

            <Route
              path="login"
              element={
                isAuthenticated ? (
                  <Navigate to={defaultHomePathForRol(user?.rol)} replace />
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

            {/* Dashboard - ruta ms especfica primero */}

            <Route path="dashboard/menu" element={<DashboardMenu />} />

            <Route
              path="dashboard"
              element={<Navigate to="/dashboard/menu" replace />}
            />

            {/* Clientes */}

            <Route path="clientes" element={<Clientes />} />

            <Route path="clientes/nuevo" element={<Clientes />} />

            <Route path="clientes/:id" element={<Clientes />} />

            {/* Prstamos */}

            <Route path="prestamos" element={<Prestamos />} />

            {/* Finiquitos: DEBE IR ANTES de /pagos para no ser capturado por <Route path="pagos"> */}

            <Route path="finiquitos" element={<FiniquitoRootPage />} />

            <Route path="finiquitos/acceso" element={<FiniquitoAccesoPage />} />

            <Route
              path="finiquitos/panel"
              element={<Navigate to="/finiquitos/gestion" replace />}
            />

            <Route
              path="finiquitos/gestion"
              element={<FiniquitoGestionGatePage />}
            />

            {/* Pagos (URL: /pagos/pagos con basename /pagos) */}

            <Route path="pagos">
              <Route index element={<PagosPage />} />

              <Route path="pago-bs" element={<PagoBsPage />} />

              <Route path=":id" element={<PagosPage />} />
            </Route>

            <Route
              path="tasa-cambio"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <TasaCambioPage />
                </SimpleProtectedRoute>
              }
            />

            {/* Infopagos: dentro del layout con sidebar (requiere login) */}

            <Route path="infopagos" element={<InfopagosPage />} />

            <Route path="escaner" element={<EscanerInfopagosPage />} />

            <Route
              path="escaner-lote"
              element={
                <SimpleProtectedRoute>
                  <EscanerInfopagosLotePage />
                </SimpleProtectedRoute>
              }
            />

            {/* Amortizacin */}

            <Route path="amortizacion" element={<AmortizacionPage />} />

            {/* Conciliacin */}

            {/* Cobros (Pagos Reportados, Detalle, Histrico) */}

            <Route
              path="cobros/pagos-reportados"
              element={<CobrosPagosReportadosPage />}
            />

            <Route
              path="cobros/pagos-reportados/:id/editar"
              element={<CobrosEditarPage />}
            />

            <Route
              path="cobros/pagos-reportados/:id"
              element={<CobrosDetallePage />}
            />

            <Route
              path="cobros/historico-cliente"
              element={<CobrosHistoricoPage />}
            />

            {/* Reportes */}

            <Route path="reportes" element={<Reportes />} />

            {/* Revisin Manual de Prstamos */}

            <Route path="revision-manual" element={<RevisionManual />} />

            <Route
              path="revision-manual/editar/:prestamoId"
              element={<EditarRevisionManual />}
            />

            <Route path="auditoria" element={<Auditoria />} />

            {/* Notificaciones (dentro de CRM en sidebar) */}

            <Route
              path="notificaciones"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <Notificaciones modulo="a1dia" />
                </SimpleProtectedRoute>
              }
            />

            <Route
              path="notificaciones/a-3-cuotas"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <Notificaciones modulo="a3cuotas" />
                </SimpleProtectedRoute>
              }
            />

            <Route
              path="notificaciones/d-2-antes"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <Notificaciones modulo="d2antes" />
                </SimpleProtectedRoute>
              }
            />

            <Route
              path="notificaciones/atraso-45-dias"
              element={<Navigate to="/notificaciones/atraso-10-dias" replace />}
            />

            <Route
              path="notificaciones/atraso-10-dias"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <Notificaciones modulo="a10dias" />
                </SimpleProtectedRoute>
              }
            />

            <Route
              path="notificaciones/general"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <Notificaciones modulo="general" />
                </SimpleProtectedRoute>
              }
            />

            <Route
              path="notificaciones/fecha"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <FechaQAuditoriaTotalPage />
                </SimpleProtectedRoute>
              }
            />
            <Route
              path="notificaciones/fecha-auditoria-total"
              element={<Navigate to="/notificaciones/fecha" replace />}
            />

            <Route
              path="notificaciones/clientes-drive"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <NotificacionesClientesDrive />
                </SimpleProtectedRoute>
              }
            />

            <Route
              path="notificaciones/recibos"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <NotificacionesRecibosPage />
                </SimpleProtectedRoute>
              }
            />

            <Route
              path="actualizaciones/prestamos"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <ActualizacionesPrestamosDrivePage />
                </SimpleProtectedRoute>
              }
            />

            <Route
              path="actualizaciones/cuotas-fecha-base"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <CuotasVsFechaBaseAdminPage />
                </SimpleProtectedRoute>
              }
            />

            {/* Compatibilidad: «Fechas 2» redirige al módulo Fechas (Q vs BD + panel por día). */}
            <Route
              path="actualizaciones/fechas-2"
              element={<Navigate to="/notificaciones/fecha" replace />}
            />

            {/* Redirect de compatibilidad: la URL anterior d-1-dia era confusa (el módulo es «2 días antes»). */}
            <Route
              path="notificaciones/d-1-dia"
              element={<Navigate to="/notificaciones/d-2-antes" replace />}
            />

            {/* Redirecciones: plantillas viven en Configuracin */}

            <Route
              path="notificaciones/plantillas"
              element={<Navigate to="/configuracion?tab=plantillas" replace />}
            />

            <Route
              path="herramientas/notificaciones"
              element={<Navigate to="/notificaciones" replace />}
            />

            <Route
              path="herramientas/plantillas"
              element={<Navigate to="/configuracion?tab=plantillas" replace />}
            />

            {/* Comunicaciones (Unificado WhatsApp y Email) */}

            <Route path="comunicaciones" element={<ComunicacionesPage />} />

            {/* Conversaciones WhatsApp (Legacy - mantener por compatibilidad) */}

            <Route
              path="conversaciones-whatsapp"
              element={<ConversacionesWhatsAppPage />}
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

            {/* Configuracin */}

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

            {/* Modelos de Vehculos */}

            <Route
              path="modelos-vehiculos"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <ModelosVehiculos />
                </SimpleProtectedRoute>
              }
            />

            {/* Chat AI  accesible por cualquier usuario autenticado (no solo admin) */}

            <Route
              path="chat-ai"
              element={
                <SimpleProtectedRoute>
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

            <Route
              path="administracion/autorizaciones-revision-manual"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <Navigate to="/revision-manual" replace />
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

            {/* Ventas: en pausa - redirige a inicio para no cargar procesos */}

            <Route path="ventas" element={<Navigate to="/pagos" replace />} />

            {/* CRM */}

            <Route path="crm/embudo-clientes" element={<EmbudoClientes />} />

            {/* CRM campañas y tickets: ocultos - redirigen a clientes */}

            <Route
              path="crm/tickets"
              element={<Navigate to="/clientes" replace />}
            />

            <Route
              path="crm/campanas"
              element={<Navigate to="/clientes" replace />}
            />

            <Route
              path="crm/embudo-concesionarios"
              element={<EmbudoConcesionarios />}
            />

            {/* 404 para rutas no encontradas */}

            <Route path="*" element={<NotFound />} />
          </Route>

          <Route path="/admin/tasas-cambio" element={<AdminTasaCambioPage />} />
        </Routes>
      </Suspense>
    </AnimatePresence>
  )
}

export default App
