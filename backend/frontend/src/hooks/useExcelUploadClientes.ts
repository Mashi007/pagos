import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'https://pagos-backend-ov5f.onrender.com/api/v1';

export interface UploadClientesResult {
  registros_creados: number;
  registros_con_error: number;
  mensaje: string;
}

export const useExcelUploadClientes = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadClientesResult | null>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      setIsLoading(true);
      setError(null);
      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_URL}/clientes/upload-excel`, {
          method: 'POST',
          body: formData,
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
          },
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Upload failed: ${response.statusText}`);
        }

        const data = await response.json();
        setResult(data);
        return data;
      } catch (err: any) {
        const errorMsg = err.message || 'Error uploading file';
        setError(errorMsg);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientes'] });
    },
  });

  const reset = () => {
    setError(null);
    setResult(null);
    uploadMutation.reset();
  };

  return {
    uploadFile: (file: File) => uploadMutation.mutate(file),
    isLoading: isLoading || uploadMutation.isPending,
    error: error || uploadMutation.error?.message,
    result,
    reset,
    isPending: uploadMutation.isPending,
  };
};
