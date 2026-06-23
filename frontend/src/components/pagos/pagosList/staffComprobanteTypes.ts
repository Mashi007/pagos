export type StaffComprobanteListPreview = {
  open: boolean
  href: string
  label: string
  pagoId: number | null
  blobUrl: string | null
  contentType: string | null
  loading: boolean
  rotDeg: number
}

export const STAFF_COMPROBANTE_LIST_PREVIEW_CLOSED: StaffComprobanteListPreview =
  {
    open: false,
    href: '',
    label: '',
    pagoId: null,
    blobUrl: null,
    contentType: null,
    loading: false,
    rotDeg: 0,
  }
