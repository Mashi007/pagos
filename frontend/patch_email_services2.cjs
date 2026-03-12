const fs = require('fs');
const path = require('path');
const file = path.join(__dirname, 'src/components/configuracion/EmailConfig.tsx');
let t = fs.readFileSync(file, 'utf8');

// 1) Interface: add the 6 keys after email_activo
if (!t.includes('email_activo_notificaciones?: string')) {
  t = t.replace(
    '  email_activo?: string\n  imap_host?: string',
    '  email_activo?: string\n  email_activo_notificaciones?: string\n  email_activo_informe_pagos?: string\n  email_activo_estado_cuenta?: string\n  email_activo_cobros?: string\n  email_activo_campanas?: string\n  email_activo_tickets?: string\n  imap_host?: string'
  );
  console.log('Interface updated');
}

// 2) configCompleta: add 6 keys after email_activo
if (!t.includes('email_activo_notificaciones: (config')) {
  t = t.replace(
    "email_activo: emailActivo ? 'true' : 'false',\n            imap_host: config.imap_host || ''",
    "email_activo: emailActivo ? 'true' : 'false',\n            email_activo_notificaciones: (config.email_activo_notificaciones ?? 'true') === 'true' ? 'true' : 'false',\n            email_activo_informe_pagos: (config.email_activo_informe_pagos ?? 'true') === 'true' ? 'true' : 'false',\n            email_activo_estado_cuenta: (config.email_activo_estado_cuenta ?? 'true') === 'true' ? 'true' : 'false',\n            email_activo_cobros: (config.email_activo_cobros ?? 'true') === 'true' ? 'true' : 'false',\n            email_activo_campanas: (config.email_activo_campanas ?? 'true') === 'true' ? 'true' : 'false',\n            email_activo_tickets: (config.email_activo_tickets ?? 'true') === 'true' ? 'true' : 'false',\n            imap_host: config.imap_host || ''"
  );
  console.log('configCompleta updated');
}

// 3) UI: after the label that contains "Inactivo" (Servicio de Email toggle), add the services section
if (!t.includes('Email por servicio')) {
  const marker = '</span>\n       </label>\n       </div>';
  const idx = t.indexOf(marker);
  if (idx === -1) {
    // try alternate
    const m2 = '{emailActivo ? \'Activo\' : \'Inactivo\'}\n         </span>\n       </label>';
    const idx2 = t.indexOf(m2);
    if (idx2 !== -1) {
      const insert = `\n       <div className="mt-4 space-y-3"><p className="text-sm font-medium text-gray-700">Email por servicio</p><p className="text-xs text-gray-600">Activa o desactiva el envio de email para cada tipo de uso.</p><div className="grid grid-cols-1 sm:grid-cols-2 gap-3">${[
        { key: 'email_activo_notificaciones', label: 'Notificaciones (plantillas a clientes)' },
        { key: 'email_activo_informe_pagos', label: 'Informe de pagos (cron)' },
        { key: 'email_activo_estado_cuenta', label: 'Estado de cuenta (codigo y PDF)' },
        { key: 'email_activo_cobros', label: 'Cobros (recibos)' },
        { key: 'email_activo_campanas', label: 'Campanas CRM' },
        { key: 'email_activo_tickets', label: 'Tickets (aviso interno)' }
      ].map(({ key, label }) => `<label key="${key}" className="flex items-center justify-between gap-2 p-2 rounded border border-gray-200 bg-gray-50/50"><span className="text-sm text-gray-700">${label}</span><input type="checkbox" checked={(config.${key} ?? 'true') === 'true'} onChange={(e) => handleChange('${key}', e.target.checked ? 'true' : 'false')} className="rounded border-gray-300" /></label>`).join('')}</div></div>`;
      t = t.slice(0, idx2 + m2.length) + insert + t.slice(idx2 + m2.length);
      console.log('UI section added');
    }
  } else {
    const insert = `\n       <div className="mt-4 space-y-3"><p className="text-sm font-medium text-gray-700">Email por servicio</p><p className="text-xs text-gray-600">Activa o desactiva el envio de email para cada tipo de uso.</p><div className="grid grid-cols-1 sm:grid-cols-2 gap-3">${[
      { key: 'email_activo_notificaciones', label: 'Notificaciones (plantillas a clientes)' },
      { key: 'email_activo_informe_pagos', label: 'Informe de pagos (cron)' },
      { key: 'email_activo_estado_cuenta', label: 'Estado de cuenta (codigo y PDF)' },
      { key: 'email_activo_cobros', label: 'Cobros (recibos)' },
      { key: 'email_activo_campanas', label: 'Campanas CRM' },
      { key: 'email_activo_tickets', label: 'Tickets (aviso interno)' }
    ].map(({ key, label }) => `<label key="${key}" className="flex items-center justify-between gap-2 p-2 rounded border border-gray-200 bg-gray-50/50"><span className="text-sm text-gray-700">${label}</span><input type="checkbox" checked={(config.${key} ?? 'true') === 'true'} onChange={(e) => handleChange('${key}', e.target.checked ? 'true' : 'false')} className="rounded border-gray-300" /></label>`).join('')}</div></div>`;
    t = t.slice(0, idx + marker.length) + insert + t.slice(idx + marker.length);
    console.log('UI section added (marker 1)');
  }
}

fs.writeFileSync(file, t, 'utf8');
console.log('Done');
