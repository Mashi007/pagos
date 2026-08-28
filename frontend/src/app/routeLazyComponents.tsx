/**
 * Rutas cargadas bajo demanda (code-splitting) para reducir JS inicial.
 * Login y pÃ¡ginas mÃ­nimas del shell siguen import estÃ¡tico en App.tsx.
 */
import { lazy } from 'react'

import { lazyWithRetry } from './lazyWithRetry'

export const PublicBasenameIndexPage = lazy(() =>
  import('../pages/PublicBasenameIndexPage').then(m => ({
    default: m.PublicBasenameIndexPage,
  }))
)

export const ReportePagoPage = lazy(() => import('../pages/ReportePagoPage'))

export const EstadoCuentaPublicoPage = lazy(
  () => import('../pages/EstadoCuentaPublicoPage')
)

export const AccesoLimitadoPage = lazy(
  () => import('../pages/AccesoLimitadoPage')
)

export const DashboardMenu = lazyWithRetry(
  () => import('../pages/DashboardMenu'),
  'dashboard-menu'
)

export const Clientes = lazy(() => import('../pages/Clientes'))

export const Prestamos = lazy(() => import('../pages/Prestamos'))

export const FiniquitoGestionGatePage = lazy(() =>
  import('../pages/FiniquitoGestionGatePage').then(m => ({
    default: m.FiniquitoGestionGatePage,
  }))
)

export const PagosPage = lazy(() => import('../pages/PagosPage'))

export const PagoBsPage = lazy(() => import('../pages/PagoBsPage'))

export const TasaCambioPage = lazy(() => import('../pages/TasaCambioPage'))

export const InfopagosPage = lazy(() => import('../pages/InfopagosPage'))

export const EscanerInfopagosPage = lazyWithRetry(
  () => import('../pages/EscanerInfopagosPage'),
  'escaner-infopagos'
)

export const EscanerInfopagosLotePage = lazyWithRetry(
  () => import('../pages/EscanerInfopagosLotePage'),
  'escaner-infopagos-lote'
)

export const CobrosPagosReportadosPage = lazy(
  () => import('../pages/CobrosPagosReportadosPage')
)

export const CobrosEditarPage = lazy(() => import('../pages/CobrosEditarPage'))

export const CobrosDetallePage = lazy(
  () => import('../pages/CobrosDetallePage')
)

export const CobrosHistoricoPage = lazy(
  () => import('../pages/CobrosHistoricoPage')
)

export const CobranzasPage = lazy(() => import('../pages/CobranzasPage'))

export const CobranzasGestoresPage = lazy(
  () => import('../pages/CobranzasGestoresPage')
)

export const RevisionManual = lazy(() => import('../pages/RevisionManual'))

export const EditarRevisionManual = lazy(
  () => import('../pages/EditarRevisionManual')
)

export const Auditoria = lazy(() => import('../pages/Auditoria'))

export const ConciliacionBancosPage = lazy(
  () => import('../pages/ConciliacionBancosPage')
)

export const ImportacionExtractoPage = lazy(
  () => import('../pages/ImportacionExtractoPage')
)

export const ConciliacionFiniquitosPage = lazy(
  () => import('../pages/ConciliacionFiniquitosPage')
)

export const Notificaciones = lazy(() => import('../pages/Notificaciones'))

export const NotificacionesClientesDrive = lazy(
  () => import('../pages/NotificacionesClientesDrive')
)

export const NotificacionesRecibosPage = lazy(
  () => import('../pages/NotificacionesRecibosPage')
)

export const NotificacionesEvidenciasPage = lazy(
  () => import('../pages/NotificacionesEvidenciasPage')
)

export const Reportes = lazy(() => import('../pages/Reportes'))

export const ActualizacionesPrestamosDrivePage = lazy(
  () => import('../pages/ActualizacionesPrestamosDrivePage')
)

export const Programador = lazy(() => import('../pages/Programador'))

export const Configuracion = lazy(() => import('../pages/Configuracion'))

export const Analistas = lazy(() => import('../pages/Analistas'))

export const Validadores = lazy(() => import('../pages/Validadores'))

export const Concesionarios = lazy(() => import('../pages/Concesionarios'))

export const ModelosVehiculos = lazy(() => import('../pages/ModelosVehiculos'))

export const ChatAI = lazy(() => import('../pages/ChatAI'))

export const Usuarios = lazy(() => import('../pages/Usuarios'))

export const AdminTasaCambioPage = lazy(() =>
  import('../pages/AdminTasaCambioPage').then(m => ({
    default: m.AdminTasaCambioPage,
  }))
)

