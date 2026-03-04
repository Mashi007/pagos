import React, { useRef, useState } from 'react';
import { Upload, FileX, CheckCircle2, AlertCircle } from 'lucide-react';
import { useExcelUploadClientes } from '@/hooks/useExcelUploadClientes';
import { toast } from 'sonner';

export const ExcelUploaderClientesUI: React.FC<{
  onClose?: () => void;
  onSuccess?: () => void;
}> = ({ onClose, onSuccess }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { uploadFile, isLoading, error, result, reset } = useExcelUploadClientes();
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileSelect = async (file: File) => {
    if (!file.name.match(/\.(xlsx|xls)$/i)) {
      toast.error('Por favor, suba un archivo Excel (.xlsx o .xls)');
      return;
    }

    uploadFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg border border-gray-200">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <Upload className="w-6 h-6 text-blue-600" />
          Carga masiva de clientes
        </h2>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            ×
          </button>
        )}
      </div>

      {/* Información sobre el formato */}
      <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <h3 className="font-semibold text-blue-900 mb-2">Formato requerido:</h3>
        <p className="text-sm text-blue-800">
          Cédula | Nombres | Dirección | Fecha Nacimiento | Ocupación | Correo | Teléfono
        </p>
        <p className="text-xs text-blue-700 mt-2">
          • Cédula: V|E|J|Z + 6-11 dígitos | • Email: formato válido y único | • Teléfono: requerido
        </p>
      </div>

      {/* Zona de carga */}
      {!result ? (
        <div
          onDrop={handleDrop}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragOver
              ? 'border-blue-600 bg-blue-50'
              : 'border-gray-300 bg-gray-50 hover:border-blue-400'
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={handleChange}
            className="hidden"
            disabled={isLoading}
          />

          <div className="flex flex-col items-center gap-3">
            <Upload className="w-12 h-12 text-gray-400" />
            <div>
              <p className="font-semibold text-gray-700">
                {isDragOver
                  ? 'Suelte el archivo aquí'
                  : 'Arrastra tu archivo Excel aquí o haz clic'}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Formatos soportados: .xlsx, .xls
              </p>
            </div>
          </div>
        </div>
      ) : null}

      {/* Resultado de carga */}
      {result && !error && (
        <div className="mt-6 p-6 bg-green-50 rounded-lg border border-green-200">
          <div className="flex items-start gap-4">
            <CheckCircle2 className="w-6 h-6 text-green-600 mt-1 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-semibold text-green-900 mb-2">
                Carga completada
              </h3>
              <div className="space-y-1 text-sm text-green-800">
                <p>✓ Clientes creados: <span className="font-bold">{result.registros_creados}</span></p>
                {result.registros_con_error > 0 && (
                  <p>⚠️ Con errores: <span className="font-bold text-yellow-700">{result.registros_con_error}</span></p>
                )}
                <p className="mt-3 text-xs text-green-700">{result.mensaje}</p>
              </div>
              <div className="flex gap-3 mt-4">
                <button
                  onClick={() => {
                    reset();
                    onSuccess?.();
                  }}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors text-sm font-medium"
                >
                  Listo
                </button>
                {result.registros_con_error > 0 && (
                  <a
                    href="/clientes/revisar"
                    className="px-4 py-2 bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200 transition-colors text-sm font-medium"
                  >
                    Ver clientes con error
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Errores */}
      {error && (
        <div className="mt-6 p-4 bg-red-50 rounded-lg border border-red-200">
          <div className="flex items-start gap-3">
            <FileX className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-semibold text-red-900">Error</p>
              <p className="text-sm text-red-800 mt-1">{error}</p>
              <button
                onClick={() => {
                  reset();
                  fileInputRef.current?.click();
                }}
                className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors text-sm font-medium"
              >
                Reintentar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Estado de carga */}
      {isLoading && (
        <div className="mt-6 flex items-center justify-center gap-3 p-4 bg-blue-50 rounded-lg">
          <div className="animate-spin w-5 h-5 border-3 border-blue-200 border-t-blue-600 rounded-full" />
          <span className="text-blue-800 font-medium">Cargando...</span>
        </div>
      )}
    </div>
  );
};
