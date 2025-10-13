#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

console.log('🚀 Configurando Sistema de Préstamos y Cobranza...\n');

// Crear archivo .env si no existe
const envPath = path.join(__dirname, '.env');
const envContent = `# API Configuration
VITE_API_URL=https://pagos-f2qf.onrender.com

# Environment
VITE_NODE_ENV=development

# App Configuration
VITE_APP_NAME="Sistema de Préstamos y Cobranza"
VITE_APP_VERSION="1.0.0"

# Features flags
VITE_ENABLE_NOTIFICATIONS=true
VITE_ENABLE_REPORTS=true
VITE_ENABLE_CONCILIATION=true
VITE_ENABLE_AI=true
`;

if (!fs.existsSync(envPath)) {
  fs.writeFileSync(envPath, envContent);
  console.log('✅ Archivo .env creado');
} else {
  console.log('ℹ️  Archivo .env ya existe');
}

console.log('\n🎉 Configuración completada!');
console.log('\n📋 Próximos pasos:');
console.log('1. npm install (si no lo has hecho)');
console.log('2. npm run dev');
console.log('3. Abrir http://localhost:3000');
console.log('\n👤 Usuarios de prueba:');
console.log('- admin@sistema.com / admin123');
console.log('- gerente@sistema.com / gerente123');
console.log('- asesor@sistema.com / asesor123');
console.log('\n🌐 API Backend: https://pagos-f2qf.onrender.com');
console.log('📚 Documentación: https://pagos-f2qf.onrender.com/docs');
