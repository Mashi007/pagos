import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, Trash2, RefreshCw } from 'lucide-react';

const API_URL = process.env.REACT_APP_API_URL || 'https://pagos-backend-ov5f.onrender.com/api/v1';

interface PrestamoConError {
  id: number;
  cedula_cliente: string;
  total_financiamiento: string;
  modalidad_pago: string;
  numero_cuotas: number;
  producto: string;
  analista: string;
  concesionario: string;
  errores: string;
  fila_origen: number;
  estado: string;
  fecha_registro: string;
}

export const PrestamosConErroresTable: React.FC = () => {
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['prestamos-con-errores', page, perPage],
    queryFn: async () => {
      const response = await fetch(
        `${API_URL}/prestamos/revisar/lista?page=${page}&per_page=${perPage}`,
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

  const deleteMutation = useMutation({
    mutationFn: async (errorId: number) => {
      const response = await fetch(`${API_URL}/prestamos/revisar/${errorId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      });
      if (!response.ok) throw new Error('Failed to delete');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prestamos-con-errores'] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-spin w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 rounded-lg border border-red-200 text-red-800">
        Error al cargar préstamos con errores
      </div>
    );
  }

  if (!data?.items || data.items.length === 0) {
    return (
      <div className="p-8 text-center bg-gray-50 rounded-lg border border-gray-200">
        <div className="text-gray-500">No hay préstamos con errores</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-yellow-600" />
          Revisar préstamos ({data.total || 0})
        </h2>
        <button
          onClick={() => refetch()}
          className="p-2 hover:bg-gray-100 rounded transition-colors"
        >
          <RefreshCw className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Tabla */}
      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Fila</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Cédula</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Monto</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Modalidad</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Cuotas</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Analista</th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">Errores</th>
              <th className="px-4 py-3 text-center font-semibold text-gray-700">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item: PrestamoConError, idx: number) => (
              <tr key={item.id} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td className="px-4 py-3 text-gray-600">{item.fila_origen}</td>
                <td className="px-4 py-3 font-mono text-gray-800">{item.cedula_cliente || '-'}</td>
                <td className="px-4 py-3 text-gray-800 font-semibold">
                  {item.total_financiamiento ? `$${parseFloat(item.total_financiamiento).toFixed(2)}` : '-'}
                </td>
                <td className="px-4 py-3 text-gray-600">{item.modalidad_pago || '-'}</td>
                <td className="px-4 py-3 text-center text-gray-600">{item.numero_cuotas || '-'}</td>
                <td className="px-4 py-3 text-gray-600 text-xs">{item.analista || '-'}</td>
                <td className="px-4 py-3">
                  <div className="max-w-xs">
                    <p className="text-xs text-red-700 break-words">
                      {item.errores?.substring(0, 80)}
                      {item.errores && item.errores.length > 80 ? '...' : ''}
                    </p>
                  </div>
                </td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => deleteMutation.mutate(item.id)}
                    disabled={deleteMutation.isPending}
                    className="p-2 hover:bg-red-100 rounded transition-colors disabled:opacity-50"
                    title="Eliminar"
                  >
                    <Trash2 className="w-4 h-4 text-red-600" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      {data.total > perPage && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-4 py-2 border rounded hover:bg-gray-100 disabled:opacity-50 text-sm"
          >
            Anterior
          </button>
          <span className="px-4 py-2 text-sm text-gray-600">
            Página {page} de {Math.ceil(data.total / perPage)}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page >= Math.ceil(data.total / perPage)}
            className="px-4 py-2 border rounded hover:bg-gray-100 disabled:opacity-50 text-sm"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  );
};
