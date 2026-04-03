/**
 * Mensajes alineados con backend: pagos desde reportes usan numero_operacion
 * como documento del pago cuando existe (Infopagos, import, Aprobar en Cobros).
 */
export const TEXTO_AVISO_NUMERO_OPERACION_FORMULARIO =
  'Use el numero que aparece en su comprobante (operacion, referencia o serial del banco). ' +
  'Ese dato es el documento del pago en sistema y el que usamos para evitar duplicados entre canales. ' +
  'El codigo RPC del recibo solo identifica su envio; no lo confunda con el comprobante bancario.'

export const TEXTO_AVISO_PAGOS_REPORTADOS_ADMIN =
  'Al pasar a la tabla Pagos se registra primero el numero de operacion del comprobante ' +
  '(mismo criterio que Infopagos y el import automatico). El RPC identifica el reporte; ' +
  'la clave frente a duplicados es el comprobante, no el RPC. ' +
  'Esta cola incluye Infopagos y el formulario publico del deudor: misma revision, aprobacion y reglas. ' +
  'Los reportes que no cumplen validadores siguen visibles aqui hasta que descargue el Excel de corrección; ' +
  'al descargarlo, salen de esta vista (puede marcar Incluir ya exportados para verlos de nuevo).'
