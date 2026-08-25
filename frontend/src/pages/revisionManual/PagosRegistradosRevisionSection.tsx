import {
  AlertTriangle,
  BarChart3,
  CreditCard,
  DollarSign,
  Edit,
  Eye,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'
import { formatDate } from '../../utils'
import type { Pago } from '../../services/pagoService'
import { ConciliarCarteraPagosProgreso } from '../../components/pagos/ConciliarCarteraPagosProgreso'
import {
  claveDocumentoPagoListaNormalizada,
  textoDocumentoPagoParaListado,
} from '../../utils/pagoExcelValidation'
import {
  abrirStaffComprobanteDesdeHref,
  esUrlComprobanteImagenConAuth,
} from '../../utils/comprobanteImagenAuth'
import {
  DuplicadoCarteraAlertaInline,
  camposDuplicadoDesdePagoRevision,
  esDuplicadoEntrePrestamosDistintos,
} from '../../components/cobros/DuplicadoPrestamosComparacion'
import {
  COHERENCIA_USD_TOL,
  esInstitucionMercantilRevision,
  pagoSerialYaAplicadoEnOtroRegistroCartera,
} from './EditarRevisionManual.helpers'
import type { PagosRegistradosRevisionSectionProps } from './pagosRegistradosRevisionTypes'
import { usePermissions } from '../../hooks/usePermissions'

export function PagosRegistradosRevisionSection(
  props: PagosRegistradosRevisionSectionProps
) {
  const {
    cedulaParaPagosRealizados,
    pagosRegistradosCardRef,
    vieneDesdeFiniquitos,
    prestamoData,
    soloLectura,
    aplicarCascadaPagosMutation,
    abrirAgregarPagoRevision,
    escaneandoComprobanteAgregarPago,
    escaneoLoteProgreso,
    abrirSelectorEscaneoComprobanteAgregarPago,
    reescaneandoCartera,
    reescaneoCarteraProgreso,
    ejecutarReescaneoCartera,
    loadingPagosRealizados,
    fetchingPagosRealizados,
    refetchPagosRealizados,
    isAdmin,
    conciliarTablaUi,
    setConciliarTablaUi,
    idsPagosPrestamoEnTabla,
    contarPagosPrestamoEnTabla,
    limpiarConciliarTablaUi,
    manejarConciliarExito,
    pagosRealizadosData,
    pagosRegistradosOrdenados,
    pagosNoOperativosOrdenados,
    conteoDocumentoPagosRevision,
    alertasReescaneoPorPagoId,
    abrirEditarPagoRevision,
    pagoEstaConciliadoOPagado,
    eliminandoPagoId,
    eliminarPagoRevision,
    pagePagosRegistrados,
    setPagePagosRegistrados,
    hayPendienteRevision,
    auditoriaCoherenciaActiva,
    estadoPrestamoNorm,
    agregadosCuotasRevision,
  } = props

  const { revisionManualFullEdit } = usePermissions()
  /** Escanear comprobante: admin, operador y gerente (no visualizador). */
  const puedeEscanearComprobantes = Boolean(revisionManualFullEdit || isAdmin)
  /** Reescanear cartera: solo administrador. */
  const puedeReescanearCartera = Boolean(isAdmin)

  const tituloReescaneo = soloLectura
    ? 'Revision cerrada: solo lectura'
    : 'Reescanea solo pagos con Conciliación Bancaria = No. Omite Sí/Ambiguo.'

  return (
    <>
      <Card ref={pagosRegistradosCardRef}>
        <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2 space-y-0 pb-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <CreditCard className="h-5 w-5" />
              Pagos registrados en cartera
            </CardTitle>
            {vieneDesdeFiniquitos && isAdmin ? (
              <p className="mt-1 max-w-2xl text-xs text-muted-foreground">
                Desde finiquitos: puede usar{' '}
                <strong className="text-amber-950">Reescanear</strong> (OCR
                sobre comprobantes ya guardados). Al terminar, vuelva a finiquitos
                y pase el caso al área de trabajo.
              </p>
            ) : null}
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="gap-2"
              disabled={
                soloLectura ||
                aplicarCascadaPagosMutation.isPending ||
                !prestamoData.prestamo_id ||
                Number(prestamoData.prestamo_id) <= 0
              }
              onClick={() => aplicarCascadaPagosMutation.mutate()}
              title={
                soloLectura
                  ? 'Revisión cerrada: solo lectura'
                  : 'Reconstruye la amortización y aplica todos los pagos de más viejo a más nuevo (no por orden de reporte).'
              }
            >
              {aplicarCascadaPagosMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <DollarSign className="h-4 w-4" />
              )}
              Aplicar a cuotas (cascada)
            </Button>
            <Button
              type="button"
              variant="default"
              size="sm"
              className="gap-2"
              disabled={soloLectura}
              onClick={abrirAgregarPagoRevision}
              title={
                soloLectura
                  ? 'Revision cerrada: solo lectura'
                  : 'Registrar un pago para esta cedula'
              }
            >
              <Plus className="h-4 w-4" />
              Agregar pago
            </Button>
            {puedeEscanearComprobantes ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-2"
                disabled={soloLectura || escaneandoComprobanteAgregarPago}
                onClick={abrirSelectorEscaneoComprobanteAgregarPago}
                title={
                  soloLectura
                    ? 'Revision cerrada: solo lectura'
                    : 'Elija 1 comprobante (revisar en formulario) o lote (varios, registro automatico)'
                }
              >
                {escaneandoComprobanteAgregarPago ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                {escaneandoComprobanteAgregarPago && escaneoLoteProgreso
                  ? `Escaneando ${escaneoLoteProgreso.hecho}/${escaneoLoteProgreso.total}`
                  : 'Escanear comprobante'}
              </Button>
            ) : null}
            {puedeReescanearCartera ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-2 border-violet-300 bg-violet-50 text-violet-950 hover:bg-violet-100"
                disabled={
                  soloLectura ||
                  reescaneandoCartera ||
                  !prestamoData.prestamo_id ||
                  Number(prestamoData.prestamo_id) <= 0
                }
                onClick={() => void ejecutarReescaneoCartera()}
                title={tituloReescaneo}
              >
                {reescaneandoCartera ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                {reescaneoCarteraProgreso
                  ? reescaneoCarteraProgreso.fase === 'cascada'
                    ? 'Aplicando cascada…'
                    : `Reescaneando ${reescaneoCarteraProgreso.hecho}/${reescaneoCarteraProgreso.total}`
                  : 'Reescanear'}
              </Button>
            ) : null}
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-2"
              disabled={loadingPagosRealizados || fetchingPagosRealizados}
              onClick={() => void refetchPagosRealizados()}
            >
              <RefreshCw
                className={`h-4 w-4 ${fetchingPagosRealizados ? 'animate-spin' : ''}`}
              />
              Actualizar
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {conciliarTablaUi && conciliarTablaUi.fase !== 'listo' ? (
            <ConciliarCarteraPagosProgreso
              fase={conciliarTablaUi.fase}
              prestamoId={Number(prestamoData.prestamo_id)}
              pagosAntes={conciliarTablaUi.pagosAntes}
              idsAnteriores={conciliarTablaUi.idsAnteriores}
              idsRecreados={conciliarTablaUi.idsRecreados}
              ocrOk={conciliarTablaUi.ocrOk}
              ocrTotal={conciliarTablaUi.ocrTotal}
            />
          ) : loadingPagosRealizados && !pagosRealizadosData ? (
            <div className="flex items-center gap-2 py-8 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              Cargando pagos…
            </div>
          ) : !pagosRealizadosData?.pagos?.length ? (
            <div className="space-y-3 py-6">
              <p className="text-sm text-muted-foreground">
                No hay filas en la tabla de pagos para esta cédula todavía.
                Puede registrar el primero con «Agregar pago» o escanear un
                comprobante para llenar el formulario.
              </p>
              {!soloLectura && (
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    className="gap-2"
                    onClick={abrirAgregarPagoRevision}
                  >
                    <Plus className="h-4 w-4" />
                    Agregar pago
                  </Button>
                  {puedeEscanearComprobantes ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="gap-2"
                      disabled={escaneandoComprobanteAgregarPago}
                      onClick={abrirSelectorEscaneoComprobanteAgregarPago}
                    >
                      {escaneandoComprobanteAgregarPago ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Upload className="h-4 w-4" />
                      )}
                      {escaneandoComprobanteAgregarPago && escaneoLoteProgreso
                        ? `Escaneando ${escaneoLoteProgreso.hecho}/${escaneoLoteProgreso.total}`
                        : 'Escanear comprobante'}
                    </Button>
                  ) : null}
                </div>
              )}
            </div>
          ) : (
            <>
              {conciliarTablaUi?.fase === 'listo' ? (
                <div className="mb-3">
                  <ConciliarCarteraPagosProgreso
                    fase="listo"
                    prestamoId={Number(prestamoData.prestamo_id)}
                    pagosAntes={conciliarTablaUi.pagosAntes}
                    idsAnteriores={conciliarTablaUi.idsAnteriores}
                    idsRecreados={conciliarTablaUi.idsRecreados}
                    ocrOk={conciliarTablaUi.ocrOk}
                    ocrTotal={conciliarTablaUi.ocrTotal}
                  />
                </div>
              ) : null}
              {(() => {
                const rp = pagosRealizadosData.resumen_prestamo
                let sumaVisible = 0
                for (const p of pagosRegistradosOrdenados) {
                  const m =
                    typeof p.monto_pagado === 'number'
                      ? p.monto_pagado
                      : parseFloat(String(p.monto_pagado || 0)) || 0
                  sumaVisible += m
                }
                sumaVisible = Math.round(sumaVisible * 100) / 100
                // Una sola cifra: lo que sumas en la tabla = Total = Pagado.
                const totalAlineado = sumaVisible
                const apiTotal =
                  rp?.suma_monto_pagado != null
                    ? Math.round(Number(rp.suma_monto_pagado) * 100) / 100
                    : pagosRealizadosData.sum_monto_pagado_cedula != null
                      ? Math.round(
                          Number(pagosRealizadosData.sum_monto_pagado_cedula) *
                            100
                        ) / 100
                      : null
                const desfaseApi =
                  apiTotal != null &&
                  Math.abs(sumaVisible - apiTotal) > COHERENCIA_USD_TOL
                let sumaNoOper = 0
                for (const p of pagosNoOperativosOrdenados) {
                  const m =
                    typeof p.monto_pagado === 'number'
                      ? p.monto_pagado
                      : parseFloat(String(p.monto_pagado || 0)) || 0
                  sumaNoOper += m
                }
                sumaNoOper = Math.round(sumaNoOper * 100) / 100
                if (
                  pagosRegistradosOrdenados.length === 0 &&
                  apiTotal == null
                ) {
                  return null
                }
                return (
                  <div className="mb-3 space-y-1">
                    <p className="text-sm font-medium text-foreground">
                      Total acumulado (suma de la tabla): $
                      {totalAlineado.toFixed(2)} USD
                      {pagosRegistradosOrdenados.length > 0
                        ? ` · ${pagosRegistradosOrdenados.length} abono${pagosRegistradosOrdenados.length === 1 ? '' : 's'}`
                        : ''}
                    </p>
                    {desfaseApi ? (
                      <p className="text-xs text-red-700">
                        Aviso: suma visible ${sumaVisible.toFixed(2)} ≠ API $
                        {apiTotal!.toFixed(2)} (¿otra página?). Pulse
                        Actualizar datos.
                      </p>
                    ) : null}
                    {sumaNoOper > 0.009 ? (
                      <p className="text-xs text-amber-900">
                        En esta tabla hay ${sumaNoOper.toFixed(2)} USD en{' '}
                        {pagosNoOperativosOrdenados.length} fila(s) con estado
                        anulado/duplicado/rechazado (IDs:{' '}
                        {pagosNoOperativosOrdenados
                          .map(p => `#${p.id}`)
                          .join(', ')}
                        ). Siguen sumando aquí; la cascada no las aplica.
                      </p>
                    ) : null}
                  </div>
                )
              })()}
              <p className="mb-2 text-xs text-muted-foreground">
                Comprobantes y filas de más viejo a más actual. La cascada
                aplica en ese orden.
              </p>
              <div className="overflow-x-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="whitespace-nowrap">ID</TableHead>
                      <TableHead
                        className="whitespace-nowrap"
                        title="Más viejo arriba; la cascada aplica en este mismo orden."
                      >
                        Fecha pago
                      </TableHead>
                      <TableHead className="whitespace-nowrap text-right">
                        Monto USD
                      </TableHead>
                      <TableHead className="whitespace-nowrap">Estado</TableHead>
                      <TableHead className="whitespace-nowrap">Banco</TableHead>
                      <TableHead className="whitespace-nowrap">
                        Nº documento
                      </TableHead>
                      <TableHead
                        className="whitespace-nowrap"
                        title="Confirmacion en Conciliacion Bancos (check verde). No es autoconciliacion OCR/cuotas."
                      >
                        Conciliación Bancaria
                      </TableHead>
                      <TableHead className="min-w-[88px] whitespace-nowrap text-right">
                        Acciones
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pagosRegistradosOrdenados.length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={8}
                          className="py-6 text-center text-sm text-muted-foreground"
                        >
                          No hay pagos registrados para este crédito.
                        </TableCell>
                      </TableRow>
                    ) : null}
                    {pagosRegistradosOrdenados.map((pago: Pago) => {
                      const docKey = claveDocumentoPagoListaNormalizada(
                        pago.numero_documento,
                        pago.codigo_documento ?? null
                      )
                      const documentoDuplicadoEnPagina =
                        !!docKey &&
                        (conteoDocumentoPagosRevision.get(docKey) || 0) > 1
                      const serialDuplicadoCartera =
                        pagoSerialYaAplicadoEnOtroRegistroCartera(pago)
                      const camposDupRevision =
                        camposDuplicadoDesdePagoRevision(pago)
                      const duplicadoEntrePrestamosDistintos =
                        serialDuplicadoCartera &&
                        esDuplicadoEntrePrestamosDistintos(camposDupRevision)
                      const fechaPagoIsoRevision =
                        pago.fecha_pago != null
                          ? String(pago.fecha_pago).slice(0, 10)
                          : null
                      const recienConciliado = (
                        conciliarTablaUi?.idsRecreados ?? []
                      ).includes(Number(pago.id))
                      const alertasReescaneo =
                        alertasReescaneoPorPagoId[Number(pago.id)] ?? []
                      return (
                        <TableRow
                          key={pago.id}
                          className={
                            recienConciliado
                              ? 'animate-in fade-in bg-green-50 ring-1 ring-inset ring-green-200 duration-500'
                              : undefined
                          }
                        >
                          <TableCell className="font-mono text-xs">
                            {pago.id}
                          </TableCell>
                          <TableCell className="whitespace-nowrap">
                            {formatDate(pago.fecha_pago)}
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            $
                            {typeof pago.monto_pagado === 'number'
                              ? pago.monto_pagado.toFixed(2)
                              : parseFloat(
                                  String(pago.monto_pagado || 0)
                                ).toFixed(2)}
                          </TableCell>
                          <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                            {String(pago.estado ?? '—').trim() || '—'}
                          </TableCell>
                          <TableCell className="max-w-[180px] truncate text-sm">
                            {pago.institucion_bancaria?.trim()
                              ? pago.institucion_bancaria
                              : '-'}
                          </TableCell>
                          <TableCell
                            className={`max-w-[240px] font-mono text-xs ${
                              documentoDuplicadoEnPagina ||
                              duplicadoEntrePrestamosDistintos
                                ? 'bg-orange-100 text-orange-950'
                                : ''
                            }`}
                            title={
                              duplicadoEntrePrestamosDistintos
                                ? 'Serial ya aplicado en cartera en otro préstamo.'
                                : documentoDuplicadoEnPagina
                                  ? 'Misma clave comprobante + código aparece más de una vez en esta página.'
                                  : undefined
                            }
                          >
                            <div className="flex min-w-0 items-center gap-1">
                              <span className="min-w-0 truncate">
                                {textoDocumentoPagoParaListado(
                                  pago.numero_documento,
                                  pago.codigo_documento
                                )}
                              </span>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="h-7 w-7 shrink-0 p-0"
                                disabled={
                                  !esUrlComprobanteImagenConAuth(
                                    pago.link_comprobante || ''
                                  )
                                }
                                title={
                                  esUrlComprobanteImagenConAuth(
                                    pago.link_comprobante || ''
                                  )
                                    ? 'Ver comprobante guardado en el sistema'
                                    : pago.link_comprobante?.trim()
                                      ? 'Solo enlace externo; use Editar pago para subir el comprobante al sistema.'
                                      : 'Sin comprobante en el sistema'
                                }
                                aria-label="Ver comprobante del sistema"
                                onClick={() => {
                                  const u = pago.link_comprobante?.trim()
                                  if (u && esUrlComprobanteImagenConAuth(u)) {
                                    void abrirStaffComprobanteDesdeHref(u)
                                  }
                                }}
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                              {alertasReescaneo.length > 0 ? (
                                <span
                                  className="inline-flex shrink-0 text-amber-600"
                                  title={alertasReescaneo.join('\n')}
                                  aria-label="Requiere revision manual tras re-escaneo"
                                >
                                  <AlertTriangle className="h-4 w-4" />
                                </span>
                              ) : null}
                            </div>
                            {serialDuplicadoCartera ? (
                              <div className="mt-1 max-w-[320px] text-sm">
                                <DuplicadoCarteraAlertaInline
                                  {...camposDupRevision}
                                  numeroDocumentoEnCartera={
                                    pago.duplicado_en_cartera_numero_documento
                                  }
                                  fechaPagoReporteIso={fechaPagoIsoRevision}
                                  institucion_financiera={
                                    pago.institucion_bancaria
                                  }
                                  esMercantil={esInstitucionMercantilRevision(
                                    pago.institucion_bancaria
                                  )}
                                  notas={pago.notas}
                                />
                              </div>
                            ) : null}
                          </TableCell>
                          <TableCell className="whitespace-nowrap">
                            {pago.conciliacion_bancaria_ambigua ? (
                              <Badge
                                variant="outline"
                                className="border-orange-600 bg-orange-500 font-semibold text-white hover:bg-orange-600"
                                style={{
                                  backgroundColor: '#f97316',
                                  color: '#fff',
                                }}
                                title="Conciliado desde AMBIGUO en Conciliacion Bancos. Solo eliminar."
                              >
                                Ambiguo
                              </Badge>
                            ) : pago.conciliacion_bancaria_confirmada ? (
                              <Badge
                                className="bg-green-500 text-white"
                                title="Confirmado en Conciliacion Bancos (Ref. Banco o Ref. RapiC)"
                              >
                                Sí
                              </Badge>
                            ) : (
                              <Badge
                                className="bg-gray-500 text-white"
                                title="Sin confirmacion en Conciliacion Bancos"
                              >
                                No
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex flex-wrap items-center justify-end gap-1">
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 shrink-0 p-0"
                                disabled={soloLectura}
                                onClick={() => abrirEditarPagoRevision(pago)}
                                title={
                                  soloLectura
                                    ? 'Revision cerrada: solo lectura'
                                    : pagoEstaConciliadoOPagado(pago) &&
                                        !isAdmin
                                      ? 'Editar pago conciliado (monto, fecha y Nº documento; código/comprobante solo administrador)'
                                      : 'Editar pago'
                                }
                                aria-label="Editar pago"
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 shrink-0 p-0 text-destructive hover:text-destructive"
                                disabled={
                                  soloLectura || eliminandoPagoId === pago.id
                                }
                                onClick={() => void eliminarPagoRevision(pago)}
                                title={
                                  soloLectura
                                    ? 'Revision cerrada: solo lectura'
                                    : 'Eliminar pago'
                                }
                                aria-label="Eliminar pago"
                              >
                                {eliminandoPagoId === pago.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <Trash2 className="h-4 w-4" />
                                )}
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
              {(pagosRealizadosData.total_pages ?? 0) > 1 && (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
                  <span>
                    Página {pagosRealizadosData.page} de{' '}
                    {pagosRealizadosData.total_pages} (
                    {pagosRealizadosData.total} pagos)
                  </span>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={pagePagosRegistrados <= 1}
                      onClick={() =>
                        setPagePagosRegistrados(p => Math.max(1, p - 1))
                      }
                    >
                      Anterior
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={
                        pagePagosRegistrados >=
                        (pagosRealizadosData.total_pages ?? 1)
                      }
                      onClick={() =>
                        setPagePagosRegistrados(p =>
                          Math.min(pagosRealizadosData.total_pages ?? 1, p + 1)
                        )
                      }
                    >
                      Siguiente
                    </Button>
                  </div>
                </div>
              )}
              {pagosNoOperativosOrdenados.length > 0 ? (
                <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50/80 p-3">
                  <p className="mb-2 text-sm font-semibold text-amber-950">
                    Filas con estado anulado/duplicado/rechazado (
                    {pagosNoOperativosOrdenados.length}) — ya están arriba; la
                    cascada no las aplica a cuotas
                  </p>
                  <ul className="space-y-1 text-xs text-amber-950">
                    {pagosNoOperativosOrdenados.map(p => {
                      const m =
                        typeof p.monto_pagado === 'number'
                          ? p.monto_pagado
                          : parseFloat(String(p.monto_pagado || 0)) || 0
                      return (
                        <li key={p.id} className="flex flex-wrap gap-x-3 gap-y-0.5">
                          <span className="font-mono">#{p.id}</span>
                          <span>{formatDate(p.fecha_pago)}</span>
                          <span className="font-semibold">
                            ${m.toFixed(2)}
                          </span>
                          <Badge
                            variant="outline"
                            className="border-amber-600 text-amber-950"
                          >
                            {String(p.estado ?? '—').trim() || '—'}
                          </Badge>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-6 px-1"
                            disabled={soloLectura}
                            onClick={() => abrirEditarPagoRevision(p)}
                          >
                            Ver
                          </Button>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>

      <Card className="overflow-hidden border-slate-200/80 shadow-sm">
        <CardHeader className="space-y-4 border-b border-slate-200/80 bg-gradient-to-br from-slate-50 via-white to-slate-50/90 pb-4">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:gap-3">
              <div
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary shadow-sm ring-1 ring-primary/10"
                aria-hidden
              >
                <BarChart3 className="h-5 w-5" />
              </div>
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle className="text-lg font-semibold tracking-tight">
                    Resumen: pagos del crédito vs cuotas
                  </CardTitle>
                  {hayPendienteRevision && !soloLectura ? (
                    <Badge
                      variant="outline"
                      className="border-amber-400/80 bg-amber-50 text-amber-950"
                    >
                      Cambios sin confirmar
                    </Badge>
                  ) : null}
                </div>
                <p className="max-w-prose text-sm text-muted-foreground">
                  Cifras del crédito en revisión (no solo la página visible de
                  la tabla). Contrasta montos en{' '}
                  <span className="font-medium text-foreground">pagos</span> con
                  lo aplicado en el{' '}
                  <span className="font-medium text-foreground">
                    plan de cuotas
                  </span>
                  .
                </p>
              </div>
            </div>
            <div
              className="flex flex-wrap gap-2 xl:max-w-[min(100%,36rem)] xl:justify-end"
              role="toolbar"
              aria-label="Acciones desde el resumen"
            >
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="gap-1.5"
                disabled={loadingPagosRealizados || fetchingPagosRealizados}
                onClick={() => void refetchPagosRealizados()}
              >
                <RefreshCw
                  className={`h-4 w-4 ${fetchingPagosRealizados ? 'animate-spin' : ''}`}
                />
                Actualizar datos
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="gap-1.5"
                disabled={
                  soloLectura ||
                  aplicarCascadaPagosMutation.isPending ||
                  !prestamoData.prestamo_id ||
                  Number(prestamoData.prestamo_id) <= 0
                }
                onClick={() => aplicarCascadaPagosMutation.mutate()}
                title={
                  soloLectura
                    ? 'Revisión cerrada: solo lectura'
                    : 'Guarda condiciones del préstamo; si faltan cuotas en BD respecto al plazo, reconstruye y aplica pagos en cascada.'
                }
              >
                {aplicarCascadaPagosMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <DollarSign className="h-4 w-4" />
                )}
                Cascada
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pt-5 text-sm">
          {!auditoriaCoherenciaActiva ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50/90 px-4 py-3 text-amber-950 shadow-sm">
              <span className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                <span>
                  El panel de coherencia (cuotas vs financiamiento y pagos) se
                  activa cuando el préstamo está en{' '}
                  <span className="font-semibold">Aprobado</span> o{' '}
                  <span className="font-semibold">Liquidado</span>. Estado
                  actual:{' '}
                  <span className="font-semibold">
                    {estadoPrestamoNorm || '-'}
                  </span>
                  . Registre pagos en la tabla de pagos y guarde con los botones
                  al final del formulario.
                </span>
              </span>
            </div>
          ) : loadingPagosRealizados &&
            !pagosRealizadosData?.resumen_prestamo ? (
            <div className="flex items-center gap-2 rounded-lg border bg-muted/20 px-4 py-6 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              Cargando resumen del crédito…
            </div>
          ) : !pagosRealizadosData?.resumen_prestamo ? (
            <div className="rounded-lg border border-dashed bg-muted/10 px-4 py-4 text-muted-foreground">
              No se recibió el agregado{' '}
              <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                resumen_prestamo
              </span>{' '}
              del servidor. Pulse «Actualizar datos» o revise el backend.
            </div>
          ) : (
            (() => {
              const rp = pagosRealizadosData.resumen_prestamo
              const tf = Number(prestamoData.total_financiamiento) || 0
              const { sumMonto: sumCuotasMonto, sumPagado: sumCuotasPagado } =
                agregadosCuotasRevision
              // Misma base que la tabla: todas las filas del crédito.
              let sumPagosTabla = 0
              for (const p of pagosRegistradosOrdenados) {
                const m =
                  typeof p.monto_pagado === 'number'
                    ? p.monto_pagado
                    : parseFloat(String(p.monto_pagado || 0)) || 0
                sumPagosTabla += m
              }
              sumPagosTabla = Math.round(sumPagosTabla * 100) / 100
              const sumPagosCredito =
                sumPagosTabla > 0 || pagosRegistradosOrdenados.length > 0
                  ? sumPagosTabla
                  : Number(rp.suma_monto_pagado) || 0
              const cantPagosCredito =
                pagosRegistradosOrdenados.length > 0
                  ? pagosRegistradosOrdenados.length
                  : Number(rp.cantidad) || 0
              const cantNoOper = pagosNoOperativosOrdenados.length
              const sumOperApi =
                rp.suma_monto_operativos != null
                  ? Number(rp.suma_monto_operativos)
                  : null
              const sumTotalBd =
                Number(rp.suma_monto_total_bd) || sumPagosCredito
              const diffPlanVsFin = sumCuotasMonto - tf
              const diffPagosVsCuotas = sumPagosCredito - sumCuotasPagado
              const faltaCubrirPlan = Math.max(
                0,
                sumCuotasMonto - sumCuotasPagado
              )
              const planAlineadoFin =
                Math.abs(diffPlanVsFin) <= COHERENCIA_USD_TOL
              const pagosAlineadosCuotas =
                Math.abs(diffPagosVsCuotas) <= COHERENCIA_USD_TOL
              const pendN = Number(rp.cantidad_pendiente) || 0
              const pendSum = Number(rp.suma_monto_pendiente) || 0
              const todoOk = planAlineadoFin && pagosAlineadosCuotas
              const pctCoberturaPlan =
                sumCuotasMonto > 0
                  ? Math.min(
                      100,
                      Math.round((sumCuotasPagado / sumCuotasMonto) * 1000) / 10
                    )
                  : 0

              const sugerencias: string[] = []
              if (!planAlineadoFin) {
                sugerencias.push(
                  `Cuotas (${sumCuotasMonto.toFixed(2)}) ≠ préstamo (${tf.toFixed(2)}).`
                )
              }
              if (!pagosAlineadosCuotas) {
                if (diffPagosVsCuotas > COHERENCIA_USD_TOL) {
                  sugerencias.push(
                    `La tabla suma $${sumPagosCredito.toFixed(2)} pero en cuotas solo hay $${sumCuotasPagado.toFixed(2)} (+${diffPagosVsCuotas.toFixed(2)}). Pruebe «Aplicar a cuotas».`
                  )
                } else {
                  sugerencias.push(
                    `Falta aplicar ${Math.abs(diffPagosVsCuotas).toFixed(2)} de los pagos a cuotas.`
                  )
                }
              }
              if (pendN > 0 && estadoPrestamoNorm === 'APROBADO') {
                sugerencias.push(
                  `${pendN} pago(s) sin aplicar (${pendSum.toFixed(2)}).`
                )
              }
              if (cantNoOper > 0) {
                let sumNo = 0
                for (const p of pagosNoOperativosOrdenados) {
                  sumNo +=
                    typeof p.monto_pagado === 'number'
                      ? p.monto_pagado
                      : parseFloat(String(p.monto_pagado || 0)) || 0
                }
                sugerencias.push(
                  `${cantNoOper} fila(s) con estado anulado/duplicado ($${sumNo.toFixed(2)}); la cascada las omite.`
                )
              } else if (
                sumOperApi != null &&
                Math.abs(sumTotalBd - sumOperApi) > COHERENCIA_USD_TOL
              ) {
                sugerencias.push(
                  `API: total BD $${sumTotalBd.toFixed(2)} vs operativos $${sumOperApi.toFixed(2)}, pero ninguna fila de esta tabla tiene estado anulado/duplicado.`
                )
              }
              if (
                estadoPrestamoNorm === 'LIQUIDADO' &&
                faltaCubrirPlan > COHERENCIA_USD_TOL
              ) {
                sugerencias.push(
                  'Liquidado con saldo pendiente en el plan.'
                )
              }

              const prestamoTotal = tf > 0 ? tf : sumCuotasMonto
              const pagado = sumPagosCredito
              // Contable: préstamo − pagado → >0 falta (rojo), <0 sobra (naranja), ≈0 cero (verde).
              const saldoContable =
                prestamoTotal > 0
                  ? prestamoTotal - pagado
                  : sumCuotasMonto - sumCuotasPagado
              const esFalta = saldoContable > COHERENCIA_USD_TOL
              const esSobra = saldoContable < -COHERENCIA_USD_TOL
              const resultadoLabel = esFalta
                ? 'Falta'
                : esSobra
                  ? 'Sobra'
                  : 'Cero'
              const resultadoMonto = esSobra
                ? Math.abs(saldoContable)
                : esFalta
                  ? saldoContable
                  : 0
              const resultadoColorClass = esFalta
                ? 'text-red-700'
                : esSobra
                  ? 'text-orange-600'
                  : 'text-emerald-800'
              const pctPagadoRaw =
                prestamoTotal > 0
                  ? Math.round((pagado / prestamoTotal) * 1000) / 10
                  : pctCoberturaPlan
              const pctPagado = Math.min(100, Math.max(0, pctPagadoRaw))
              const barraColorClass = esFalta
                ? 'bg-red-500'
                : esSobra
                  ? 'bg-orange-500'
                  : 'bg-emerald-500'

              return (
                <div className="space-y-3">
                  <div
                    className={`rounded-xl border p-4 shadow-sm ${
                      todoOk
                        ? 'border-slate-200 bg-white'
                        : 'border-amber-200 bg-amber-50/40'
                    }`}
                  >
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-foreground">
                        Resumen del crédito
                      </p>
                      <Badge
                        variant="outline"
                        className={
                          todoOk
                            ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                            : 'border-amber-400 bg-amber-50 text-amber-950'
                        }
                      >
                        {todoOk ? 'Cuadre OK' : 'Revisar cuadre'}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap items-stretch justify-center gap-1 sm:gap-2">
                      <div className="min-w-0 flex-1 basis-[28%] rounded-lg bg-slate-50 px-2 py-3 text-center sm:px-3">
                        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                          Préstamo
                        </p>
                        <p className="mt-1 truncate text-xl font-bold tabular-nums text-foreground sm:text-2xl">
                          ${prestamoTotal.toFixed(2)}
                        </p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          USD
                        </p>
                      </div>
                      <div
                        className="flex shrink-0 items-center px-0.5 text-lg font-semibold text-muted-foreground sm:px-1 sm:text-xl"
                        aria-hidden
                      >
                        −
                      </div>
                      <div className="min-w-0 flex-1 basis-[28%] rounded-lg bg-slate-50 px-2 py-3 text-center sm:px-3">
                        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                          Pagado
                        </p>
                        <p className="mt-1 truncate text-xl font-bold tabular-nums text-emerald-800 sm:text-2xl">
                          ${pagado.toFixed(2)}
                        </p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          USD
                          {cantPagosCredito > 0
                            ? ` · ${cantPagosCredito} abono${cantPagosCredito === 1 ? '' : 's'}`
                            : ''}
                        </p>
                      </div>
                      <div
                        className="flex shrink-0 items-center px-0.5 text-lg font-semibold text-muted-foreground sm:px-1 sm:text-xl"
                        aria-hidden
                      >
                        =
                      </div>
                      <div className="min-w-0 flex-1 basis-[28%] rounded-lg bg-slate-50 px-2 py-3 text-center sm:px-3">
                        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                          {resultadoLabel}
                        </p>
                        <p
                          className={`mt-1 truncate text-xl font-bold tabular-nums sm:text-2xl ${resultadoColorClass}`}
                        >
                          ${resultadoMonto.toFixed(2)}
                        </p>
                        <p className="mt-0.5 text-[11px] text-muted-foreground">
                          USD
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 space-y-1.5">
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>Avance</span>
                        <span className="font-semibold tabular-nums text-foreground">
                          {esSobra
                            ? `${pctPagadoRaw.toFixed(1)}%`
                            : `${pctPagado}%`}
                        </span>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200/80">
                        <div
                          className={`h-full rounded-full transition-[width] duration-300 ${barraColorClass}`}
                          style={{ width: `${pctPagado}%` }}
                        />
                      </div>
                    </div>

                    <div className="mt-4 overflow-x-auto border-t border-slate-100 pt-3">
                      <table className="w-full min-w-[18rem] text-sm">
                        <thead>
                          <tr className="text-left text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                            <th className="pb-2 pr-3 font-medium">Concepto</th>
                            <th className="pb-2 px-2 text-right font-medium">
                              Cuotas
                            </th>
                            <th className="pb-2 pl-2 text-right font-medium">
                              Saldo pendiente
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr className="border-t border-slate-100">
                            <td className="py-2.5 pr-3 font-medium text-amber-950">
                              Pagos vencidos
                            </td>
                            <td className="py-2.5 px-2 text-right tabular-nums text-foreground">
                              {agregadosCuotasRevision.vencidosN}
                            </td>
                            <td className="py-2.5 pl-2 text-right font-semibold tabular-nums text-amber-900">
                              $
                              {agregadosCuotasRevision.vencidosSaldo.toFixed(2)}
                            </td>
                          </tr>
                          <tr className="border-t border-slate-100">
                            <td className="py-2.5 pr-3 font-medium text-red-950">
                              Pagos en mora
                            </td>
                            <td className="py-2.5 px-2 text-right tabular-nums text-foreground">
                              {agregadosCuotasRevision.moraN}
                            </td>
                            <td className="py-2.5 pl-2 text-right font-semibold tabular-nums text-red-800">
                              $
                              {agregadosCuotasRevision.moraSaldo.toFixed(2)}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                      <p className="mt-2 text-[11px] leading-snug text-muted-foreground">
                        Según el estado de cada cuota del plan (vencido = atraso
                        sin umbral de mora; mora = ≥4 meses + 6 días desde el
                        vencimiento).
                      </p>
                    </div>
                  </div>

                  {sugerencias.length > 0 ? (
                    <div className="rounded-lg border border-amber-200 bg-amber-50/80 px-3 py-2 text-sm text-amber-950">
                      <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide">
                        <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                        Atención
                      </p>
                      <ul className="list-inside list-disc space-y-0.5 text-xs">
                        {sugerencias.map((t, i) => (
                          <li key={i}>{t}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              )
            })()
          )}
        </CardContent>
      </Card>
    </>
  )
}
