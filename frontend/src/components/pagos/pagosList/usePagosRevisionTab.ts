import { useState, useEffect, useMemo, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import {
  deleteInfopagosBorradorEscaneer,
  listInfopagosBorradoresEscaneer,
  type InfopagosBorradorListItem,
} from '../../../services/cobrosService'
import {
  pagoConErrorService,
  type PagoConError,
} from '../../../services/pagoConErrorService'
import { invalidatePagosPrestamosRevisionYCuotas } from '../../../constants/queryKeys'
import { getErrorMessage } from '../../../types/errors'
import { eliminarPagoRevisionOConError } from '../../../utils/eliminarPagoRevision'
import { BASE_PATH } from '../../../config/env'
import { claveDocumentoPagoListaNormalizada } from '../../../utils/pagoExcelValidation'

export type RevisionRowAnalizada = {
  pago: PagoConError
  motivos: string[]
  score: number
  esDuplicadoFechaNumero: boolean
}

export type UsePagosRevisionTabOptions = {
  active: boolean
  perPage: number
  includeExportados: boolean
  onIncludeExportadosChange: (value: boolean) => void
  onOpenPagoEditor: (pago: PagoConError) => void
  openStaffComprobanteForList: (
    href: string,
    label: string,
    pagoId: number | null
  ) => void | Promise<void>
}

export function usePagosRevisionTab({
  active,
  perPage,
  includeExportados,
  onIncludeExportadosChange,
  onOpenPagoEditor,
  openStaffComprobanteForList,
}: UsePagosRevisionTabOptions) {
  const queryClient = useQueryClient()
  const [revisionPage, setRevisionPage] = useState(1)
  const [revisionCedulaInput, setRevisionCedulaInput] = useState('')
  const [revisionCedulaFiltro, setRevisionCedulaFiltro] = useState('')
  const [revisionNumeroDocumentoInput, setRevisionNumeroDocumentoInput] =
    useState('')
  const [revisionNumeroDocumentoFiltro, setRevisionNumeroDocumentoFiltro] =
    useState('')
  const [revisionFechaPagoInput, setRevisionFechaPagoInput] = useState('')
  const [revisionFechaPagoFiltro, setRevisionFechaPagoFiltro] = useState('')
  const [revisionTipoFiltro, setRevisionTipoFiltro] = useState<
    '' | 'anomalo' | 'irreal' | 'duplicado'
  >('')
  const [revisionMotivoFiltro, setRevisionMotivoFiltro] = useState<
    | ''
    | 'sin_credito'
    | 'duplicado'
    | 'irreal'
    | 'con_observacion'
    | 'error_validacion'
  >('')
  const [editingRevisionId, setEditingRevisionId] = useState<number | null>(
    null
  )
  const [revisionObservacionDraft, setRevisionObservacionDraft] = useState('')
  const [savingRevisionId, setSavingRevisionId] = useState<number | null>(null)
  const [deletingRevisionId, setDeletingRevisionId] = useState<number | null>(
    null
  )
  const [selectedRevisionIds, setSelectedRevisionIds] = useState<Set<number>>(
    new Set()
  )
  const [isBulkScanningRevision, setIsBulkScanningRevision] = useState(false)
  const [bulkRevisionObservacion, setBulkRevisionObservacion] = useState('')
  const [isBulkSavingRevision, setIsBulkSavingRevision] = useState(false)
  const [isBulkDeletingRevision, setIsBulkDeletingRevision] = useState(false)
  const [isBulkMovingRevision, setIsBulkMovingRevision] = useState(false)
  const [isLimpiandoYaCargados, setIsLimpiandoYaCargados] = useState(false)
  const [bulkMovingProgress, setBulkMovingProgress] = useState({
    movidos: 0,
    total: 0,
  })
  const [deletingBorradorId, setDeletingBorradorId] = useState<string | null>(
    null
  )
  const [showBorradoresEscanerDialog, setShowBorradoresEscanerDialog] =
    useState(false)

  const {
    data: revisionData,
    isLoading: isLoadingRevision,
    isError: isRevisionError,
  } = useQuery({
    queryKey: [
      'pagos-con-errores-tab',
      revisionPage,
      perPage,
      revisionCedulaFiltro,
      revisionNumeroDocumentoFiltro,
      includeExportados,
    ],
    queryFn: () =>
      pagoConErrorService.getAll(revisionPage, perPage, {
        cedula: revisionCedulaFiltro || undefined,
        numeroDocumento: revisionNumeroDocumentoFiltro || undefined,
        includeExportados: includeExportados,
      }),
    enabled: active,
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  })
  const {
    data: borradoresPendientesData,
    isLoading: isLoadingBorradoresPendientes,
    isError: isBorradoresPendientesError,
  } = useQuery({
    queryKey: ['escaner-infopagos-borradores-pendientes'],
    queryFn: () => listInfopagosBorradoresEscaneer(40),
    enabled: active,
    staleTime: 15_000,
    refetchOnWindowFocus: false,
  })

  const revisionRowsAnalizadas = useMemo(() => {
    const rows = revisionData?.pagos ?? []
    const dupMap = new Map<string, number>()
    for (const p of rows) {
      const f =
        typeof p.fecha_pago === 'string'
          ? p.fecha_pago.slice(0, 10)
          : new Date(p.fecha_pago).toISOString().slice(0, 10)
      const docKey = claveDocumentoPagoListaNormalizada(
        p.numero_documento,
        p.codigo_documento ?? null
      )
      if (!docKey) continue
      const key = `${f}::${docKey}`
      dupMap.set(key, (dupMap.get(key) ?? 0) + 1)
    }
    return rows
      .map(p => {
        const motivos: string[] = []
        const monto = Number(p.monto_pagado ?? 0)
        const fechaPagoDate = new Date(p.fecha_pago as string)
        const hoy = new Date()
        hoy.setHours(0, 0, 0, 0)
        const docKey = claveDocumentoPagoListaNormalizada(
          p.numero_documento,
          p.codigo_documento ?? null
        )
        const fechaKey = Number.isNaN(fechaPagoDate.getTime())
          ? ''
          : fechaPagoDate.toISOString().slice(0, 10)
        const dupKey = docKey && fechaKey ? `${fechaKey}::${docKey}` : ''
        const esDuplicadoFechaNumero = dupKey
          ? (dupMap.get(dupKey) ?? 0) > 1
          : false
        if (monto <= 0) motivos.push('Monto no válido')
        if (!Number.isNaN(fechaPagoDate.getTime()) && fechaPagoDate > hoy) {
          motivos.push('Fecha futura')
        }
        if (esDuplicadoFechaNumero) motivos.push('Duplicado fecha + número')
        if ((p as PagoConError).duplicado_documento_en_pagos === true) {
          motivos.push('Documento duplicado (pagos)')
        }
        if (!p.prestamo_id) motivos.push('Sin crédito asociado')
        if ((p.observaciones ?? '').trim()) motivos.push('Con observación')
        if ((p.errores_descripcion ?? []).length > 0) {
          motivos.push('Error de validación')
        }
        if (
          revisionTipoFiltro === 'irreal' &&
          !motivos.includes('Monto no válido') &&
          !motivos.includes('Fecha futura')
        ) {
          motivos.push('Irreal detectado por regla de cartera')
        }
        return {
          pago: p,
          motivos,
          score: motivos.length,
          esDuplicadoFechaNumero,
        }
      })
      .sort((a, b) => {
        // Fecha de pago ascendente (más antiguas primero); fechas inválidas al final.
        const fa = new Date(a.pago.fecha_pago as string).getTime()
        const fb = new Date(b.pago.fecha_pago as string).getTime()
        const aValida = !Number.isNaN(fa)
        const bValida = !Number.isNaN(fb)
        if (aValida && bValida && fa !== fb) return fa - fb
        if (aValida !== bValida) return aValida ? -1 : 1
        // Empate por fecha: anomalías primero, luego id ascendente.
        return b.score - a.score || a.pago.id - b.pago.id
      })
  }, [revisionData?.pagos, revisionTipoFiltro])
  const revisionRowsFiltradas = useMemo(() => {
    if (!revisionMotivoFiltro) return revisionRowsAnalizadas
    return revisionRowsAnalizadas.filter(row => {
      if (revisionMotivoFiltro === 'sin_credito') {
        return row.motivos.includes('Sin crédito asociado')
      }
      if (revisionMotivoFiltro === 'duplicado') {
        return (
          row.motivos.includes('Duplicado fecha + número') ||
          row.motivos.includes('Documento duplicado (pagos)')
        )
      }
      if (revisionMotivoFiltro === 'irreal') {
        return (
          row.motivos.includes('Monto no válido') ||
          row.motivos.includes('Fecha futura') ||
          row.motivos.includes('Irreal detectado por regla de cartera')
        )
      }
      if (revisionMotivoFiltro === 'con_observacion') {
        return row.motivos.includes('Con observación')
      }
      if (revisionMotivoFiltro === 'error_validacion') {
        return row.motivos.includes('Error de validación')
      }
      return true
    })
  }, [revisionRowsAnalizadas, revisionMotivoFiltro])
  const borradoresPendientes: InfopagosBorradorListItem[] =
    borradoresPendientesData?.items ?? []
  useEffect(() => {
    const idsVisibles = new Set(revisionRowsFiltradas.map(r => r.pago.id))
    setSelectedRevisionIds(prev => {
      const next = new Set<number>()
      prev.forEach(id => {
        if (idsVisibles.has(id)) next.add(id)
      })
      return next
    })
  }, [revisionRowsFiltradas])
  const resumenRevision = useMemo(() => {
    const resumen = {
      duplicados: 0,
      irreales: 0,
      sinCredito: 0,
      conObservacion: 0,
    }
    for (const row of revisionRowsAnalizadas) {
      if (row.esDuplicadoFechaNumero) resumen.duplicados += 1
      if (
        row.motivos.includes('Monto no válido') ||
        row.motivos.includes('Fecha futura') ||
        row.motivos.includes('Irreal detectado por regla de cartera')
      ) {
        resumen.irreales += 1
      }
      if (row.motivos.includes('Sin crédito asociado')) resumen.sinCredito += 1
      if (row.motivos.includes('Con observación')) resumen.conObservacion += 1
    }
    return resumen
  }, [revisionRowsAnalizadas])

  const [searchParams, setSearchParams] = useSearchParams()
  useEffect(() => {
    const pestana = (searchParams.get('pestana') || '').trim().toLowerCase()
    if (pestana !== 'revision' && pestana !== 'revision-global') return
    const ndoc = (searchParams.get('numero_documento') || '').trim()
    if (ndoc) {
      setRevisionNumeroDocumentoInput(ndoc)
      setRevisionNumeroDocumentoFiltro(ndoc)
    }
    setRevisionPage(1)
    const next = new URLSearchParams(searchParams)
    next.delete('pestana')
    next.delete('numero_documento')
    if (next.toString()) {
      setSearchParams(next, { replace: true })
    } else {
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, setSearchParams])

  const setIncludeRevisionExportados = useCallback(
    (checked: boolean) => {
      onIncludeExportadosChange(checked)
      setRevisionPage(1)
    },
    [onIncludeExportadosChange]
  )

  const refetchDiagnosticoRevision = async () => {
    await queryClient.refetchQueries({
      queryKey: ['pagos-con-errores-tab'],
      exact: false,
    })
    await queryClient.refetchQueries({
      queryKey: ['pagos-revision-global-tab'],
      exact: false,
    })
  }
  const handleEditarRevision = (pago: PagoConError) => {
    setEditingRevisionId(pago.id)
    setRevisionObservacionDraft((pago.observaciones ?? '').trim())
  }
  const handleAbrirEditorPagoRevision = (pago: PagoConError) => {
    onOpenPagoEditor(pago)
  }
  const handleSiguienteAnomalia = () => {
    const candidatos = revisionRowsAnalizadas.filter(r => r.score > 0)
    if (candidatos.length === 0) {
      toast.info('No hay anomalías priorizadas en esta página.')
      return
    }
    const idxActual = candidatos.findIndex(r => r.pago.id === editingRevisionId)
    const siguiente =
      candidatos[(idxActual + 1 + candidatos.length) % candidatos.length]
    setEditingRevisionId(siguiente.pago.id)
    setRevisionObservacionDraft((siguiente.pago.observaciones ?? '').trim())
    onOpenPagoEditor(siguiente.pago)
    toast.success(
      `Abriendo anomalía ${idxActual >= 0 ? idxActual + 2 : 1}/${candidatos.length} (ID ${siguiente.pago.id})`
    )
  }
  const toggleRevisionSeleccion = (id: number) => {
    setSelectedRevisionIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }
  const toggleRevisionSeleccionTodas = () => {
    const visibles = revisionRowsFiltradas.map(r => r.pago.id)
    const todosSeleccionados =
      visibles.length > 0 && visibles.every(id => selectedRevisionIds.has(id))
    setSelectedRevisionIds(todosSeleccionados ? new Set() : new Set(visibles))
  }
  const handleGuardarRevisionMasivo = async () => {
    const ids = [...selectedRevisionIds]
    if (ids.length === 0) {
      toast.info('Seleccione al menos un pago.')
      return
    }
    setIsBulkSavingRevision(true)
    try {
      const respuestas = await Promise.all(
        ids.map(id =>
          pagoConErrorService.update(id, {
            observaciones: bulkRevisionObservacion.trim() || null,
          })
        )
      )
      const yaCargadoLimpiados = respuestas.filter(
        r =>
          r &&
          typeof r === 'object' &&
          'ya_cargado_eliminado' in r &&
          (r as { ya_cargado_eliminado?: boolean }).ya_cargado_eliminado ===
            true
      ).length
      const guardados = ids.length - yaCargadoLimpiados
      let mensaje = `Observación guardada en ${guardados} pago(s).`
      if (yaCargadoLimpiados > 0) {
        mensaje += ` 🧹 ${yaCargadoLimpiados} ya estaban cargado(s) y aplicado(s) en cartera: eliminados por redundancia.`
      }
      toast.success(mensaje, { duration: 6000 })
      setSelectedRevisionIds(new Set())
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setIsBulkSavingRevision(false)
    }
  }
  const handleEliminarRevisionMasivo = async () => {
    const ids = [...selectedRevisionIds]
    if (ids.length === 0) {
      toast.info('Seleccione al menos un pago.')
      return
    }
    if (!window.confirm(`¿Eliminar ${ids.length} pago(s) seleccionados?`))
      return

    // Invalidar caché para evitar mostrar viejo
    queryClient.removeQueries({
      queryKey: ['pagos-con-errores-tab'],
    })

    setIsBulkDeletingRevision(true)
    try {
      const resultados = await Promise.all(
        ids.map(id => eliminarPagoRevisionOConError({ idConError: id }))
      )
      const omitidos = resultados.filter(r => r === 'ya_ausente').length
      const eliminados = resultados.length - omitidos

      toast.success(
        omitidos > 0
          ? `✅ ${eliminados} pago(s) eliminados; ${omitidos} ya no estaban en revisión (procesados antes).`
          : `✅ ${eliminados} pago(s) eliminados de la BD`
      )
      setSelectedRevisionIds(new Set())

      // Refrescar tabla
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(`Error al eliminar: ${getErrorMessage(e)}`)

      // Refetch para sincronizar
      await refetchDiagnosticoRevision()
    } finally {
      setIsBulkDeletingRevision(false)
    }
  }
  const handleMoverRevisionMasivo = async () => {
    const ids = [...selectedRevisionIds]
    if (ids.length === 0) {
      toast.info('Seleccione al menos un pago.')
      return
    }
    const sinPrestamo = (revisionData?.pagos ?? []).filter(
      p => ids.includes(p.id) && !p.prestamo_id
    )
    if (sinPrestamo.length > 0) {
      toast.message(
        `${sinPrestamo.length} pago(s) sin préstamo asignado: se intentará vincular al único crédito APROBADO de la cédula; si hay varios o ninguno, edite la fila antes de reintentar.`,
        { duration: 7000 }
      )
    }
    setIsBulkMovingRevision(true)
    setBulkMovingProgress({ movidos: 0, total: ids.length })
    try {
      const result = await pagoConErrorService.moverAPagosNormales(ids)

      let mensaje = `✅ ${result.movidos} pago(s) movido(s) a tabla principal.\n💰 ${result.cuotas_aplicadas ?? 0} cuota(s) aplicada(s).`

      const yaCargadoCount = result.ya_cargado_eliminados_count ?? 0
      if (yaCargadoCount > 0) {
        mensaje += `\n🧹 ${yaCargadoCount} ya estaban cargado(s) en cartera y aplicado(s) a cuotas: eliminados de revisión por redundancia.`
      }

      if (result.errores && result.errores.length > 0) {
        mensaje += `\n⚠️ ${result.errores.length} error(es):\n${result.errores.join('\n')}`
        toast.warning(mensaje, { duration: 8000 })
      } else {
        toast.success(mensaje, { duration: 6000 })
      }

      setSelectedRevisionIds(new Set())
      setBulkMovingProgress({ movidos: 0, total: 0 })
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setIsBulkMovingRevision(false)
      setBulkMovingProgress({ movidos: 0, total: 0 })
    }
  }
  const abrirEscanerLoteConIds = useCallback((idsRaw: number[]) => {
    if (idsRaw.length === 0) {
      toast.info('Seleccione al menos un pago.')
      return false
    }
    const ids = idsRaw.slice(0, 10)
    if (idsRaw.length > 10) {
      toast.info('Solo se escanean 10 seleccionados por lote.')
    }
    const qs = new URLSearchParams({
      from: 'pagos',
      ids: ids.join(','),
    })
    const href = `${BASE_PATH}/escaner-lote?${qs.toString()}`.replace(
      /\/+/g,
      '/'
    )
    window.location.assign(href)
    return true
  }, [])
  const handleEscanearRevisionMasivo = () => {
    const ids = [...selectedRevisionIds]
    setIsBulkScanningRevision(true)
    try {
      abrirEscanerLoteConIds(ids)
    } finally {
      setIsBulkScanningRevision(false)
    }
  }
  /**
   * Limpia PagoConError redundantes con criterio estricto (mismo numero_documento canónico
   * + cuota_pagos aplicado + misma cédula y préstamo cuando el origen lo informa).
   * Si hay seleccionados, opera sobre ellos; si no, barre todos los pendientes.
   */
  const handleLimpiarYaCargados = async () => {
    const ids = [...selectedRevisionIds]
    const operaSobreSeleccion = ids.length > 0
    const confirmacion = operaSobreSeleccion
      ? `¿Eliminar de revisión los ${ids.length} pago(s) seleccionado(s) que ya estén cargados y aplicados a cuotas en cartera?`
      : '¿Barrer toda la lista de revisión y eliminar las filas cuyo pago ya esté cargado y aplicado a cuotas en cartera? El criterio es estricto: mismo Nº documento + cuota_pagos aplicado + misma cédula/préstamo.'
    if (!window.confirm(confirmacion)) return
    setIsLimpiandoYaCargados(true)
    try {
      const result = await pagoConErrorService.limpiarYaCargados(
        operaSobreSeleccion ? ids : undefined
      )
      let mensaje = `🧹 ${result.eliminados} eliminado(s) de revisión por estar ya cargado(s) en cartera.\nEvaluados: ${result.evaluados}.`
      if (result.errores && result.errores.length > 0) {
        mensaje += `\n⚠️ ${result.errores.length} error(es):\n${result.errores.join('\n')}`
        toast.warning(mensaje, { duration: 8000 })
      } else if (result.eliminados === 0) {
        toast.info(mensaje, { duration: 4000 })
      } else {
        toast.success(mensaje, { duration: 6000 })
      }
      if (operaSobreSeleccion) {
        const idsEliminados = new Set(
          (result.detalles || []).map(d => d.pago_con_error_id)
        )
        setSelectedRevisionIds(prev => {
          const next = new Set(prev)
          idsEliminados.forEach(id => next.delete(id))
          return next
        })
      } else {
        setSelectedRevisionIds(new Set())
      }
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setIsLimpiandoYaCargados(false)
    }
  }
  const handleBuscarRevisionPorCedula = () => {
    setRevisionCedulaFiltro(revisionCedulaInput.trim())
    setRevisionNumeroDocumentoFiltro(revisionNumeroDocumentoInput.trim())
    setRevisionFechaPagoFiltro('')
    setRevisionFechaPagoInput('')
    setRevisionTipoFiltro('')
    setRevisionMotivoFiltro('')
    setRevisionPage(1)
  }
  const handleLimpiarRevisionCedula = () => {
    setRevisionCedulaInput('')
    setRevisionCedulaFiltro('')
    setRevisionNumeroDocumentoInput('')
    setRevisionNumeroDocumentoFiltro('')
    setRevisionFechaPagoInput('')
    setRevisionFechaPagoFiltro('')
    setRevisionTipoFiltro('')
    setRevisionMotivoFiltro('')
    setRevisionPage(1)
  }
  const handleGuardarRevision = async (id: number) => {
    if (editingRevisionId !== id) return
    setSavingRevisionId(id)
    try {
      const resp = await pagoConErrorService.update(id, {
        observaciones: revisionObservacionDraft.trim() || null,
      })
      if (
        resp &&
        typeof resp === 'object' &&
        'ya_cargado_eliminado' in resp &&
        (resp as { ya_cargado_eliminado?: boolean }).ya_cargado_eliminado ===
          true
      ) {
        const info = resp as { pago_id: number; prestamo_id?: number | null }
        toast.success(
          `🧹 Este pago ya estaba cargado en cartera (pago #${info.pago_id}` +
            (info.prestamo_id != null
              ? `, préstamo #${info.prestamo_id}`
              : '') +
            ') y aplicado a cuotas. Se eliminó de revisión por redundancia.',
          { duration: 6500 }
        )
      } else {
        toast.success('Observación guardada')
      }
      setEditingRevisionId(null)
      setRevisionObservacionDraft('')
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setSavingRevisionId(null)
    }
  }
  const handleEliminarRevision = async (id: number) => {
    if (!window.confirm(`¿Eliminar el pago pendiente ID ${id}?`)) return

    // Invalidar caché para evitar mostrar viejo
    queryClient.removeQueries({
      queryKey: ['pagos-con-errores-tab'],
    })

    setDeletingRevisionId(id)
    try {
      const resultado = await eliminarPagoRevisionOConError({
        idConError: id,
      })
      toast.success(
        resultado === 'ya_ausente'
          ? 'El pago ya no estaba en revisión (probablemente ya fue procesado y movido a cartera).'
          : '✅ Pago pendiente eliminado de la BD'
      )

      // Refrescar tabla desde servidor
      await invalidatePagosPrestamosRevisionYCuotas(queryClient)
      await refetchDiagnosticoRevision()

      if ((revisionData?.pagos?.length ?? 0) <= 1 && revisionPage > 1) {
        setRevisionPage(prev => Math.max(1, prev - 1))
      }
    } catch (e) {
      toast.error(`Error al eliminar: ${getErrorMessage(e)}`)

      // Refetch para sincronizar en caso de error
      await refetchDiagnosticoRevision()
    } finally {
      setDeletingRevisionId(null)
    }
  }
  const handleEliminarBorradorPendiente = useCallback(
    async (id: string) => {
      if (
        !window.confirm('¿Eliminar este borrador con validación pendiente?')
      ) {
        return
      }
      setDeletingBorradorId(id)
      try {
        await deleteInfopagosBorradorEscaneer(id)
        toast.success('Borrador eliminado')
        await queryClient.invalidateQueries({
          queryKey: ['escaner-infopagos-borradores-pendientes'],
        })
      } catch (e) {
        toast.error(getErrorMessage(e))
      } finally {
        setDeletingBorradorId(null)
      }
    },
    [queryClient]
  )
  return {
    revisionCedulaInput,
    setRevisionCedulaInput,
    revisionNumeroDocumentoInput,
    setRevisionNumeroDocumentoInput,
    revisionCedulaFiltro,
    revisionNumeroDocumentoFiltro,
    includeRevisionExportados: includeExportados,
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
  }
}
