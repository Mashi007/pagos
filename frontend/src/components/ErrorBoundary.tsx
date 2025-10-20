// frontend/src/components/ErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error capturado por ErrorBoundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
          <div className="max-w-2xl w-full p-8 bg-white rounded-lg shadow-lg">
            <div className="text-center">
              <div className="mb-6">
                <div className="text-6xl mb-4">⚠️</div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                  Algo salió mal
                </h1>
                <p className="text-gray-600">
                  La aplicación encontró un error inesperado.
                </p>
              </div>

              <div className="flex gap-4 justify-center">
                <button 
                  onClick={() => window.location.reload()} 
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Recargar Página
                </button>
                <button 
                  onClick={() => window.location.href = '/'} 
                  className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                >
                  Ir al Inicio
                </button>
              </div>

              <p className="mt-4 text-sm text-gray-500">
                Si el problema persiste, contacte al administrador del sistema.
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
