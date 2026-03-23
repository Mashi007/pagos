from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 1) PagoExcelRow
PVAL = ROOT / "frontend" / "src" / "utils" / "pagoExcelValidation.ts"
t = PVAL.read_text(encoding="utf-8")
OLD = """  conciliado: boolean
}"""
NEW = """  conciliado: boolean

  /** Opcional: columnas moneda / tasa en plantilla Excel */

  moneda_registro?: 'USD' | 'BS'

  tasa_cambio_manual?: number
}"""
if OLD not in t:
    raise SystemExit("PagoExcelRow anchor not found")
PVAL.write_text(t.replace(OLD, NEW, 1), encoding="utf-8")

# 2) useExcelUploadPagos - extend cols return and rowData + payloads
UE = ROOT / "frontend" / "src" / "hooks" / "useExcelUploadPagos.ts"
text = UE.read_text(encoding="utf-8")

OLD2 = """          let cedula = 0,
            fecha = 1,
            monto = 2,
            documento = 3,
            prestamo = 4,
            conciliacion = 5

          let cedulaHeaderMatched = false"""
NEW2 = """          let cedula = 0,
            fecha = 1,
            monto = 2,
            documento = 3,
            prestamo = 4,
            conciliacion = 5

          let monedaCol = -1

          let tasaCol = -1

          let cedulaHeaderMatched = false"""
if OLD2 not in text:
    raise SystemExit("cols vars anchor not found")
text = text.replace(OLD2, NEW2, 1)

OLD3 = """            if (match(i, 'conciliacion', 'conciliación')) conciliacion = i
          }

          return { cedula, fecha, monto, documento, prestamo, conciliacion }
        })()"""
NEW3 = """            if (match(i, 'conciliacion', 'conciliación')) conciliacion = i

            if (match(i, 'moneda', 'currency')) monedaCol = i

            if (match(i, 'tasa', 'tasa_cambio', 'tc', 'bcv')) tasaCol = i
          }

          return { cedula, fecha, monto, documento, prestamo, conciliacion, monedaCol, tasaCol }
        })()"""
if OLD3 not in text:
    raise SystemExit("cols return anchor not found")
text = text.replace(OLD3, NEW3, 1)

OLD4 = """          const conciliado = conciliacionRaw === 'NO' ? false : true

          const numeroDocStr ="""
NEW4 = """          const conciliado = conciliacionRaw === 'NO' ? false : true

          let moneda_registro: 'USD' | 'BS' = 'USD'

          if (cols.monedaCol >= 0) {
            const raw = String(row[cols.monedaCol] ?? '')
              .trim()
              .toUpperCase()

            if (raw === 'BS' || raw.includes('BOLIV')) moneda_registro = 'BS'
          }

          let tasa_cambio_manual: number | undefined

          if (cols.tasaCol >= 0) {
            const tr = parseFloat(String(row[cols.tasaCol] ?? '').replace(',', '.'))

            if (Number.isFinite(tr) && tr > 0) tasa_cambio_manual = tr
          }

          const numeroDocStr ="""
if OLD4 not in text:
    raise SystemExit("conciliado anchor not found")
text = text.replace(OLD4, NEW4, 1)

OLD5 = """            conciliado,
          }"""
NEW5 = """            conciliado,

            moneda_registro,

            tasa_cambio_manual,
          }"""
if OLD5 not in text:
    raise SystemExit("rowData object anchor not found")
text = text.replace(OLD5, NEW5, 1)

OLD6 = """        const pagoData = {
          cedula_cliente: cedulaLookup,

          prestamo_id: prestamoId,

          fecha_pago:
            convertirFechaParaBackendPago(row.fecha_pago) ||
            new Date().toISOString().split('T')[0],

          monto_pagado: Number(row.monto_pagado) || 0,

          numero_documento: numeroDoc || '',

          institucion_bancaria: null,

          notas: null,

          conciliado: !!row.conciliado,
        }"""
NEW6 = """        const pagoData = {
          cedula_cliente: cedulaLookup,

          prestamo_id: prestamoId,

          fecha_pago:
            convertirFechaParaBackendPago(row.fecha_pago) ||
            new Date().toISOString().split('T')[0],

          monto_pagado: Number(row.monto_pagado) || 0,

          numero_documento: numeroDoc || '',

          institucion_bancaria: null,

          notas: null,

          conciliado: !!row.conciliado,

          moneda_registro: row.moneda_registro || 'USD',

          ...(row.tasa_cambio_manual
            ? { tasa_cambio_manual: row.tasa_cambio_manual }
            : {}),
        }"""
if OLD6 not in text:
    raise SystemExit("pagoData anchor not found")
text = text.replace(OLD6, NEW6, 1)

OLD7 = """      return {
        cedula_cliente: cedulaLookup,

        prestamo_id: prestamoId,

        fecha_pago:
          convertirFechaParaBackendPago(row.fecha_pago) ||
          new Date().toISOString().split('T')[0],

        monto_pagado: Number(row.monto_pagado) || 0,

        numero_documento: normalizarNumeroDocumento(row.numero_documento) || '',

        institucion_bancaria: null,

        notas: null,

        conciliado: !!row.conciliado,
      }
    }"""
NEW7 = """      return {
        cedula_cliente: cedulaLookup,

        prestamo_id: prestamoId,

        fecha_pago:
          convertirFechaParaBackendPago(row.fecha_pago) ||
          new Date().toISOString().split('T')[0],

        monto_pagado: Number(row.monto_pagado) || 0,

        numero_documento: normalizarNumeroDocumento(row.numero_documento) || '',

        institucion_bancaria: null,

        notas: null,

        conciliado: !!row.conciliado,

        moneda_registro: row.moneda_registro || 'USD',

        ...(row.tasa_cambio_manual
          ? { tasa_cambio_manual: row.tasa_cambio_manual }
          : {}),
      }
    }"""
if OLD7 not in text:
    raise SystemExit("buildPagoData anchor not found")
text = text.replace(OLD7, NEW7, 1)

UE.write_text(text, encoding="utf-8")
print("excel moneda patched")
