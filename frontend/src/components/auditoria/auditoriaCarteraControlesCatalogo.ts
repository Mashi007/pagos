/**
 * Orden fijo igual a backend `prestamo_cartera_auditoria.py` (add_control).
 * Sirve para numerar y filtrar por control en la UI.
 */
export const AUDITORIA_CARTERA_CONTROLES_CATALOGO: ReadonlyArray<{
  n: number
  codigo: string
  titulo: string
  /** Texto corto de accion sugerida (solo UI). */
  notaOperativa?: string
}> = [
  {
    n: 1,
    codigo: 'cedula_cliente_vs_prestamo',
    titulo: 'Cedula cliente vs prestamo (API alinea al guardar)',
  },
  {
    n: 2,
    codigo: 'prestamos_duplicados_misma_cedula',
    titulo:
      'Prestamos APROBADO misma cedula por encima del cupo (E/V max 1, J max 5)',
  },
  {
    n: 3,
    codigo: 'cupo_cedula_aprobados_politica',
    titulo:
      'Cupo cedula: E/V max 1 APROBADO, J max 5 APROBADO, prefijos validos E V J',
  },
  {
    n: 4,
    codigo: 'prestamos_duplicados_nombre_cedula_fecha_registro',
    titulo: 'Prestamos duplicados (mismo nombre, cedula y fecha de registro)',
  },
  {
    n: 5,
    codigo: 'pagos_mismo_dia_monto',
    titulo: 'Pagos duplicados (misma fecha y monto)',
    notaOperativa:
      'El conteo es por prestamo afectado. Banco Mercantil u otros sin serie de documento: admin puede usar Visto (icono) para anexar sufijo _A#### o _P#### (A mismo credito/cuotas, P si el documento choca con otro prestamo) al Nº documento, registrar auditoria y excluir ese pago del control. SQL: backend/sql/control_5_pagos_duplicados_misma_fecha_monto.sql. Si es duplicado real, anular/unificar y reaplicar cascada.',
  },
  {
    n: 6,
    codigo: 'pagos_monto_no_positivo',
    titulo: 'Pagos con monto cero o negativo',
  },
  {
    n: 7,
    codigo: 'total_pagado_vs_aplicado_cuotas',
    titulo: 'Total pagos vs aplicado a cuotas (solo LIQUIDADO marca alerta SI)',
    notaOperativa:
      'La alerta SI solo aplica a prestamos en estado LIQUIDADO; en APROBADO el diff es informativo. Prioridad: diagnosticar Bs mal cargados como USD (monto_pagado inflado). Backend: python scripts/diagnostico_control_7_prioridad_critica.py y sql/control_7_prioridad_critica.sql. Corregir pagos con comprobante, luego reaplicar cascada por prestamo; ver control_7_total_pagos_vs_aplicado_diagnostico_y_correccion.sql.',
  },
  {
    n: 8,
    codigo: 'total_financiamiento_vs_suma_cuotas',
    titulo: 'Total financiamiento vs suma de cuotas',
  },
  {
    n: 9,
    codigo: 'sin_cuotas',
    titulo: 'Prestamo aprobado sin filas en cuotas',
  },
  {
    n: 10,
    codigo: 'numero_cuotas_inconsistente',
    titulo: 'Numero de cuotas configurado vs filas en BD',
  },
  {
    n: 11,
    codigo: 'liquidado_con_cuota_pendiente',
    titulo: 'LIQUIDADO con cuota sin cubrir al 100%',
  },
  {
    n: 12,
    codigo: 'estado_cuota_vs_calculo',
    titulo: 'Estado en tabla cuotas vs regla de negocio (vencimiento y pagos)',
    notaOperativa:
      'Use el boton Alinear estados de cuotas en esta pestana para masificar la correccion en cartera; luego vuelva a ejecutar el control.',
  },
  {
    n: 13,
    codigo: 'pago_bs_sin_tasa_cambio_diaria',
    titulo: 'Pago en bolivares sin tasa oficial del dia (tasas_cambio_diaria)',
    notaOperativa:
      'En Admin > Tasa de cambio: agregue la tasa por fecha de pago. Si hay filas con tasa 0 o valor de plantilla (99999.99), use Consultar problematicas y Rellenar desde vecino (simular antes de aplicar).',
  },
  {
    n: 14,
    codigo: 'conversion_bs_a_usd_incoherente',
    titulo: 'Conversion BS a USD incoherente (cero tolerancia 2 decimales)',
  },
  {
    n: 15,
    codigo: 'pagos_sin_aplicacion_a_cuotas',
    titulo: 'Pagos operativos sin aplicacion a cuotas o saldo sin aplicar',
    notaOperativa:
      'En la tabla: Ver pagos (detalle) y Cascada por prestamo, o el boton masivo Reaplicar cascada (control 15). Tras corregir montos/tasas, use cascada; si el total pagado supera la suma de cuotas del plan, puede quedar saldo sin cuota que absorba (revision de negocio).',
  },
  {
    n: 16,
    codigo: 'pagos_huella_funcional_duplicada',
    titulo: 'Pagos con misma huella funcional (fecha, monto, ref_norm)',
  },
  {
    n: 17,
    codigo: 'liquidado_descuadre_total_pagos_vs_aplicado_cuotas',
    titulo:
      'LIQUIDADO con descuadre: total pagos operativos vs aplicado a cuotas',
  },
]

export function numeroControlAuditoriaCartera(
  codigo: string
): number | undefined {
  return AUDITORIA_CARTERA_CONTROLES_CATALOGO.find(c => c.codigo === codigo)?.n
}
