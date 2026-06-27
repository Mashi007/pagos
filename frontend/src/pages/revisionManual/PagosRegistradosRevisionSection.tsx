import {
  AlertTriangle,
  BarChart3,
  Check,
  CheckSquare,
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
import { ConciliarCarteraRevisionManualButton } from '../../components/pagos/ConciliarCarteraRevisionManualButton'
import { ConciliarCarteraPagosProgreso } from '../../components/pagos/ConciliarCarteraPagosProgreso'
import {
  claveDocumentoPagoListaNormalizada,
  textoDocumentoPagoParaListado,
} from '../../utils/pagoExcelValidation'
import {
  abrirStaffComprobanteDesdeHref,
  esUrlComprobanteImagenConAuth,
} from '../../utils/comprobanteImagenAuth'
import { DuplicadoPrestamosResumen } from '../../components/cobros/DuplicadoPrestamosComparacion'
import {
  COHERENCIA_USD_TOL,
  esInstitucionMercantilRevision,
  pagoSerialYaAplicadoEnOtroRegistroCartera,
} from './EditarRevisionManual.helpers'
import type { PagosRegistradosRevisionSectionProps } from './pagosRegistradosRevisionTypes'

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

  return (
    <>
      <Card ref={pagosRegistradosCardRef}>
        <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2 space-y-0 pb-2">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <CreditCard className="h-5 w-5" />
              Pagos registrados en cartera
            </CardTitle>
            {vieneDesdeFiniquitos ? (
              <p className="mt-1 max-w-2xl text-xs text-muted-foreground">
                Desde finiquitos: puede usar{' '}
                <strong className="text-amber-950">Reescanear</strong> (OCR
                sobre comprobantes ya guardados) o{' '}
                <strong className="text-amber-950">Conciliar</strong> (reserva
                comprobantes, ABONOS de Notificaciones → General, OCR y
                cascada). Al terminar, vuelva a finiquitos y pase el caso al
                área de trabajo.
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
                  : 'Guarda primero las condiciones del préstamo en BD; si faltan cuotas respecto al plazo, reconstruye la tabla y aplica pagos en cascada.'
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
                  : 'Subir imagen o PDF del comprobante para llenar el formulario de pago'
              }
            >
              {escaneandoComprobanteAgregarPago ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              Escanear comprobante
            </Button>
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
              title={
                soloLectura
                  ? 'Revision cerrada: solo lectura'
                  : 'Limpia fecha, banco, Nº, monto y moneda; re-escanea comprobantes guardados y persiste solo lo devuelto por OCR (sin mezclar con valores previos). Luego aplica cascada.'
              }
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
            {isAdmin &&
            prestamoData.prestamo_id != null &&
            Number(prestamoData.prestamo_id) > 0 ? (
              <ConciliarCarteraRevisionManualButton
                prestamoId={Number(prestamoData.prestamo_id)}
                cedula={cedulaParaPagosRealizados}
                disabled={soloLectura || conciliarTablaUi != null}
                faseTabla={conciliarTablaUi?.fase ?? null}
                idsAnterioresTabla={conciliarTablaUi?.idsAnteriores ?? []}
                pagosAntesTabla={conciliarTablaUi?.pagosAntes ?? 0}
                onEjecutarInicio={() => {
                  const idsAnt = idsPagosPrestamoEnTabla()
                  setConciliarTablaUi({
                    fase: 'borrando',
                    pagosAntes: idsAnt.length,
                    idsAnteriores: idsAnt,
                  })
                  pagosRegistradosCardRef.current?.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start',
                  })
                }}
                onProgresoTabla={fase => {
                  setConciliarTablaUi(prev =>
                    prev
                      ? { ...prev, fase }
                      : {
                          fase,
                          pagosAntes: contarPagosPrestamoEnTabla(),
                          idsAnteriores: idsPagosPrestamoEnTabla(),
                        }
                  )
                }}
                onEjecutarError={limpiarConciliarTablaUi}
                onExito={manejarConciliarExito}
              />
            ) : null}
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
                    Escanear comprobante
                  </Button>
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
              {pagosRealizadosData.sum_monto_pagado_cedula != null && (
                <p className="mb-3 text-sm font-medium text-foreground">
                  Total acumulado (todos los pagos de la cédula): $
                  {Number(pagosRealizadosData.sum_monto_pagado_cedula).toFixed(
                    2
                  )}{' '}
                  USD
                </p>
              )}
              <div className="overflow-x-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="whitespace-nowrap">ID</TableHead>
                      <TableHead className="whitespace-nowrap">
                        Fecha pago
                      </TableHead>
                      <TableHead className="whitespace-nowrap text-right">
                        Monto USD
                      </TableHead>
                      <TableHead className="whitespace-nowrap">Banco</TableHead>
                      <TableHead className="whitespace-nowrap">
                        Nº documento
                      </TableHead>
                      <TableHead className="whitespace-nowrap">
                        Crédito
                      </TableHead>
                      <TableHead>Notas</TableHead>
                      <TableHead className="min-w-[88px] whitespace-nowrap text-right">
                        Acciones
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
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
                      const prestObjRevision =
                        typeof pago.prestamo_id === 'number'
                          ? pago.prestamo_id
                          : null
                      const prestExRevision =
                        pago.duplicado_en_cartera_prestamo_id ?? null
                      const prestamoDupEsObjetivoRevision =
                        prestExRevision != null && prestObjRevision != null
                          ? prestExRevision === prestObjRevision
                          : null
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
                          <TableCell className="max-w-[180px] truncate text-sm">
                            {pago.institucion_bancaria?.trim()
                              ? pago.institucion_bancaria
                              : '-'}
                          </TableCell>
                          <TableCell
                            className={`max-w-[240px] font-mono text-xs ${
                              documentoDuplicadoEnPagina || serialDuplicadoCartera
                                ? 'bg-orange-100 text-orange-950'
                                : ''
                            }`}
                            title={
                              serialDuplicadoCartera
                                ? 'Serial ya aplicado en otro pago de cartera.'
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
                          </TableCell>
                          <TableCell className="whitespace-nowrap">
                            {pago.prestamo_id != null ? pago.prestamo_id : '-'}
                          </TableCell>
                          <TableCell className="max-w-[320px] align-top text-sm">
                            {serialDuplicadoCartera ? (
                              <div className="space-y-1.5">
                                <div className="rounded border border-orange-300 bg-orange-50 px-2 py-1.5 text-[11px] font-semibold leading-snug text-orange-950">
                                  PAGO DUPLICADO — En cartera Nº{' '}
                                  <span className="break-all font-mono font-normal">
                                    {pago.duplicado_en_cartera_numero_documento?.trim() ||
                                      '-'}
                                  </span>
                                  {pago.duplicado_en_cartera_pago_id != null
                                    ? ` · pago #${pago.duplicado_en_cartera_pago_id}`
                                    : ''}
                                  <DuplicadoPrestamosResumen
                                    prestamoExistenteId={prestExRevision}
                                    pagoExistenteId={
                                      pago.duplicado_en_cartera_pago_id
                                    }
                                    prestamoObjetivoId={prestObjRevision}
                                    prestamoDuplicadoEsObjetivo={
                                      prestamoDupEsObjetivoRevision
                                    }
                                    fechaPagoReporteIso={fechaPagoIsoRevision}
                                    esMercantil={esInstitucionMercantilRevision(
                                      pago.institucion_bancaria
                                    )}
                                  />
                                </div>
                                {pago.notas?.trim() ? (
                                  <p className="truncate text-muted-foreground">
                                    {pago.notas}
                                  </p>
                                ) : null}
                              </div>
                            ) : pago.notas?.trim() ? (
                              <span className="truncate text-muted-foreground">
                                {pago.notas}
                              </span>
                            ) : (
                              '-'
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
              const sumPagosCredito = Number(rp.suma_monto_pagado) || 0
              const cantPagosCredito = Number(rp.cantidad) || 0
              const cantNoOper = Number(rp.cantidad_no_operativos) || 0
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
              const pagN = Number(rp.cantidad_pagado) || 0
              const pagSum = Number(rp.suma_monto_estado_pagado) || 0
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
                  `Cuotas vs financiamiento: la suma de montos de cuotas (${sumCuotasMonto.toFixed(2)} USD) no coincide con el total declarado (${tf.toFixed(2)} USD); diferencia ${diffPlanVsFin.toFixed(2)}. Revise montos de cuotas o el total del préstamo y guarde.`
                )
              }
              if (!pagosAlineadosCuotas) {
                if (diffPagosVsCuotas > COHERENCIA_USD_TOL) {
                  sugerencias.push(
                    `Pagos vs aplicado: hay ${diffPagosVsCuotas.toFixed(2)} USD más en pagos del crédito que en total aplicado en cuotas. Pruebe «Cascada», revise pagos sin aplicar o duplicados.`
                  )
                } else {
                  sugerencias.push(
                    `Pagos vs aplicado: faltan ${Math.abs(diffPagosVsCuotas).toFixed(2)} USD en pagos del crédito respecto a lo aplicado en cuotas. Revise registros en la tabla de pagos o aplicaciones.`
                  )
                }
              }
              if (pendN > 0 && estadoPrestamoNorm === 'APROBADO') {
                sugerencias.push(
                  `Hay ${pendN} pago(s) sin aplicar a cuotas por ${pendSum.toFixed(2)} USD; valide cartera y luego cascada si corresponde.`
                )
              }
              if (
                cantNoOper > 0 &&
                sumTotalBd > sumPagosCredito + COHERENCIA_USD_TOL
              ) {
                sugerencias.push(
                  `Hay ${cantNoOper} pago(s) no operativo(s) (anulado/duplicado) por ${(sumTotalBd - sumPagosCredito).toFixed(2)} USD en la tabla; no entran en cascada ni en el cuadre de cartera.`
                )
              }
              if (
                pagosAlineadosCuotas &&
                faltaCubrirPlan > COHERENCIA_USD_TOL &&
                estadoPrestamoNorm === 'APROBADO'
              ) {
                sugerencias.push(
                  `Faltan ${faltaCubrirPlan.toFixed(2)} USD por cubrir en el cronograma (${pctCoberturaPlan}% cubierto). Los pagos operativos ya están aplicados; registre el abono faltante o revise cuotas.`
                )
              }
              if (
                estadoPrestamoNorm === 'LIQUIDADO' &&
                faltaCubrirPlan > COHERENCIA_USD_TOL
              ) {
                sugerencias.push(
                  'Crédito liquidado pero el cronograma muestra saldo pendiente: conviene revisar cuotas y pagos antes de cerrar la revisión.'
                )
              }

              return (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      variant="outline"
                      className={
                        todoOk
                          ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                          : 'border-amber-400 bg-amber-50 text-amber-950'
                      }
                    >
                      {todoOk ? 'Cuadre: coherente' : 'Cuadre: revisar'}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      Tolerancia numérica: {COHERENCIA_USD_TOL.toFixed(2)} USD
                    </span>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-sm ring-1 ring-slate-100">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                        Pagos (este crédito, BD)
                      </p>
                      <p className="mt-2 text-2xl font-bold tabular-nums text-foreground">
                        ${sumPagosCredito.toFixed(2)}{' '}
                        <span className="text-base font-semibold text-muted-foreground">
                          USD
                        </span>
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {cantPagosCredito}{' '}
                        {cantPagosCredito === 1 ? 'registro' : 'registros'} en
                        base
                        {cantNoOper > 0 ? (
                          <>
                            {' '}
                            ·{' '}
                            <span className="text-amber-800">
                              {cantNoOper} no operativo
                              {cantNoOper === 1 ? '' : 's'}
                            </span>
                          </>
                        ) : null}
                      </p>
                      <dl className="mt-3 space-y-1.5 border-t border-slate-100 pt-3 text-xs">
                        <div className="flex justify-between gap-2">
                          <dt className="text-muted-foreground">
                            Sin aplicar a cuotas
                          </dt>
                          <dd className="font-medium tabular-nums">
                            {pendN} · ${pendSum.toFixed(2)}
                          </dd>
                        </div>
                        <div className="flex justify-between gap-2">
                          <dt className="text-muted-foreground">
                            Con abono en cuotas
                          </dt>
                          <dd className="font-medium tabular-nums">
                            {pagN} · ${pagSum.toFixed(2)}
                          </dd>
                        </div>
                      </dl>
                    </div>

                    <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-sm ring-1 ring-slate-100">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                        Plan de cuotas (formulario / BD)
                      </p>
                      <p className="mt-2 text-2xl font-bold tabular-nums text-foreground">
                        ${sumCuotasMonto.toFixed(2)}{' '}
                        <span className="text-base font-semibold text-muted-foreground">
                          USD
                        </span>
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Aplicado en cuotas:{' '}
                        <span className="font-semibold text-foreground">
                          ${sumCuotasPagado.toFixed(2)} USD
                        </span>
                      </p>
                      <dl className="mt-3 space-y-1.5 border-t border-slate-100 pt-3 text-xs">
                        <div className="flex justify-between gap-2">
                          <dt className="text-muted-foreground">
                            Financiamiento declarado
                          </dt>
                          <dd className="font-medium tabular-nums">
                            ${tf.toFixed(2)}
                          </dd>
                        </div>
                        <div className="flex justify-between gap-2">
                          <dt className="text-muted-foreground">
                            Delta cuotas - financiamiento
                          </dt>
                          <dd
                            className={`font-semibold tabular-nums ${planAlineadoFin ? 'text-emerald-700' : 'text-amber-800'}`}
                          >
                            {diffPlanVsFin >= 0 ? '+' : ''}
                            {diffPlanVsFin.toFixed(2)}
                          </dd>
                        </div>
                      </dl>
                    </div>

                    <div
                      className={`rounded-xl border p-4 shadow-sm ring-1 sm:col-span-2 xl:col-span-1 ${
                        pagosAlineadosCuotas
                          ? 'border-emerald-200/90 bg-emerald-50/40 ring-emerald-100'
                          : diffPagosVsCuotas > COHERENCIA_USD_TOL
                            ? 'border-sky-200/90 bg-sky-50/50 ring-sky-100'
                            : 'border-orange-200/90 bg-orange-50/50 ring-orange-100'
                      }`}
                    >
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                        Pagos del crédito - aplicado en cuotas
                      </p>
                      <p
                        className={`mt-2 text-2xl font-bold tabular-nums ${
                          pagosAlineadosCuotas
                            ? 'text-emerald-800'
                            : diffPagosVsCuotas > COHERENCIA_USD_TOL
                              ? 'text-sky-900'
                              : 'text-orange-900'
                        }`}
                      >
                        {diffPagosVsCuotas >= 0 ? '+' : '-'}$
                        {Math.abs(diffPagosVsCuotas).toFixed(2)} USD
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {pagosAlineadosCuotas
                          ? 'Dentro de tolerancia: cartera alineada al plan.'
                          : diffPagosVsCuotas > COHERENCIA_USD_TOL
                            ? 'Sobrante en cartera vs cuotas.'
                            : 'Falta monto en pagos vs lo aplicado.'}
                      </p>
                      <div className="mt-4 space-y-1.5">
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>Cobertura del cronograma</span>
                          <span className="font-medium tabular-nums text-foreground">
                            {pctCoberturaPlan}%
                          </span>
                        </div>
                        <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/80 ring-1 ring-slate-200/80">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-[width] duration-300"
                            style={{
                              width: `${pctCoberturaPlan}%`,
                            }}
                          />
                        </div>
                        <p className="text-[11px] text-muted-foreground">
                          Aplicado sobre suma de montos de cuotas (
                          {sumCuotasMonto > 0
                            ? 'proporción cubierta'
                            : 'sin cuotas para medir'}
                          ).
                        </p>
                      </div>
                    </div>
                  </div>

                  {!planAlineadoFin && (
                    <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50/90 px-4 py-3 text-amber-950 shadow-sm">
                      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                      <div>
                        <p className="font-semibold">
                          Financiamiento vs suma de cuotas
                        </p>
                        <p className="mt-1 text-sm">
                          La suma de montos de cuotas ($
                          {sumCuotasMonto.toFixed(2)}) no coincide con el
                          financiamiento (${tf.toFixed(2)}); diferencia{' '}
                          {diffPlanVsFin.toFixed(2)} USD.
                        </p>
                      </div>
                    </div>
                  )}

                  <div
                    className={`flex items-start gap-3 rounded-lg border px-4 py-3 shadow-sm ${
                      pagosAlineadosCuotas
                        ? 'border-emerald-200 bg-emerald-50/90 text-emerald-950'
                        : diffPagosVsCuotas > COHERENCIA_USD_TOL
                          ? 'border-sky-200 bg-sky-50/90 text-sky-950'
                          : 'border-orange-200 bg-orange-50/90 text-orange-950'
                    }`}
                  >
                    {pagosAlineadosCuotas ? (
                      <Check className="mt-0.5 h-5 w-5 shrink-0" />
                    ) : (
                      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                    )}
                    <div className="min-w-0 space-y-1">
                      <p className="font-semibold">
                        Pagos del crédito vs total aplicado en cuotas
                      </p>
                      {pagosAlineadosCuotas ? (
                        <p className="text-sm">
                          Coherente: la suma de pagos del crédito coincide con
                          lo aplicado en cuotas (tolerancia{' '}
                          {COHERENCIA_USD_TOL.toFixed(2)} USD).
                        </p>
                      ) : diffPagosVsCuotas > COHERENCIA_USD_TOL ? (
                        <p className="text-sm">
                          <span className="font-semibold">
                            Sobrante en cartera
                          </span>{' '}
                          respecto a lo aplicado: {diffPagosVsCuotas.toFixed(2)}{' '}
                          USD. Suele deberse a pagos sin cascada o cuotas
                          desactualizadas.
                        </p>
                      ) : (
                        <p className="text-sm">
                          <span className="font-semibold">Falta en pagos</span>{' '}
                          respecto a lo aplicado:{' '}
                          {Math.abs(diffPagosVsCuotas).toFixed(2)} USD. Revise
                          registros y aplicaciones.
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-200/90 bg-slate-50/50 p-4 shadow-sm">
                    <p className="text-sm font-semibold text-foreground">
                      Falta por cubrir en el plan de cuotas
                    </p>
                    <p className="mt-1 text-3xl font-bold tabular-nums tracking-tight text-foreground">
                      ${faltaCubrirPlan.toFixed(2)}{' '}
                      <span className="text-lg font-semibold text-muted-foreground">
                        USD
                      </span>
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Saldo pendiente del cronograma (suma montos de cuotas
                      menos total aplicado).
                    </p>
                  </div>

                  {sugerencias.length > 0 ? (
                    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm ring-1 ring-slate-100">
                      <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
                        <CheckSquare className="h-4 w-4 shrink-0 text-primary" />
                        Qué revisar (priorizado)
                      </p>
                      <ul className="list-inside list-decimal space-y-2 text-sm text-muted-foreground marker:text-primary">
                        {sugerencias.map((t, i) => (
                          <li key={i} className="pl-0.5">
                            {t}
                          </li>
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
