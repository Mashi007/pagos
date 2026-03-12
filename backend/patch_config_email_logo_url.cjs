// Replace {{LOGO_URL}} in body when sending prueba email (Node script to patch Python file)
const fs = require('fs');
const path = require('path');
const file = path.join(__dirname, 'app/api/v1/endpoints/configuracion_email.py');
let c = fs.readFileSync(file, 'utf8');

if (c.includes('{{LOGO_URL}}') && c.includes('logo_url')) {
  console.log('Already patched');
  process.exit(0);
}

const old = `    subject = (payload.subject or "").strip() or "Prueba de email - RapiCredit"
    body = (payload.mensaje or "").strip() or "Este es un correo de prueba enviado desde la configuracion de email."
    recipients = [destino]`;

const new = `    subject = (payload.subject or "").strip() or "Prueba de email - RapiCredit"
    body = (payload.mensaje or "").strip() or "Este es un correo de prueba enviado desde la configuracion de email."
    if "{{LOGO_URL}}" in body:
        try:
            from app.core.email import _logo_url_for_email
            body = body.replace("{{LOGO_URL}}", _logo_url_for_email())
        except Exception:
            body = body.replace("{{LOGO_URL}}", "https://rapicredit.onrender.com/pagos/logos/rapicredit-public.png")
    recipients = [destino]`;

if (!c.includes(old)) {
  console.log('Pattern not found');
  process.exit(1);
}
c = c.replace(old, new);
fs.writeFileSync(file, c);
console.log('Patched configuracion_email.py: {{LOGO_URL}} replaced in prueba body');
