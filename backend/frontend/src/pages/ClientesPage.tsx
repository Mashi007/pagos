import React, { useState } from 'react';
import { Plus, FileUp, AlertCircle } from 'lucide-react';
import { ExcelUploaderClientesUI } from '@/components/clientes/ExcelUploaderClientesUI';
import { ClientesConErroresTable } from '@/components/clientes/ClientesConErroresTable';
import { useQuery } from '@tanstack/react-query';

const API_URL = process.env.REACT_APP_API_URL || 'https://pagos-backend-ov5f.onrender.com/api/v1';

interface Cliente {
  id: number;
  cedula: string;
  nombres: string;
  email: string;
  telefono: string;
  estado: string;
  fecha_registro: string;
}

export const ClientesPage: React.FC = () => {
  const [view, setView] = useState<'lista' | 'nueva' | 'revisar'>('lista');
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);

  const { data: clientesData, isLoading, refetch } = useQuery({
    queryKey: ['clientes', page, perPage],
    queryFn: async () => {
      const response = await fetch(
        `${API_URL}/clientes?page=${page}&per_page=${perPage}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
          },
        }
      );
      if (!response.ok) throw new Error('Failed to fetch');
      return response.json();
    },
  });

  const handleNewClientoClick = () => {
    setView('nueva');
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Clientes</h1>
          
          {/* Botón Nuevo Cliente (dropdown) */}
          <div className="relative group">
            <button
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              <Plus className="w-5 h-5" />
              Nuevo Cliente
              <ChevronDown className="w-4 h-4 ml-1" />
            </button>

            {/* Dropdown Menu */}
            <div className="absolute right-0 top-full mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto transition-opacity z-10">
              <button
                onClick={() => {
                  setView('nueva');
                  setShowUploadDialog(false);
                }}
                className="w-full text-left px-4 py-3 hover:bg-blue-50 flex items-center gap-2 text-gray-700 hover:text-blue-600 border-b border-gray-100"
              >
                <Plus className="w-4 h-4" />
                Crear cliente manual
              </button>
              <button
                onClick={() => {
                  setShowUploadDialog(true);
                }}
                className="w-full text-left px-4 py-3 hover:bg-blue-50 flex items-center gap-2 text-gray-700 hover:text-blue-600"
              >
                <FileUp className="w-4 h-4" />
                Cargar desde Excel
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b border-gray-200">
          <button
            onClick={() => setView('lista')}
            className={`px-4 py-2 font-medium transition-colors ${
              view === 'lista'
                ? 'text-blue-600 border-b-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Todos ({clientesData?.total || 0})
          </button>
          <button
            onClick={() => setView('revisar')}
            className={`px-4 py-2 font-medium transition-colors flex items-center gap-2 ${
              view === 'revisar'
                ? 'text-yellow-600 border-b-2 border-yellow-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <AlertCircle className="w-4 h-4" />
            Con errores
          </button>
        </div>

        {/* Upload Dialog Modal */}
        {showUploadDialog && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-auto">
              <ExcelUploaderClientesUI
                onClose={() => setShowUploadDialog(false)}
                onSuccess={() => {
                  setShowUploadDialog(false);
                  refetch();
                }}
              />
            </div>
          </div>
        )}

        {/* Contenido según vista */}
        {view === 'lista' && (
          <div className="bg-white rounded-lg shadow">
            {isLoading ? (
              <div className="flex justify-center py-8">
                <div className="animate-spin w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full" />
              </div>
            ) : !clientesData?.items || clientesData.items.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                No hay clientes registrados
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="px-6 py-3 text-left font-semibold text-gray-700">
                        Cédula
                      </th>
                      <th className="px-6 py-3 text-left font-semibold text-gray-700">
                        Nombres
                      </th>
                      <th className="px-6 py-3 text-left font-semibold text-gray-700">
                        Email
                      </th>
                      <th className="px-6 py-3 text-left font-semibold text-gray-700">
                        Teléfono
                      </th>
                      <th className="px-6 py-3 text-left font-semibold text-gray-700">
                        Estado
                      </th>
                      <th className="px-6 py-3 text-center font-semibold text-gray-700">
                        Acciones
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {clientesData.items.map((cliente: Cliente, idx: number) => (
                      <tr
                        key={cliente.id}
                        className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                      >
                        <td className="px-6 py-3 font-mono text-gray-800">
                          {cliente.cedula}
                        </td>
                        <td className="px-6 py-3 text-gray-800">
                          {cliente.nombres}
                        </td>
                        <td className="px-6 py-3 text-gray-600 text-xs">
                          {cliente.email}
                        </td>
                        <td className="px-6 py-3 text-gray-600">
                          {cliente.telefono}
                        </td>
                        <td className="px-6 py-3">
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium ${
                              cliente.estado === 'ACTIVO'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {cliente.estado}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-center">
                          <button className="text-blue-600 hover:text-blue-800 font-medium text-sm">
                            Ver
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {view === 'revisar' && (
          <div className="bg-white rounded-lg shadow p-6">
            <ClientesConErroresTable />
          </div>
        )}
      </div>
    </div>
  );
};

// Helper component for chevron icon
const ChevronDown: React.FC<{ className: string }> = ({ className }) => (
  <svg
    className={className}
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M19 14l-7 7m0 0l-7-7m7 7V3"
    />
  </svg>
);
