from pathlib import Path

path = Path(__file__).resolve().parents[1] / "src" / "components" / "pagos" / "PagosList.tsx"
text = path.read_text(encoding="utf-8")

old_imp = """} from '../../utils/comprobanteImagenAuth'

type StaffComprobanteListPreview"""
new_imp = """} from '../../utils/comprobanteImagenAuth'
import {
  GMAIL_METRICS_SNAPSHOT_KEY,
  observacionesConMarcaDuplicadoCartera,
  pagoElegibleConciliarAplicar,
  pagoEstaCerradoSoloConsulta,
} from './pagosList/pagosListUtils'
import { ReemplazarPagosDialog } from './pagosList/ReemplazarPagosDialog'
import { StaffComprobanteDock } from './pagosList/StaffComprobanteDock'
import { useStaffComprobantePreview } from './pagosList/useStaffComprobantePreview'

type _RemovedStaffComprobanteListPreview"""
if old_imp not in text:
    raise SystemExit("import anchor not found")
text = text.replace(old_imp, new_imp, 1)

start = text.find("type _RemovedStaffComprobanteListPreview")
end = text.find("export function PagosList()")
if start < 0 or end < 0:
    raise SystemExit("block markers not found")
text = text[:start] + text[end:]

marker_start = "  const [lgViewport, setLgViewport] = useState(false)"
marker_end = "  const dockStaffComprobante = staffComprobantePreview.open && lgViewport\n\n  const sincronizarPendientesRevision"
if marker_start not in text:
    raise SystemExit("lg viewport block not found")
i = text.find(marker_start)
j = text.find(marker_end)
if j < 0:
    raise SystemExit("end marker not found")
replacement = """  const {
    staffComprobantePreview,
    setStaffComprobantePreview,
    closeStaffComprobanteListPreview,
    openStaffComprobanteForList,
    dockStaffComprobante,
  } = useStaffComprobantePreview()

  const sincronizarPendientesRevision"""
text = text[:i] + replacement + text[j + len(marker_end) :]

dock_start = '      {dockStaffComprobante ? (\n        <aside className="flex min-h-[min(36vh,320px)]'
dock_end = "      ) : null}\n\n      <div\n        className={cn(\n          dockStaffComprobante &&"
i = text.find(dock_start)
j = text.find(dock_end)
if i < 0 or j < 0:
    raise SystemExit(f"dock block not found {i} {j}")
dock_new = """      {dockStaffComprobante ? (
        <StaffComprobanteDock
          preview={staffComprobantePreview}
          onClose={closeStaffComprobanteListPreview}
          onRotate={delta =>
            setStaffComprobantePreview(prev => ({
              ...prev,
              rotDeg: (prev.rotDeg + delta + 360) % 360,
            }))
          }
        />
      ) : null}

      <div
        className={cn(
          dockStaffComprobante &&"""
text = text[:i] + dock_new + text[j + len(dock_end) :]

dlg_start = "        <Dialog\n          open={reemplazarPagosOpen}"
dlg_end = "        </Dialog>\n        {/* Después de importar desde Cobros"
i = text.find(dlg_start)
j = text.find(dlg_end)
if i < 0 or j < 0:
    raise SystemExit(f"dialog block not found {i} {j}")
dlg_new = """        <ReemplazarPagosDialog
          open={reemplazarPagosOpen}
          step={reemplazarStep}
          cedula={cedulaReemplazo}
          prestamos={prestamosReemplazo}
          prestamoId={prestamoIdReemplazo}
          prestamoSeleccionado={prestamoReemplazoSeleccionado}
          loading={loadingReemplazo}
          onOpenChange={open => {
            if (!open) cerrarReemplazarPagos()
          }}
          onCedulaChange={setCedulaReemplazo}
          onPrestamoIdChange={setPrestamoIdReemplazo}
          onStepChange={setReemplazarStep}
          onBuscarPrestamos={handleBuscarPrestamosReemplazo}
          onConfirmar={handleConfirmarReemplazarPagos}
        />
        {/* Después de importar desde Cobros"""
text = text[:i] + dlg_new + text[j + len(dlg_end) :]

path.write_text(text, encoding="utf-8")
print("PagosList patched, lines:", text.count("\n") + 1)
