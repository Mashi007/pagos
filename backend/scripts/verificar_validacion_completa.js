// ============================================
// VERIFICAR VALIDACIÓN COMPLETA
// Verificar todos los campos y sus valores para entender por qué falla
// ============================================

(() => {
  console.log('🔍 VERIFICACIÓN COMPLETA DE VALIDACIÓN\n');
  console.log('='.repeat(60));
  
  const inputs = Array.from(document.querySelectorAll('input, textarea'))
    .filter(inp => inp.offsetParent !== null);
  
  const campos = {};
  
  // Identificar campos por posición y tipo
  inputs.forEach((inp, i) => {
    const tipo = inp.type || 'text';
    const valor = inp.value || '';
    
    // Identificar por posición y tipo
    if (i === 0 && valor.includes('smtp')) {
      campos.smtp_host = valor;
    } else if (i === 1 && valor === '587') {
      campos.smtp_port = valor;
    } else if (tipo === 'email' && !campos.smtp_user) {
      campos.smtp_user = valor;
    } else if (tipo === 'password') {
      campos.smtp_password = valor ? '***' : '';
    } else if (tipo === 'email' && campos.smtp_user) {
      campos.from_email = valor;
    } else if (tipo === 'text' && valor === 'RapiCredit') {
      campos.from_name = valor;
    } else if (tipo === 'checkbox') {
      const label = inp.nextElementSibling;
      if (label?.textContent.includes('TLS')) {
        campos.smtp_use_tls = inp.checked ? 'true' : 'false';
      }
    }
  });
  
  console.log('📋 VALORES ENCONTRADOS EN EL DOM:\n');
  console.log(`   smtp_host: "${campos.smtp_host || '(vacío)'}"`);
  console.log(`   smtp_port: "${campos.smtp_port || '(vacío)'}"`);
  console.log(`   smtp_user: "${campos.smtp_user || '(vacío)'}"`);
  console.log(`   smtp_password: ${campos.smtp_password ? '*** (tiene valor)' : '(vacío)'}`);
  console.log(`   from_email: "${campos.from_email || '(vacío)'}"`);
  console.log(`   smtp_use_tls: "${campos.smtp_use_tls || '(vacío)'}"`);
  
  // Verificar validaciones según el código de React
  console.log('\n🔍 APLICANDO VALIDACIONES (según código React):\n');
  
  const errores = [];
  
  // 1. Campos obligatorios básicos
  if (!campos.smtp_host || !campos.smtp_host.trim()) {
    errores.push('❌ smtp_host está vacío');
  } else {
    console.log('✅ smtp_host: OK');
  }
  
  if (!campos.smtp_port || !campos.smtp_port.trim()) {
    errores.push('❌ smtp_port está vacío');
  } else {
    console.log('✅ smtp_port: OK');
  }
  
  if (!campos.smtp_user || !campos.smtp_user.trim()) {
    errores.push('❌ smtp_user está vacío');
  } else {
    console.log('✅ smtp_user: OK');
  }
  
  if (!campos.from_email || !campos.from_email.trim()) {
    errores.push('❌ from_email está vacío');
  } else {
    console.log('✅ from_email: OK');
  }
  
  // 2. Validar puerto numérico
  if (campos.smtp_port) {
    const puerto = parseInt(campos.smtp_port);
    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      errores.push(`❌ Puerto inválido: ${campos.smtp_port}`);
    } else {
      console.log(`✅ Puerto válido: ${puerto}`);
    }
  }
  
  // 3. Validaciones para Gmail
  if (campos.smtp_host?.toLowerCase().includes('gmail.com')) {
    console.log('\n📧 Validaciones específicas para Gmail:');
    
    if (!campos.smtp_password || campos.smtp_password.trim() === '') {
      errores.push('❌ Gmail requiere contraseña');
    } else {
      console.log('✅ Contraseña: OK');
    }
    
    const puerto = parseInt(campos.smtp_port || '0');
    if (puerto === 587) {
      if (campos.smtp_use_tls !== 'true') {
        errores.push('❌ Puerto 587 requiere TLS habilitado');
      } else {
        console.log('✅ TLS habilitado para puerto 587: OK');
      }
    }
  }
  
  console.log('\n' + '='.repeat(60));
  
  if (errores.length > 0) {
    console.log('❌ ERRORES ENCONTRADOS:\n');
    errores.forEach(error => console.log(`   ${error}`));
    console.log('\n💡 Estos son los campos que necesitas completar o corregir.');
  } else {
    console.log('✅ TODAS LAS VALIDACIONES PASARON');
    console.log('\n⚠️ Si el botón sigue deshabilitado, el problema puede ser:');
    console.log('   1. El estado de React no se está actualizando');
    console.log('   2. Hay un problema con el useMemo de puedeGuardar');
    console.log('   3. Los valores en el DOM no coinciden con el estado de React');
    console.log('\n💡 Intenta hacer clic en cada campo y presionar Tab para forzar actualización.');
  }
  
  return { campos, errores };
})();

