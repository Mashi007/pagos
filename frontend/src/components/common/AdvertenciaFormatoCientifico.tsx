import React, { useState } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertTriangle, X, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface AdvertenciaFormatoCientificoProps {
  onConfirmar?: () => void;
  onRevisar?: () => void;
  mostrarDialog?: boolean;
  onCerrarDialog?: () => void;
}

export const AdvertenciaFormatoCientifico: React.FC<AdvertenciaFormatoCientificoProps> = ({
  onConfirmar,
  onRevisar,
  mostrarDialog = false,
  onCerrarDialog,
}) => {
  const [mostrarDialogo, setMostrarDialogo] = useState(mostrarDialog);
  const [confirmado, setConfirmado] = useState(false);

  const handleConfirmar = () => {
    setConfirmado(true);
    setMostrarDialogo(false);
    onConfirmar?.();
    onCerrarDialog?.();
  };

  const handleRevisar = () => {
    setMostrarDialogo(true);
    onRevisar?.();
  };

  const handleCerrar = () => {
    setMostrarDialogo(false);
    onCerrarDialog?.();
  };

  if (confirmado) {
    return (
      <Alert className="mb-4 border-green-200 bg-green-50">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
        <AlertTitle className="text-green-800">Advertencia revisada</AlertTitle>
        <AlertDescription className="text-green-700">
          Has confirmado que entiendes el problema del formato científico. 
          Los números se normalizarán automáticamente en futuras importaciones.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <>
      <Alert className="mb-4 border-yellow-200 bg-yellow-50">
        <AlertTriangle className="h-4 w-4 text-yellow-600" />
        <AlertTitle className="text-yellow-800">
          ⚠️ Advertencia: Problema de Formato Científico en Números de Documento
        </AlertTitle>
        <AlertDescription className="text-yellow-700 space-y-2">
          <p>
            <strong>Problema detectado:</strong> Algunos números de documento están almacenados en formato científico 
            (ej: <code className="bg-yellow-100 px-1 rounded">7.40087E+14</code>), lo que oculta los últimos dígitos significativos.
          </p>
          <p>
            <strong>Impacto:</strong> Esto puede causar que números diferentes aparezcan como iguales, afectando la 
            reconciliación de pagos y la integridad de los datos.
          </p>
          <p>
            <strong>Solución implementada:</strong> El sistema ahora normaliza automáticamente estos números en futuras 
            importaciones. Sin embargo, los datos existentes pueden requerir revisión y corrección manual.
          </p>
          <div className="flex gap-2 mt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRevisar}
              className="border-yellow-600 text-yellow-700 hover:bg-yellow-100"
            >
              Revisar y Corregir Datos
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleConfirmar}
              className="border-green-600 text-green-700 hover:bg-green-100"
            >
              Entendido, Continuar
            </Button>
          </div>
        </AlertDescription>
      </Alert>

      <Dialog open={mostrarDialogo} onOpenChange={setMostrarDialogo}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              Revisión y Corrección de Datos con Formato Científico
            </DialogTitle>
            <div className="text-sm text-gray-600 mb-4">
              Puedes revisar y corregir los datos afectados usando las herramientas de edición disponibles.
            </div>
          </DialogHeader>

          <div className="space-y-4">
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <h4 className="font-semibold text-blue-900 mb-2">Herramientas Disponibles:</h4>
              <ul className="list-disc list-inside space-y-1 text-blue-800 text-sm">
                <li><strong>Editar Pagos:</strong> Puedes editar números de documento directamente desde la lista de pagos</li>
                <li><strong>Editar Cuotas:</strong> Revisa y corrige información de cuotas si es necesario</li>
                <li><strong>Editar Préstamos:</strong> Verifica y actualiza datos de préstamos relacionados</li>
                <li><strong>Eliminar y Recrear:</strong> Si es necesario, puedes eliminar registros incorrectos y recrearlos con datos correctos</li>
              </ul>
            </div>

            <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
              <h4 className="font-semibold text-yellow-900 mb-2">⚠️ Importante:</h4>
              <ul className="list-disc list-inside space-y-1 text-yellow-800 text-sm">
                <li>Los números en formato científico se normalizan automáticamente al guardar</li>
                <li>Si el número original tenía más dígitos que los recuperables, estos se perderán</li>
                <li>Revisa los archivos CSV/Excel originales para obtener los números completos si es posible</li>
                <li>Todos los cambios quedan registrados en la auditoría del sistema</li>
              </ul>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <h4 className="font-semibold text-gray-900 mb-2">Datos Afectados:</h4>
              <ul className="list-disc list-inside space-y-1 text-gray-800 text-sm">
                <li><strong>Pagos:</strong> Números de documento en formato científico</li>
                <li><strong>Cuotas:</strong> Información relacionada con pagos afectados</li>
                <li><strong>Préstamos:</strong> Datos de préstamos con pagos afectados</li>
                <li><strong>Tablas de Amortización:</strong> Cuotas generadas para préstamos afectados</li>
              </ul>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleCerrar}>
              Cerrar
            </Button>
            <Button onClick={handleConfirmar} className="bg-green-600 hover:bg-green-700">
              Entendido, Continuar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AdvertenciaFormatoCientifico;
