/**
 * Mensajes alineados con backend: pagos desde reportes usan numero_operacion
 * como documento del pago cuando existe (Infopagos, import, Aprobar en Cobros).
 */
export const TEXTO_AVISO_NUMERO_OPERACION_FORMULARIO =
  'Use el numero que aparece en su comprobante (operacion, referencia o serial del banco). ' +
  'Ese dato es el documento del pago en sistema y el que usamos para evitar duplicados entre canales. ' +
  'El codigo RPC del recibo solo identifica su envio; no lo confunda con el comprobante bancario.'
