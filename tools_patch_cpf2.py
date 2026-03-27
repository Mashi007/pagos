from pathlib import Path
p = Path("frontend/src/components/prestamos/CrearPrestamoForm.tsx")
t = p.read_text(encoding="utf-8")
needle = """                    <p className=\"mt-1 text-xs text-gray-500\">
                      Al guardar se persistirá el estado en la base de datos.
                      Revise coherencia con cuotas y pagos.
                    </p>
                  </div>
                ) : null}"""
if needle not in t:
    # ascii persistira
    raise SystemExit("help paragraph not found")
ins = """                    <p className=\"mt-1 text-xs text-gray-500\">
                      Al guardar se persistirá el estado en la base de datos.
                      Revise coherencia con cuotas y pagos.
                    </p>
                    {prestamo?.estado === 'DESISTIMIENTO' && prestamo?.fecha_desistimiento ? (
                      <p className=\"mt-2 text-xs text-slate-600\">
                        Fecha de desistimiento: {fechaInputYmd(prestamo.fecha_desistimiento)}
                      </p>
                    ) : null}
                  </div>
                ) : null}"""
p.write_text(t.replace(needle, ins, 1), encoding="utf-8", newline="\n")
print("fecha_desistimiento hint ok")
