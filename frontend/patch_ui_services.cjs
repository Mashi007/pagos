const fs = require('fs');
const path = require('path');
const file = path.join(__dirname, 'src/components/configuracion/EmailConfig.tsx');
let t = fs.readFileSync(file, 'utf8');

if (t.includes('Email por servicio')) {
  console.log('Already has UI');
  process.exit(0);
}

const uiBlock = `

          <div className="mt-4 space-y-3">
            <p className="text-sm font-medium text-gray-700">Email por servicio</p>
            <p className="text-xs text-gray-600">Activa o desactiva el envio de email para cada tipo de uso. Si apagas uno, los demas siguen funcionando.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { key: 'email_activo_notificaciones', label: 'Notificaciones (plantillas a clientes)' },
                { key: 'email_activo_informe_pagos', label: 'Informe de pagos (cron)' },
                { key: 'email_activo_estado_cuenta', label: 'Estado de cuenta (codigo y PDF)' },
                { key: 'email_activo_cobros', label: 'Cobros (recibos)' },
                { key: 'email_activo_campanas', label: 'Campanas CRM' },
                { key: 'email_activo_tickets', label: 'Tickets (aviso interno)' }
              ].map(({ key, label }) => (
                <label key={key} className="flex items-center justify-between gap-2 p-2 rounded border border-gray-200 bg-gray-50/50">
                  <span className="text-sm text-gray-700">{label}</span>
                  <input
                    type="checkbox"
                    checked={(config[key] ?? 'true') === 'true'}
                    onChange={(e) => handleChange(key, e.target.checked ? 'true' : 'false')}
                    className="rounded border-gray-300"
                  />
                </label>
              ))}
            </div>
          </div>`;

const marker = '            </div>\n          </div>\n\n          {/* Banners de estado';
const idx = t.indexOf(marker);
if (idx !== -1) {
  t = t.slice(0, idx + marker.length) + uiBlock + t.slice(idx + marker.length);
  fs.writeFileSync(file, t, 'utf8');
  console.log('UI section added');
} else {
  console.log('Marker not found. Tried: ', marker.substring(0, 50));
}
