import { Link } from 'react-router-dom'
import { Check, Edit, Eye, FileText, Loader2, Trash2, X } from 'lucide-react'
import { Button } from '../../ui/button'
import { Input } from '../../ui/input'
import { ListPaginationBar } from '../../ui/ListPaginationBar'
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card'
import { Badge } from '../../ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../../ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../ui/table'
import { formatDate, cn } from '../../../utils'
import { toast } from 'sonner'
import type { PagoConError } from '../../../services/pagoConErrorService'
import {
  observacionesConMarcaDuplicadoCartera,
  pagoEstaCerradoSoloConsulta,
} from './pagosListUtils'
import { textoDocumentoPagoParaListado } from '../../../utils/pagoExcelValidation'
import {
  usePagosRevisionTab,
  type UsePagosRevisionTabOptions,
} from './usePagosRevisionTab'

export type PagosRevisionTabProps = UsePagosRevisionTabOptions

export function PagosRevisionTab(props: PagosRevisionTabProps) {
  const tab = usePagosRevisionTab(props)
  const {
    revisionCedulaInput,
    setRevisionCedulaInput,
    revisionNumeroDocumentoInput,
    setRevisionNumeroDocumentoInput,
    revisionCedulaFiltro,
    revisionNumeroDocumentoFiltro,
    includeRevisionExportados,
    setIncludeRevisionExportados,
    setRevisionPage,
    isLoadingRevision,
    isRevisionError,
    revisionData,
    showBorradoresEscanerDialog,
    setShowBorradoresEscanerDialog,
    isLoadingBorradoresPendientes,
    isBorradoresPendientesError,
    borradoresPendientes,
    handleBuscarRevisionPorCedula,
    handleLimpiarRevisionCedula,
    handleSiguienteAnomalia,
    bulkRevisionObservacion,
    setBulkRevisionObservacion,
    selectedRevisionIds,
    isBulkSavingRevision,
    isBulkMovingRevision,
    bulkMovingProgress,
    isBulkDeletingRevision,
    isBulkScanningRevision,
    isLimpiandoYaCargados,
    handleGuardarRevisionMasivo,
    handleMoverRevisionMasivo,
    handleEliminarRevisionMasivo,
    handleEscanearRevisionMasivo,
    handleLimpiarYaCargados,
    resumenRevision,
    revisionRowsFiltradas,
    toggleRevisionSeleccionTodas,
    toggleRevisionSeleccion,
    editingRevisionId,
    revisionObservacionDraft,
    setRevisionObservacionDraft,
    savingRevisionId,
    deletingRevisionId,
    handleGuardarRevision,
    handleEliminarRevision,
    handleEditarRevision,
    handleAbrirEditorPagoRevision,
    openStaffComprobanteForList,
    deletingBorradorId,
    handleEliminarBorradorPendiente,
  } = tab

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Revisión Manual de Pagos</CardTitle>
          <p className="text-sm text-muted-foreground">
            Mesa de trabajo para revisar y procesar pagos con errores de
            validación. Edita observaciones, elimina registros o mueve pagos
            corregidos a la tabla principal.
          </p>
          <p className="mt-2 rounded bg-blue-50 p-2 text-xs font-medium text-blue-700">
            ℹ️ Flujo: Edita observaciones → Mover a Pagos Normales → Se aplican
            automáticamente a cuotas
          </p>
        </CardHeader>
        <CardContent>
          <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50/50 p-3">
            <p className="text-sm font-medium text-blue-950">
              ✅ Acciones Disponibles
            </p>
            <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-blue-900/90">
              <li>
                <strong>Guardar Observación:</strong> Actualiza notas sin mover
                el pago
              </li>
              <li>
                <strong>Mover a Pagos Normales:</strong> Traslada a tabla
                principal y aplica automáticamente a cuotas
              </li>
              <li>
                <strong>Eliminar:</strong> Borra el pago de revisión (no
                recuperable)
              </li>
              <li>
                <strong>Escanear:</strong> Abre interfaz de escaneo para este
                lote
              </li>
            </ul>
          </div>
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Filtrar por cédula
              </label>
              <Input
                placeholder="Ej: V12345678"
                value={revisionCedulaInput}
                onChange={e => setRevisionCedulaInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleBuscarRevisionPorCedula()
                  }
                }}
                className="max-w-md"
              />
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Filtrar por N° documento
              </label>
              <Input
                placeholder="Ej: 00012345"
                value={revisionNumeroDocumentoInput}
                onChange={e => setRevisionNumeroDocumentoInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleBuscarRevisionPorCedula()
                  }
                }}
                className="max-w-md"
              />
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowBorradoresEscanerDialog(true)}
              >
                Borradores escáner (
                {isLoadingBorradoresPendientes
                  ? '...'
                  : String(borradoresPendientes.length)}
                )
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={handleBuscarRevisionPorCedula}
              >
                Buscar
              </Button>
              <Button
                type="button"
                onClick={handleSiguienteAnomalia}
                title="Abrir la siguiente fila priorizada para edición"
              >
                Siguiente anomalía
              </Button>
              {(revisionCedulaFiltro || revisionNumeroDocumentoFiltro) && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={handleLimpiarRevisionCedula}
                >
                  <X className="mr-1 h-4 w-4" />
                  Limpiar
                </Button>
              )}
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={includeRevisionExportados}
                onChange={e => {
                  setIncludeRevisionExportados(e.target.checked)
                }}
              />
              Incluir exportados/archivados
            </label>
          </div>
          {isLoadingRevision ? (
            <div className="py-8 text-center text-sm text-gray-500">
              Cargando pendientes de revisión...
            </div>
          ) : isRevisionError ? (
            <div className="py-8 text-center text-sm text-red-600">
              Error cargando pendientes de revisión
            </div>
          ) : !revisionData?.pagos?.length ? (
            <div className="py-8 text-center text-sm text-gray-500">
              No hay pagos pendientes de revisión.
            </div>
          ) : (
            <>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Input
                  placeholder="Observación masiva para seleccionados"
                  value={bulkRevisionObservacion}
                  onChange={e => setBulkRevisionObservacion(e.target.value)}
                  className="max-w-sm"
                />
                <Button
                  variant="outline"
                  onClick={() => void handleGuardarRevisionMasivo()}
                  disabled={
                    selectedRevisionIds.size === 0 || isBulkSavingRevision
                  }
                >
                  {isBulkSavingRevision
                    ? 'Guardando...'
                    : 'Guardar seleccionados'}
                </Button>
                <Button
                  variant="default"
                  onClick={() => void handleMoverRevisionMasivo()}
                  disabled={
                    selectedRevisionIds.size === 0 || isBulkMovingRevision
                  }
                  className="bg-green-600 hover:bg-green-700"
                  title="Para los pagos seleccionados: pasan a la tabla pagos, se marcan conciliados (verificado SI) y se aplican a cuotas en cascada. Filas con duplicado de documento se omiten con aviso."
                >
                  {isBulkMovingRevision ? (
                    <>
                      <span className="mr-2 inline-block animate-spin">⏳</span>
                      Cargando {bulkMovingProgress.movidos}/
                      {bulkMovingProgress.total}...
                    </>
                  ) : (
                    <>
                      ✓ Cargar pagos en masa
                      {selectedRevisionIds.size > 0
                        ? ` (${selectedRevisionIds.size})`
                        : ''}
                    </>
                  )}
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => void handleEliminarRevisionMasivo()}
                  disabled={
                    selectedRevisionIds.size === 0 || isBulkDeletingRevision
                  }
                >
                  {isBulkDeletingRevision
                    ? 'Eliminando...'
                    : 'Eliminar seleccionados'}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => handleEscanearRevisionMasivo()}
                  disabled={
                    selectedRevisionIds.size === 0 || isBulkScanningRevision
                  }
                >
                  {isBulkScanningRevision
                    ? 'Abriendo escáner...'
                    : 'Escanear seleccionados (máx. 10)'}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => void handleLimpiarYaCargados()}
                  disabled={isLimpiandoYaCargados}
                  className="border-emerald-300 text-emerald-800 hover:bg-emerald-50"
                  title="Elimina de revisión las filas cuyo Nº de documento ya está cargado y aplicado a cuotas en cartera (mismo cliente y préstamo). Si hay seleccionados, opera sobre ellos; si no, barre toda la lista pendiente."
                >
                  {isLimpiandoYaCargados ? (
                    <>
                      <span className="mr-2 inline-block animate-spin">⏳</span>
                      Limpiando...
                    </>
                  ) : (
                    <>
                      🧹 Limpiar pagos ya cargados
                      {selectedRevisionIds.size > 0
                        ? ` (${selectedRevisionIds.size})`
                        : ' (toda la lista)'}
                    </>
                  )}
                </Button>
                <span className="text-xs text-gray-600">
                  Seleccionados: {selectedRevisionIds.size}
                </span>
              </div>
              <p className="mb-2 text-xs text-slate-600">
                <strong>Cargar pagos en masa</strong>: para cada fila
                seleccionada se mueve a la tabla operativa{' '}
                <code className="font-mono">pagos</code>, se marca conciliado y
                verificado <strong>SI</strong>, y se ejecuta la cascada para
                aplicar cuotas. Las filas con documento duplicado en cartera se
                omiten con aviso (use <strong>Visto</strong> para asignar código
                y reintentar).
              </p>
              <p className="mb-2 text-xs text-slate-600">
                <strong>🧹 Limpiar pagos ya cargados</strong>: detecta y elimina
                filas cuyo Nº de documento ya tiene un pago en cartera con
                cuota_pagos aplicado (mismo cliente y préstamo). Si hay
                seleccionados, solo evalúa esos; si no, barre toda la lista.
                Ahorra ir uno por uno borrando duplicados ya conciliados en el
                préstamo.
              </p>
              <div className="mb-3 flex flex-wrap gap-2 text-xs">
                <Badge variant="outline">
                  Duplicados: {resumenRevision.duplicados}
                </Badge>
                <Badge variant="outline">
                  Irreales: {resumenRevision.irreales}
                </Badge>
                <Badge variant="outline">
                  Sin crédito: {resumenRevision.sinCredito}
                </Badge>
                <Badge variant="outline">
                  Con observación: {resumenRevision.conObservacion}
                </Badge>
              </div>
              <div className="overflow-hidden rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[44px]">
                        <input
                          type="checkbox"
                          checked={
                            revisionRowsFiltradas.length > 0 &&
                            revisionRowsFiltradas.every(r =>
                              selectedRevisionIds.has(r.pago.id)
                            )
                          }
                          onChange={toggleRevisionSeleccionTodas}
                        />
                      </TableHead>
                      <TableHead>ID</TableHead>
                      <TableHead>Cédula</TableHead>
                      <TableHead>Crédito</TableHead>
                      <TableHead>Monto</TableHead>
                      <TableHead>Fecha Pago</TableHead>
                      <TableHead>Nº Documento</TableHead>
                      <TableHead>Motivos</TableHead>
                      <TableHead>Observación</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {revisionRowsFiltradas.map(({ pago, motivos, score }) => (
                      <TableRow
                        key={pago.id}
                        className={score >= 2 ? 'bg-amber-50/40' : undefined}
                      >
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={selectedRevisionIds.has(pago.id)}
                            onChange={() => toggleRevisionSeleccion(pago.id)}
                          />
                        </TableCell>
                        <TableCell>{pago.id}</TableCell>
                        <TableCell>{pago.cedula_cliente}</TableCell>
                        <TableCell>
                          {pago.prestamo_id ? `#${pago.prestamo_id}` : '-'}
                        </TableCell>
                        <TableCell>
                          ${Number(pago.monto_pagado).toFixed(2)}
                        </TableCell>
                        <TableCell>{formatDate(pago.fecha_pago)}</TableCell>
                        <TableCell>
                          {textoDocumentoPagoParaListado(
                            pago.numero_documento,
                            pago.codigo_documento
                          )}
                        </TableCell>
                        <TableCell className="max-w-[260px]">
                          <div className="flex flex-wrap gap-1">
                            {motivos.length === 0 ? (
                              <Badge variant="outline">Sin marca</Badge>
                            ) : (
                              motivos.map(m => (
                                <Badge
                                  key={`${pago.id}-${m}`}
                                  variant="outline"
                                >
                                  {m}
                                </Badge>
                              ))
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="min-w-[260px]">
                          {editingRevisionId === pago.id ? (
                            <Input
                              value={revisionObservacionDraft}
                              onChange={e =>
                                setRevisionObservacionDraft(e.target.value)
                              }
                              onKeyDown={e => {
                                if (e.key === 'Enter') {
                                  e.preventDefault()
                                  void handleGuardarRevision(pago.id)
                                }
                              }}
                              placeholder="Motivo por el que no cumple"
                            />
                          ) : (
                            <span
                              className={cn(
                                'text-sm text-amber-700',
                                (pago as PagoConError)
                                  .duplicado_documento_en_pagos === true &&
                                  'font-semibold text-orange-900'
                              )}
                            >
                              {(() => {
                                const pe = pago as PagoConError
                                const texto =
                                  observacionesConMarcaDuplicadoCartera(
                                    pe
                                  ).trim()
                                return (
                                  texto ||
                                  (!pe.duplicado_documento_en_pagos &&
                                    'No cumple validaciones automáticas') ||
                                  ''
                                )
                              })()}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="inline-flex items-center gap-2">
                            <Button
                              size="icon"
                              variant="outline"
                              title="Ver recibo"
                              onClick={() => {
                                if (!pago.documento_ruta) {
                                  toast.error(
                                    'Este pago no tiene recibo o comprobante asociado.'
                                  )
                                  return
                                }
                                void openStaffComprobanteForList(
                                  pago.documento_ruta,
                                  `Pago #${pago.id}`,
                                  pago.id
                                )
                              }}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            {(() => {
                              const cerrado = pagoEstaCerradoSoloConsulta(pago)
                              return (
                                <Button
                                  size="icon"
                                  variant="outline"
                                  title={
                                    cerrado
                                      ? 'Ver pago (solo consulta - ya cargado a cuotas)'
                                      : 'Editar pago'
                                  }
                                  aria-label={
                                    cerrado
                                      ? 'Ver pago (solo consulta)'
                                      : 'Editar pago'
                                  }
                                  onClick={() =>
                                    handleAbrirEditorPagoRevision(pago)
                                  }
                                >
                                  {cerrado ? (
                                    <Eye className="h-4 w-4" />
                                  ) : (
                                    <Edit className="h-4 w-4" />
                                  )}
                                </Button>
                              )
                            })()}
                            <Button
                              size="icon"
                              variant="outline"
                              title="Editar observación"
                              onClick={() => handleEditarRevision(pago)}
                            >
                              <FileText className="h-4 w-4" />
                            </Button>
                            <Button
                              size="icon"
                              variant="outline"
                              title="Guardar observación"
                              disabled={
                                editingRevisionId !== pago.id ||
                                savingRevisionId === pago.id
                              }
                              onClick={() =>
                                void handleGuardarRevision(pago.id)
                              }
                            >
                              {savingRevisionId === pago.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Check className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              size="icon"
                              variant="destructive"
                              title="Eliminar fila"
                              disabled={deletingRevisionId === pago.id}
                              onClick={() =>
                                void handleEliminarRevision(pago.id)
                              }
                            >
                              {deletingRevisionId === pago.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Trash2 className="h-4 w-4" />
                              )}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <ListPaginationBar
                className="mt-4"
                page={revisionData.page}
                totalPages={Math.max(1, revisionData.total_pages)}
                onPageChange={p => setRevisionPage(p)}
                subtitle={`${revisionData.total} registros · ${revisionData.per_page} por página`}
              />
            </>
          )}
        </CardContent>
      </Card>
      <Dialog
        open={showBorradoresEscanerDialog}
        onOpenChange={setShowBorradoresEscanerDialog}
      >
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Borradores con validación pendiente (Escáner)
            </DialogTitle>
          </DialogHeader>
          {isLoadingBorradoresPendientes ? (
            <p className="text-sm text-slate-600">Cargando lista...</p>
          ) : isBorradoresPendientesError ? (
            <p className="text-sm text-red-700">
              No se pudo cargar la lista de borradores del escáner.
            </p>
          ) : borradoresPendientes.length === 0 ? (
            <p className="text-sm text-slate-600">
              No hay borradores pendientes.
            </p>
          ) : (
            <ul className="divide-y divide-amber-200 rounded-md border border-amber-200 bg-white">
              {borradoresPendientes.map(row => (
                <li
                  key={row.id}
                  className="flex flex-wrap items-start justify-between gap-2 px-3 py-2 text-sm"
                >
                  <div className="min-w-0 flex-1 space-y-0.5">
                    <p className="font-medium text-slate-900">
                      {(
                        row.cliente_nombre ||
                        row.cedula_normalizada ||
                        ''
                      ).trim() || 'Cliente'}
                      <span className="ml-2 font-mono text-xs text-slate-600">
                        {row.comprobante_nombre}
                      </span>
                    </p>
                    <p className="text-xs text-slate-600">
                      {row.resumen_validacion}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 gap-1 px-2"
                      asChild
                    >
                      <Link
                        to={`/escaner?borrador=${encodeURIComponent(row.id)}`}
                      >
                        <Edit className="h-3.5 w-3.5" />
                        Editar
                      </Link>
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 gap-1 border-red-200 px-2 text-red-800 hover:bg-red-50"
                      disabled={deletingBorradorId === row.id}
                      onClick={() =>
                        void handleEliminarBorradorPendiente(row.id)
                      }
                    >
                      {deletingBorradorId === row.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                      Eliminar
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
