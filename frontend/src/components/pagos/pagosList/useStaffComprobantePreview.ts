import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { getErrorMessage } from '../../../types/errors'
import {
  abrirStaffComprobanteDesdeHref,
  esUrlComprobanteImagenConAuth,
  fetchStaffComprobanteBlobWithDisplayMime,
} from '../../../utils/comprobanteImagenAuth'
import {
  STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED,
  type StaffComprobanteListPreview,
} from './staffComprobanteTypes'

export function useStaffComprobantePreview() {
  const [lgViewport, setLgViewport] = useState(false)
  const [staffComprobantePreview, setStaffComprobantePreview] =
    useState<StaffComprobanteListPreview>(STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const mq = window.matchMedia('(min-width: 1024px)')
    const apply = () => setLgViewport(mq.matches)
    apply()
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [])

  useEffect(() => {
    if (!lgViewport && staffComprobantePreview.open) {
      setStaffComprobantePreview(prev => {
        if (prev.blobUrl) URL.revokeObjectURL(prev.blobUrl)
        return STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED
      })
    }
  }, [lgViewport, staffComprobantePreview.open])

  useEffect(() => {
    return () => {
      if (staffComprobantePreview.blobUrl) {
        URL.revokeObjectURL(staffComprobantePreview.blobUrl)
      }
    }
  }, [staffComprobantePreview.blobUrl])

  const closeStaffComprobanteListPreview = useCallback(() => {
    setStaffComprobantePreview(prev => {
      if (prev.blobUrl) URL.revokeObjectURL(prev.blobUrl)
      return STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED
    })
  }, [])

  const openStaffComprobanteForList = useCallback(
    async (href: string, label: string, pagoId: number | null) => {
      const u = String(href || '').trim()
      if (!u) {
        toast.error('No hay comprobante o recibo asociado.')
        return
      }
      if (!esUrlComprobanteImagenConAuth(u)) {
        await abrirStaffComprobanteDesdeHref(u)
        return
      }
      if (!lgViewport) {
        await abrirStaffComprobanteDesdeHref(u)
        return
      }
      setStaffComprobantePreview(prev => {
        if (prev.blobUrl) URL.revokeObjectURL(prev.blobUrl)
        return {
          ...STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED,
          open: true,
          href: u,
          label,
          pagoId,
          loading: true,
        }
      })
      try {
        const { blob, contentType } =
          await fetchStaffComprobanteBlobWithDisplayMime(u)
        const blobUrl = URL.createObjectURL(blob)
        setStaffComprobantePreview(prev => ({
          ...prev,
          blobUrl,
          contentType,
          loading: false,
          rotDeg: 0,
        }))
      } catch (e) {
        toast.error(getErrorMessage(e) || 'No se pudo cargar el comprobante.')
        setStaffComprobantePreview(prev => {
          if (prev.blobUrl) URL.revokeObjectURL(prev.blobUrl)
          return STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED
        })
      }
    },
    [lgViewport]
  )

  const dockStaffComprobante = staffComprobantePreview.open && lgViewport

  return {
    staffComprobantePreview,
    setStaffComprobantePreview,
    closeStaffComprobanteListPreview,
    openStaffComprobanteForList,
    dockStaffComprobante,
  }
}
