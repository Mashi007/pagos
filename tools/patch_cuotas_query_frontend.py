# Run from repo root: python tools/patch_cuotas_query_frontend.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_tabla() -> None:
    p = ROOT / "frontend/src/components/prestamos/TablaAmortizacionPrestamo.tsx"
    t = p.read_text(encoding="utf-8")
    needle = (
        "import { prestamoService } from '../../services/prestamoService'\n\n"
        "import { useQuery } from '@tanstack/react-query'"
    )
    if needle not in t:
        raise SystemExit("tabla: import needle not found")
    repl = (
        "import { prestamoService } from '../../services/prestamoService'\n\n"
        "import { cuotasPrestamoQueryKey } from '../../constants/queryKeys'\n\n"
        "import { useQuery } from '@tanstack/react-query'"
    )
    t = t.replace(needle, repl, 1)
    t = t.replace(
        "queryKey: ['cuotas-prestamo', prestamo.id],",
        "queryKey: cuotasPrestamoQueryKey(prestamo.id),",
        1,
    )
    t = t.replace("refetchOnMount: true,", "refetchOnMount: 'always',", 1)
    p.write_text(t, encoding="utf-8")
    print("patched", p.relative_to(ROOT))


def patch_modal() -> None:
    p = ROOT / "frontend/src/components/prestamos/PrestamoDetalleModal.tsx"
    t = p.read_text(encoding="utf-8")
    if "cuotasPrestamoQueryKey" in t:
        print("modal already patched")
        return
    old_import = "import { useQuery } from '@tanstack/react-query'"
    if old_import not in t:
        raise SystemExit("modal: useQuery import not found")
    new_import = (
        "import { useQuery, useQueryClient } from '@tanstack/react-query'\n\n"
        "import { cuotasPrestamoQueryKey } from '../../constants/queryKeys'"
    )
    t = t.replace(old_import, new_import, 1)
    old_fn = (
        "export function PrestamoDetalleModal({\n"
        "  prestamo: prestamoInitial,\n"
        "  onClose,\n"
        "}: PrestamoDetalleModalProps) {\n"
        "  const [activeTab, setActiveTab] = useState<'detalles' | 'amortizacion'>(\n"
        "    'detalles'\n"
        "  )"
    )
    new_fn = (
        "export function PrestamoDetalleModal({\n"
        "  prestamo: prestamoInitial,\n"
        "  onClose,\n"
        "}: PrestamoDetalleModalProps) {\n"
        "  const queryClient = useQueryClient()\n\n"
        "  const [activeTab, setActiveTab] = useState<'detalles' | 'amortizacion'>(\n"
        "    'detalles'\n"
        "  )"
    )
    if old_fn not in t:
        raise SystemExit("modal: function header not found")
    t = t.replace(old_fn, new_fn, 1)
    old_btn = (
        "              <button\n"
        "                onClick={() => setActiveTab('amortizacion')}\n"
        "                className={`border-b-2 px-4 py-3 transition-colors ${\n"
        "                  activeTab === 'amortizacion'\n"
        "                    ? 'border-blue-600 text-blue-600'\n"
        "                    : 'border-transparent text-gray-600 hover:text-gray-900'\n"
        "                }`}\n"
        "              >\n"
        "                Tabla de AmortizaciA3n\n"
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
        "                Tabla de AmortizaciA3n\n"
        "              </button>"
    )
    if old_btn not in t:
        raise SystemExit("modal: amortization button block not found")
    t = t.replace(old_btn, new_btn, 1)
    p.write_text(t, encoding="utf-8")
    print("patched", p.relative_to(ROOT))


def patch_pagos_list_refetch() -> None:
    """Tras invalidar cuotas, forzar refetch inmediato de queries activas."""
    p = ROOT / "frontend/src/components/pagos/PagosList.tsx"
    t = p.read_text(encoding="utf-8")
    needle = (
        "              await queryClient.invalidateQueries({\n"
        "                queryKey: ['cuotas-prestamo'],\n"
        "                exact: false,\n"
        "              })\n"
        "              await queryClient.invalidateQueries({\n"
        "                queryKey: ['prestamos'],\n"
        "                exact: false,\n"
        "              })\n"
        "              await queryClient.invalidateQueries({\n"
        "                queryKey: ['pagos-por-cedula'],\n"
        "                exact: false,\n"
        "              })\n"
        "              // Refetch inmediato de KPIs para actualizaciA3n en tiempo real"
    )
    if "refetchQueries({\n                queryKey: ['cuotas-prestamo']" in t:
        print("PagosList already has cuotas refetch")
        return
    if needle not in t:
        raise SystemExit("PagosList: onSuccess block not found")
    insert = (
        "              await queryClient.invalidateQueries({\n"
        "                queryKey: ['cuotas-prestamo'],\n"
        "                exact: false,\n"
        "              })\n"
        "              await queryClient.refetchQueries({\n"
        "                queryKey: ['cuotas-prestamo'],\n"
        "                exact: false,\n"
        "              })\n"
        "              await queryClient.invalidateQueries({\n"
        "                queryKey: ['prestamos'],\n"
        "                exact: false,\n"
        "              })\n"
        "              await queryClient.invalidateQueries({\n"
        "                queryKey: ['pagos-por-cedula'],\n"
        "                exact: false,\n"
        "              })\n"
        "              // Refetch inmediato de KPIs para actualizaciA3n en tiempo real"
    )
    t = t.replace(needle, insert, 1)
    p.write_text(t, encoding="utf-8")
    print("patched PagosList onSuccess refetch cuotas")


if __name__ == "__main__":
    patch_tabla()
    patch_modal()
    patch_pagos_list_refetch()
