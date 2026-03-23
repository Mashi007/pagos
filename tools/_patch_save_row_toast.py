from pathlib import Path

p = Path(r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\hooks\useExcelUploadPagos.ts")
t = p.read_text(encoding="utf-8")

old = """      } catch (err: any) {
        return false
      }
    },

    [prestamosPorCedula, refreshPagos]
  )"""

new = """      } catch (err: any) {
        const detail = err?.response?.data?.detail

        const msg = Array.isArray(detail)
          ? detail.map((d: any) => d.msg || d.message).join(' ')
          : detail || err?.message || 'Error al guardar'

        addToast(
          'error',
          typeof msg === 'string' ? msg : 'Error al guardar la fila'
        )

        return false
      }
    },

    [prestamosPorCedula, refreshPagos, addToast, excelData]
  )"""

if old not in t:
    raise SystemExit("catch block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8", newline="\n")
print("OK saveRowIfValid toast + deps")
