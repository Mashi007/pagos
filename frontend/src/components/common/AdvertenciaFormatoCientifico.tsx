import React, { useState } from 'react';
import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Button } from '../../components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';

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
          Has confirmado que entiendes el problema del formato cientÃÂ­fico. 
          Los nÃÂºmeros se normalizarÃÂ¡n automÃÂ¡ticamente en futuras importaciones.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <>
      <Alert className="mb-4 border-yellow-200 bg-yellow-50">
        <AlertTriangle className="h-4 w-4 text-yellow-600" />
        <AlertTitle className="text-yellow-800">
          ÃÂ¢ÃÂ¡ ÃÂ¯ÃÂ¸ÃÂ Advertencia: Problema de Formato CientÃÂ­fico en NÃÂºmeros de Documento
        </AlertTitle>
        <AlertDescription className="text-yellow-700 space-y-2">
          <p>
            <strong>Problema detectado:</strong> Algunos nÃÂºmeros de documento estÃÂ¡n almacenados en formato cientÃÂ­fico 
            (ej: <code className="bg-yellow-100 px-1 rounded">7.40087E+14</code>), lo que oculta los ÃÂºltimos dÃÂ­gitos significativos.
          </p>
          <p>
            <strong>Impacto:</strong> Esto puede causar que nÃÂºmeros diferentes aparezcan como iguales, afectando la 
            reconciliaciÃÂ³n de pagos y la integridad de los datos.
          </p>
          <p>
            <strong>SoluciÃÂ³n implementada:</strong> El sistema ahora normaliza automÃÂ¡ticamente estos nÃÂºmeros en futuras 
            importaciones. Sin embargo, los datos existentes pueden requerir revisiÃÂ³n y correcciÃÂ³n manual.
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
              RevisiÃÂ³n y CorrecciÃÂ³n de Datos con Formato CientÃÂ­fico
            </DialogTitle>
            <div className="text-sm text-gray-600 mb-4">
              Puedes revisar y corregir los datos afectados usando las herramientas de ediciÃÂ³n disponibles.
            </div>
          </DialogHeader>

          <div className="space-y-4">
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <h4 className="font-semibold text-blue-900 mb-2">Herramientas Disponibles:</h4>
              <ul className="list-disc list-inside space-y-1 text-blue-800 text-sm">
                <li><strong>Editar Pagos:</strong> Puedes editar nÃÂºmeros de documento directamente desde la lista de pagos</li>
                <li><strong>Editar Cuotas:</strong> Revisa y corrige informaciÃÂ³n de cuotas si es necesario</li>
                <li><strong>Editar PrÃÂ©stamos:</strong> Verifica y actualiza datos de prÃÂ©stamos relacionados</li>
                <li><strong>Eliminar y Recrear:</strong> Si es necesario, puedes eliminar registros incorrectos y recrearlos con datos correctos</li>
              </ul>
            </div>

            <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
              <h4 className="font-semibold text-yellow-900 mb-2">ÃÂ¢ÃÂ¡ ÃÂ¯ÃÂ¸ÃÂ Importante:</h4>
              <ul className="list-disc list-inside space-y-1 text-yellow-800 text-sm">
                <li>Los nÃÂºmeros en formato cientÃÂ­fico se normalizan automÃÂ¡ticamente al guardar</li>
                <li>Si el nÃÂºmero original tenÃÂ­a mÃÂ¡s dÃÂ­gitos que los recuperables, estos se perderÃÂ¡n</li>
                <li>Revisa los archivos CSV/Excel originales para obtener los nÃÂºmeros completos si es posible</li>
                <li>Todos los cambios quedan registrados en la auditorÃÂ­a del sistema</li>
              </ul>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <h4 className="font-semibold text-gray-900 mb-2">Datos Afectados:</h4>
              <ul className="list-disc list-inside space-y-1 text-gray-800 text-sm">
                <li><strong>Pagos:</strong> NÃÂºmeros de documento en formato cientÃÂ­fico</li>
                <li><strong>Cuotas:</strong> InformaciÃÂ³n relacionada con pagos afectados</li>
                <li><strong>PrÃÂ©stamos:</strong> Datos de prÃÂ©stamos con pagos afectados</li>
                <li><strong>Tablas de AmortizaciÃÂ³n:</strong> Cuotas generadas para prÃÂ©stamos afectados</li>
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
