from pathlib import Path

p = Path(__file__).resolve().parent / "src/components/prestamos/PrestamoDetalleModal.tsx"
t = p.read_text(encoding="utf-8")
if "cuotasPrestamoQueryKey" in t:
    print("already patched")
    raise SystemExit(0)
t = t.replace(
    "import { useQuery } from '@tanstack/react-query'",
    "import { useQuery, useQueryClient } from '@tanstack/react-query'\n\n"
    "import { cuotasPrestamoQueryKey } from '../../constants/queryKeys'",
    1,
)
t = t.replace(
    "export function PrestamoDetalleModal({\n"
    "  prestamo: prestamoInitial,\n"
    "  onClose,\n"
    "}: PrestamoDetalleModalProps) {\n"
    "  const [activeTab, setActiveTab] = useState<'detalles' | 'amortizacion'>(\n"
    "    'detalles'\n"
    "  )",
    "export function PrestamoDetalleModal({\n"
    "  prestamo: prestamoInitial,\n"
    "  onClose,\n"
    "}: PrestamoDetalleModalProps) {\n"
    "  const queryClient = useQueryClient()\n\n"
    "  const [activeTab, setActiveTab] = useState<'detalles' | 'amortizacion'>(\n"
    "    'detalles'\n"
    "  )",
    1,
)
old_btn = (
    "              <button\n"
    "                onClick={() => setActiveTab('amortizacion')}\n"
    "                className={`border-b-2 px-4 py-3 transition-colors ${\n"
    "                  activeTab === 'amortizacion'\n"
    "                    ? 'border-blue-600 text-blue-600'\n"
    "                    : 'border-transparent text-gray-600 hover:text-gray-900'\n"
    "                }`}\n"
    "              >\n"
    "                Tabla de Amortización\n"
    "              </button>"
)
new_btn = (
    "              <button\n"
    "                type=\"button\"\n"
    "                onClick={() => {\n"
    "                  const pid = prestamoInitial.id\n"
    "                  void queryClient.invalidateQueries({\n"
    "                    queryKey: cuotasPrestamoQueryKey(pid),\n"
    "                  })\n"
    "                  void queryClient.refetchQueries({\n"
    "                    queryKey: cuotasPrestamoQueryKey(pid),\n"
    "                  })\n"
    "                  setActiveTab('amortizacion')\n"
    "                }}\n"
    "                className={`border-b-2 px-4 py-3 transition-colors ${\n"
    "                  activeTab === 'amortizacion'\n"
    "                    ? 'border-blue-600 text-blue-600'\n"
    "                    : 'border-transparent text-gray-600 hover:text-gray-900'\n"
    "                }`}\n"
    "              >\n"
    "                Tabla de Amortización\n"
    "              </button>"
)
if old_btn not in t:
    raise SystemExit("button block not found")
t = t.replace(old_btn, new_btn, 1)
p.write_text(t, encoding="utf-8")
print("patched modal")
