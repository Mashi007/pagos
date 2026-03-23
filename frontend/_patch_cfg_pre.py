# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "src" / "components" / "notificaciones" / "ConfiguracionNotificaciones.tsx"
t = p.read_text(encoding="utf-8")
needle = """                <Button
                  type=\"button\"
                  variant=\"outline\"
                  onClick={() => void handleDiagnosticoPaquete()}
                  className=\"flex h-auto w-full items-center justify-center gap-2 rounded-lg py-2\"
                >
                  Diagnosticar paquete (sin enviar correo)
                </Button>

                """
if needle not in t:
    raise SystemExit("needle not found")
extra = needle + """                {diagnosticoPaquete && (
                  <pre className="mt-2 max-h-48 overflow-auto rounded border border-gray-200 bg-gray-50 p-2 text-left text-xs text-gray-800">
                    {JSON.stringify(diagnosticoPaquete, null, 2)}
                  </pre>
                )}

                """
t = t.replace(needle, extra, 1)
p.write_text(t, encoding="utf-8")
print("ok")
