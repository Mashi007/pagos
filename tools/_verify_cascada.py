from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

pre = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
t = pre.read_text(encoding="utf-8", errors="replace")
print("reaplicar-cascada-aplicacion" in t, "cascada route")
print(t.count("@router.post"), "router.post count")

pg = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
p = pg.read_text(encoding="utf-8", errors="replace")
print("c == cascada norm", 'if c == "cascada":' in p)
print("_estado_pago_tras_aplicar_cascada" in p, "cascada fn")
print("_estado_pago_tras_aplicar_fifo = _estado_pago_tras_aplicar_cascada" in p, "alias")

sv = ROOT / "backend" / "app" / "services" / "pagos_cuotas_reaplicacion.py"
s = sv.read_text(encoding="utf-8", errors="replace")
print("reset_y_reaplicar_cascada_prestamo" in s, "service cascada")
print("reset_y_reaplicar_fifo_prestamo =" in s, "service fifo alias")
