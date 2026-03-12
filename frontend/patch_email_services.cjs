/**
 * Add per-service email toggles to EmailConfig.
 * Run from frontend dir: node patch_email_services.js
 */
const fs = require('fs');
const path = require('path');
const file = path.join(__dirname, 'src/components/configuracion/EmailConfig.tsx');
let t = fs.readFileSync(file, 'utf8');

// 1) Interface: add optional service flags
const iface = `  email_activo?: string
  imap_host?: string`;
const ifaceNew = `  email_activo?: string
  email_activo_notificaciones?: string
  email_activo_informe_pagos?: string
  email_activo_estado_cuenta?: string
  email_activo_cobros?: string
  email_activo_campanas?: string
  email_activo_tickets?: string
  imap_host?: string`;
if (!t.includes('email_activo_notificaciones')) {
  t = t.replace(iface, ifaceNew);
}

// 2) cargarConfiguracion: set service flags from data (default 'true')
const loadMark = "setEmailActivo(emailActivoValue)";
const loadInsert = `
      setConfig(prev => {
        const next = { ...prev };
        ['email_activo_notificaciones','email_activo_informe_pagos','email_activo_estado_cuenta','email_activo_cobros','email_activo_campanas','email_activo_tickets'].forEach(k => {
          if (data[k] !== undefined && data[k] !== null) next[k] = (data[k] === 'true' || data[k] === '1') ? 'true' : 'false';
          else if (prev[k] === undefined) next[k] = 'true';
        });
        return next;
      });
      `;
// Actually we're already in setConfig(prev=>...) before setEmailActivo. So we need to set the service flags when we set config. The current code does setConfig(prev => { const next = { ...data }; ... return next }). So next already has data. We just need to ensure data has the 6 keys with default 'true'. So in the block where we do "if (data.tickets_notify_emails === undefined)" we add defaults for the 6 keys.
const defaultBlock = "if (data.tickets_notify_emails === undefined) data.tickets_notify_emails = ''";
const defaultBlockNew = `if (data.tickets_notify_emails === undefined) data.tickets_notify_emails = ''
      const serviceKeys = ['email_activo_notificaciones','email_activo_informe_pagos','email_activo_estado_cuenta','email_activo_cobros','email_activo_campanas','email_activo_tickets']
      serviceKeys.forEach(k => { if (data[k] === undefined || data[k] === null) data[k] = 'true' })`;
if (!t.includes('email_activo_notificaciones')) {
  t = t.replace(defaultBlock, defaultBlockNew);
}

// 3) configCompleta: add the 6 keys
const configBlock = "email_activo: emailActivo ? 'true' : 'false',\n            imap_host:";
const configBlockNew = `email_activo: emailActivo ? 'true' : 'false',
            email_activo_notificaciones: (config.email_activo_notificaciones ?? 'true') === 'true' ? 'true' : 'false',
            email_activo_informe_pagos: (config.email_activo_informe_pagos ?? 'true') === 'true' ? 'true' : 'false',
            email_activo_estado_cuenta: (config.email_activo_estado_cuenta ?? 'true') === 'true' ? 'true' : 'false',
            email_activo_cobros: (config.email_activo_cobros ?? 'true') === 'true' ? 'true' : 'false',
            email_activo_campanas: (config.email_activo_campanas ?? 'true') === 'true' ? 'true' : 'false',
            email_activo_tickets: (config.email_activo_tickets ?? 'true') === 'true' ? 'true' : 'false',
            imap_host:`;
if (!t.includes('email_activo_notificaciones')) {
  t = t.replace(configBlock, configBlockNew);
}

// 4) UI: after the "Servicio de Email" toggle (after the closing </label> and parent div), add a new Card "Email por servicio"
const toggleEnd = "{emailActivo ? 'Activo' : 'Inactivo'}\n         </span>\n       </label>";
const servicesUI = `{emailActivo ? 'Activo' : 'Inactivo'}
         </span>
       </label>

       {/* Email por servicio: on/off independiente por cada uno */}
       <div className="mt-4 space-y-3">
         <p className="text-sm font-medium text-gray-700">Email por servicio</p>
         <p className="text-xs text-gray-600">Activa o desactiva el envio de email para cada tipo de uso. Si apagas uno, los demas siguen funcionando.</p>
         <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
           {[
             { key: 'email_activo_notificaciones', label: 'Notificaciones (plantillas a clientes)' },
             { key: 'email_activo_informe_pagos', label: 'Informe de pagos (cron)' },
             { key: 'email_activo_estado_cuenta', label: 'Estado de cuenta (codigo y PDF)' },
             { key: 'email_activo_cobros', label: 'Cobros (recibos y notificaciones)' },
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
if (!t.includes('Email por servicio')) {
  t = t.replace(toggleEnd, servicesUI);
}

fs.writeFileSync(file, t, 'utf8');
console.log('EmailConfig.tsx patched OK');
