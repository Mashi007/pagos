# -*- coding: utf-8 -*-
from pathlib import Path
API = Path("frontend/src/services/api.ts")
t = API.read_text(encoding="utf-8")
reps = [
  ("configuraci\ufffdn", "configuración"),
  ("m\ufffds", "más"),
  ("or\ufffdgenes", "orígenes"),
  ("est\ufffdn", "estén"),
  ("est\ufffd expirado", "esté expirado"),
  ("est\ufffd presente", "esté presente"),
  ("est\ufffd siendo", "está siendo"),
  ("est\ufffd disponible", "esté disponible"),
  ("est\ufffd funcionando", "esté funcionando"),
  ("est\ufffd tardando", "esté tardando"),
  ("est\ufffd reiniciando", "esté reiniciando"),
  ("autenticaci\ufffdn", "autenticación"),
  ("contrase\ufffda", "contraseña"),
  ("l\ufffdnea", "línea"),
  ("Sesi\ufffdn", "Sesión"),
  ("sesi\ufffdn", "sesión"),
  ("inv\ufffdlido", "inválido"),
  ("conexi\ufffdn", "conexión"),
  ("teor\ufffda", "teoría"),
  ("s\ufffd es", "sí es"),
  ("protecci\ufffdn", "protección"),
  ("petici\ufffdn", "petición"),
  ("despu\ufffds", "después"),
  ("validaci\ufffdn", "validación"),
  ("v\ufffdlida", "válida"),
  ("fall\ufffd.", "falló."),
  ("m\ufffds requests", "más requests"),
  ("c\ufffddula", "cédula"),
  ("c\ufffddulas", "cédulas"),
  ("CORRECCI\ufffdN", "CORRECCIÓN"),
  ("acci\ufffdn", "acción"),
  ("informaci\ufffdn", "información"),
  ("espec\ufffdfico", "específico"),
  ("espec\ufffdfica", "específica"),
  ("espec\ufffdficos", "específicos"),
  ("diagn\ufffdstico", "diagnóstico"),
  ("gen\ufffdrico", "genérico"),
  ("autom\ufffdticamente", "automáticamente"),
  ("ver\ufffd el", "verá el"),
  ("expl\ufffdcito", "explícito"),
  ("recibi\ufffd", "recibió"),
  ("(vac\ufffdo)", "(vacío)"),
  ("M\ufffdtodo", "Método"),
  ("FUNCI\ufffdN", "FUNCIÓN"),
  ("espec\ufffdficamente", "específicamente"),
  ("par\ufffdmetros", "parámetros"),
  ("s\ufffdncrono", "síncrono"),
  ("fr\ufffdo", "frío"),
  ("3\ufffd5 s", "3-5 s"),
  ("seg\ufffdn el", "según el"),
  ("m\ufffds descriptivo", "más descriptivo"),
  ("ahora m\ufffds espec\ufffdfico", "ahora más específico"),
  ("m\ufffds espec\ufffdfico", "más específico"),
  ("M\ufffdodos HTTP", "Métodos HTTP"),
  ("M\ufffdtodo para", "Método para"),
  ("Error en la configuraci\ufffdn", "Error en la configuración"),
  ("espec\ufffdfico del", "específico del"),
  ("espec\ufffdficos del", "específicos del"),
]
for a,b in reps:
  t = t.replace(a,b)
if "\ufffd" in t:
  for i,line in enumerate(t.splitlines(),1):
    if "\ufffd" in line:
      print("REMAINING", i)
  raise SystemExit(1)
API.write_text(t, encoding="utf-8", newline="\n")
print("OK, all FFFD removed")
