# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "src" / "components" / "notificaciones" / "ConfiguracionNotificaciones.tsx"
t = p.read_text(encoding="utf-8")

bad1 = (
    "          msg = Ningun envio: active Envio en la pestana del caso ( omitidos por configuracion).\n"
)
good1 = (
    "          msg = `Ningun envio: active Envio en la pestana del caso (${oc} omitidos por configuracion).`\n"
)

bad2 = (
    "          ${res.mensaje} En unos segundos use Actualizar en Ultimo envio masivo para ver enviados y omitidos por paquete. Si enviados=0, revise PDFs en pestana 3 y disco persistente en Render.,\n"
)
good2 = (
    "          `${res.mensaje} En unos segundos use Actualizar en Ultimo envio masivo para ver enviados y omitidos por paquete. Si enviados=0, revise PDFs en pestana 3 y disco persistente en Render.`,\n"
)

if bad1 not in t:
    raise SystemExit("bad1 not found")
if bad2 not in t:
    raise SystemExit("bad2 not found")

t = t.replace(bad1, good1, 1).replace(bad2, good2, 1)
p.write_text(t, encoding="utf-8")
print("ok")
