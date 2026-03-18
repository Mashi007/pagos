"""
Actualiza pocos prestamos MENSUAL y luego ejecuta la verificacion.
Uso (desde backend):  python actualizar_y_verificar_mensual.py [N]
  N = numero de prestamos a actualizar (default 5).
"""
import os
import sys
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== Antes ===")
from verificar_mensual_sql import main as verificar
verificar()

print("\n=== Actualizando", N, "prestamos ===")
import subprocess
r = subprocess.run(
    [sys.executable, "actualizar_amortizacion_mensual.py", "--limit", str(N)],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    capture_output=False,
    timeout=300,
)
if r.returncode != 0:
    print("Actualizacion fallo con codigo", r.returncode)
    sys.exit(r.returncode)

print("\n=== Despues ===")
verificar()
