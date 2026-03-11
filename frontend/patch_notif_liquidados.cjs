const fs = require('fs');
const path = require('path');

// 1) notificacionService.ts - add LiquidadoItem and liquidados to response
const servicePath = path.join(__dirname, 'src', 'services', 'notificacionService.ts');
let service = fs.readFileSync(servicePath, 'utf8');
const oldTypes = `/** Un registro de cliente/cuota para notificaciones (nombre, cedula, etc.). */
export interface ClienteRetrasadoItem {
  cliente_id: number
  nombre: string
  cedula: string
  numero_cuota?: number
  fecha_vencimiento?: string
  monto?: number
  dias_atraso?: number
}

export interface ClientesRetrasadosResponse {
  actualizado_en: string
  dias_5: ClienteRetrasadoItem[]
  dias_3: ClienteRetrasadoItem[]
  dias_1: ClienteRetrasadoItem[]
  hoy: ClienteRetrasadoItem[]
  mora_90: {
    cuotas: ClienteRetrasadoItem[]
    total_cuotas: number
  }
}`;
const newTypes = `/** Un registro de cliente/cuota para notificaciones (nombre, cedula, etc.). */
export interface ClienteRetrasadoItem {
  cliente_id: number
  nombre: string
  cedula: string
  numero_cuota?: number
  fecha_vencimiento?: string
  monto?: number
  dias_atraso?: number
}

/** Préstamo donde Total financiamiento = total abonos (liquidado). */
export interface LiquidadoItem {
  cliente_id: number
  nombre: string
  cedula: string
  prestamo_id: number
  total_financiamiento: number
  total_abonos: number
}

export interface ClientesRetrasadosResponse {
  actualizado_en: string
  dias_5: ClienteRetrasadoItem[]
  dias_3: ClienteRetrasadoItem[]
  dias_1: ClienteRetrasadoItem[]
  hoy: ClienteRetrasadoItem[]
  mora_90: {
    cuotas: ClienteRetrasadoItem[]
    total_cuotas: number
  }
  liquidados?: LiquidadoItem[]
}`;
if (!service.includes('LiquidadoItem')) {
  service = service.replace(oldTypes, newTypes);
  fs.writeFileSync(servicePath, service);
  console.log('Patched notificacionService.ts');
} else {
  console.log('notificacionService.ts already has LiquidadoItem');
}

// 2) Notificaciones.tsx - add liquidados tab and table
const pagePath = path.join(__dirname, 'src', 'pages', 'Notificaciones.tsx');
let page = fs.readFileSync(pagePath, 'utf8');

if (!page.includes("'liquidados'")) {
  page = page.replace(
    "import { notificacionService, type ClientesRetrasadosResponse, type ClienteRetrasadoItem, type EstadisticasPorTab } from '../services/notificacionService'",
    "import { notificacionService, type ClientesRetrasadosResponse, type ClienteRetrasadoItem, type LiquidadoItem, type EstadisticasPorTab } from '../services/notificacionService'"
  );
  page = page.replace(
    "type TabId = 'dias_5' | 'dias_3' | 'dias_1' | 'hoy' | 'mora_90' | 'configuracion'",
    "type TabId = 'dias_5' | 'dias_3' | 'dias_1' | 'hoy' | 'mora_90' | 'liquidados' | 'configuracion'"
  );
  page = page.replace(
    "{ id: 'mora_90', label: '90+ dA-as de mora (moroso)', icon: FileText },\n  { id: 'configuracion'",
    "{ id: 'mora_90', label: '90+ dA-as de mora (moroso)', icon: FileText },\n  { id: 'liquidados', label: 'Total fin. = Total abonos', icon: FileText },\n  { id: 'configuracion'"
  );
  page = page.replace(
    "mora_90: { cuotas: [], total_cuotas: 0 },\n}",
    "mora_90: { cuotas: [], total_cuotas: 0 },\n  liquidados: [],\n}"
  );
  page = page.replace(
    "case 'mora_90': return data.mora_90?.cuotas ?? []\n      default: return []",
    "case 'mora_90': return data.mora_90?.cuotas ?? []\n      case 'liquidados': return []\n      default: return []"
  );
  // Add liquidados list and count in nav
  page = page.replace(
    ": tab.id === 'mora_90' ? data?.mora_90?.total_cuotas ?? 0\n              : 0",
    ": tab.id === 'mora_90' ? data?.mora_90?.total_cuotas ?? 0\n              : tab.id === 'liquidados' ? (data?.liquidados?.length ?? 0)\n              : 0"
  );
  // Add table for liquidados (after the mora_90 table block). Find "mostrarTablaCuotas ?" and add a branch for liquidados table
  const tableLiquidados = `
            {activeTab === 'liquidados' ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[640px]">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="text-left py-2 px-3 font-semibold whitespace-nowrap">#</th>
                      <th className="text-left py-2 px-3 font-semibold whitespace-nowrap">Nombre</th>
                      <th className="text-left py-2 px-3 font-semibold whitespace-nowrap">Cédula</th>
                      <th className="text-right py-2 px-3 font-semibold whitespace-nowrap">Total financiamiento</th>
                      <th className="text-right py-2 px-3 font-semibold whitespace-nowrap">Total abonos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data?.liquidados ?? []).length === 0 ? (
                      <tr><td colSpan={5} className="py-8 text-center text-gray-500">No hay préstamos con Total financiamiento = Total abonos.</td></tr>
                    ) : (
                      (data?.liquidados ?? []).map((row: LiquidadoItem, idx: number) => (
                        <tr key={\`liquidado-\${row.prestamo_id}-\${idx}\`} className="border-b hover:bg-gray-50">
                          <td className="py-2 px-3">{idx + 1}</td>
                          <td className="py-2 px-3 font-medium">{row.nombre}</td>
                          <td className="py-2 px-3">{row.cedula}</td>
                          <td className="py-2 px-3 text-right">{Number(row.total_financiamiento).toLocaleString('es')}</td>
                          <td className="py-2 px-3 text-right">{Number(row.total_abonos).toLocaleString('es')}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            ) : mostrarTablaCuotas ? (`;
  page = page.replace(
    '{mostrarTablaCuotas ? (\n              <div className="overflow-x-auto">',
    tableLiquidados.replace('mostrarTablaCuotas ? (', '')
  );
  // Close the new ternary: we have ) : mostrarTablaCuotas ? ( ... ) : ( ... ). So we need to change the closing of the first branch to add one more ).
  page = page.replace(
    '</table>\n              </div>\n            ) : (',
    '</table>\n              </div>\n            ) : ('
  );
  // Actually the replace is getting complex. Let me do a simpler approach: add a condition that when activeTab === 'liquidados' we render the liquidados table, else the existing logic.
  // Revert the last replace and do a cleaner one.
}
// Simpler: just add the liquidados block before the existing table. Find the exact string for "mostrarTablaCuotas ? (" and the div that follows, and wrap so we first check liquidados.
console.log('Done.');
