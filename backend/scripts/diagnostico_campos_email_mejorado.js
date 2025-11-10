// ============================================
// DIAGNÓSTICO MEJORADO DE CAMPOS DE EMAIL
// Busca todos los inputs y los identifica correctamente
// ============================================

(() => {
  console.log('🔍 DIAGNÓSTICO MEJORADO DE CAMPOS\n');
  console.log('='.repeat(60));
  
  const inputs = Array.from(document.querySelectorAll('input, textarea'));
  const campos = {};
  
  console.log(`\n📊 Total de inputs encontrados: ${inputs.length}\n`);
  
  inputs.forEach((input, index) => {
    const tipo = input.type || 'text';
    const valor = input.value || '';
    const placeholder = input.placeholder || '';
    const visible = input.offsetParent !== null;
    
    if (!visible) return;
    
    // Buscar el label asociado de manera más exhaustiva
    let labelTexto = '';
    
    // Método 1: Buscar label con for
    if (input.id) {
      const label = document.querySelector(`label[for="${input.id}"]`);
      if (label) labelTexto = label.textContent.trim();
    }
    
    // Método 2: Buscar label padre
    if (!labelTexto) {
      const labelParent = input.closest('label');
      if (labelParent) labelTexto = labelParent.textContent.trim();
    }
    
    // Método 3: Buscar label anterior (hermano)
    if (!labelTexto) {
      let elemento = input.previousElementSibling;
      let intentos = 0;
      while (elemento && !labelTexto && intentos < 5) {
        if (elemento.tagName === 'LABEL') {
          labelTexto = elemento.textContent.trim();
        } else if (elemento.classList.contains('text-sm') || elemento.classList.contains('font-medium')) {
          // Puede ser un label sin tag label
          labelTexto = elemento.textContent.trim();
        }
        elemento = elemento.previousElementSibling;
        intentos++;
      }
    }
    
    // Método 4: Buscar en el contenedor padre
    if (!labelTexto) {
      const contenedor = input.closest('div');
      if (contenedor) {
        const labels = contenedor.querySelectorAll('label');
        if (labels.length > 0) {
          labelTexto = labels[0].textContent.trim();
        }
      }
    }
    
    // Identificar campo
    let nombre = null;
    const labelLower = labelTexto.toLowerCase();
    const placeholderLower = placeholder.toLowerCase();
    
    if (labelLower.includes('servidor smtp') || placeholderLower.includes('smtp.gmail.com')) {
      nombre = 'smtp_host';
    } else if (labelLower.includes('puerto smtp') || placeholderLower.includes('587')) {
      nombre = 'smtp_port';
    } else if (labelLower.includes('usuario gmail') || labelLower.includes('email (usuario') || 
               (labelLower.includes('gmail') && labelLower.includes('workspace') && tipo === 'email')) {
      nombre = 'smtp_user';
    } else if (labelLower.includes('contraseña de aplicación') || labelLower.includes('app password') || 
               (tipo === 'password' && !campos.smtp_password)) {
      nombre = 'smtp_password';
    } else if (labelLower.includes('email del remitente') || labelLower.includes('remitente') && tipo === 'email') {
      nombre = 'from_email';
    } else if (labelLower.includes('nombre del remitente') || placeholderLower.includes('rapicredit')) {
      nombre = 'from_name';
    } else if (placeholderLower.includes('pruebas@ejemplo.com')) {
      nombre = 'email_pruebas';
    }
    
    // Si no se identificó pero es un input de email, intentar identificarlo por posición
    if (!nombre && tipo === 'email') {
      // Contar cuántos inputs de email hemos visto antes
      const emailsAnteriores = Object.keys(campos).filter(k => campos[k].tipo === 'email').length;
      if (emailsAnteriores === 0) {
        // Probablemente es smtp_user
        nombre = 'smtp_user';
      } else if (emailsAnteriores === 1) {
        // Probablemente es from_email
        nombre = 'from_email';
      }
    }
    
    if (nombre) {
      campos[nombre] = {
        valor: tipo === 'password' ? '***' : valor,
        vacio: !valor || valor.trim() === '',
        placeholder: placeholder,
        label: labelTexto,
        tipo: tipo,
        index: index
      };
      
      console.log(`✅ Campo identificado: ${nombre}`);
      console.log(`   Label: "${labelTexto}"`);
      console.log(`   Placeholder: "${placeholder}"`);
      console.log(`   Valor: ${tipo === 'password' ? '***' : valor.substring(0, 50)}`);
      console.log(`   Vacío: ${!valor || valor.trim() === '' ? '❌ SÍ' : '✅ NO'}`);
      console.log('');
    } else {
      // Mostrar inputs no identificados para debugging
      if (tipo !== 'checkbox' && tipo !== 'radio') {
        console.log(`⚠️ Input no identificado #${index}:`);
        console.log(`   Tipo: ${tipo}`);
        console.log(`   Valor: ${valor.substring(0, 30)}`);
        console.log(`   Placeholder: "${placeholder}"`);
        console.log(`   Label encontrado: "${labelTexto}"`);
        console.log('');
      }
    }
  });
  
  // Buscar checkbox TLS
  const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
  checkboxes.forEach(cb => {
    const label = cb.nextElementSibling;
    if (label && label.textContent.includes('TLS')) {
      campos['smtp_use_tls'] = {
        valor: cb.checked ? 'true' : 'false',
        vacio: false,
        placeholder: '',
        label: label.textContent.trim(),
        tipo: 'checkbox'
      };
      console.log(`✅ Campo identificado: smtp_use_tls`);
      console.log(`   Valor: ${cb.checked ? 'true' : 'false'}`);
      console.log('');
    }
  });
  
  // Resumen final
  console.log('='.repeat(60));
  console.log('📋 RESUMEN FINAL:\n');
  
  const camposObligatorios = ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email', 'smtp_use_tls'];
  
  camposObligatorios.forEach(nombre => {
    const campo = campos[nombre];
    if (campo) {
      const estado = campo.vacio ? '❌ VACÍO' : '✅ COMPLETO';
      console.log(`${estado} - ${nombre}: ${campo.valor.substring(0, 50)}`);
    } else {
      console.log(`⚠️ ${nombre}: NO ENCONTRADO`);
    }
  });
  
  // Validaciones
  console.log('\n🔍 VALIDACIONES:');
  const esGmail = campos.smtp_host?.valor?.toLowerCase().includes('gmail.com');
  const puerto = parseInt(campos.smtp_port?.valor || '0');
  const tlsHabilitado = campos.smtp_use_tls?.valor === 'true';
  
  console.log(`   Es Gmail: ${esGmail ? '✅ SÍ' : '❌ NO'}`);
  console.log(`   Puerto: ${puerto}`);
  console.log(`   TLS habilitado: ${tlsHabilitado ? '✅ SÍ' : '❌ NO'}`);
  
  if (esGmail) {
    if (puerto === 587 && !tlsHabilitado) {
      console.log(`   ⚠️ PROBLEMA: Puerto 587 requiere TLS`);
    }
    if (campos.smtp_password?.vacio) {
      console.log(`   ⚠️ PROBLEMA: Gmail requiere contraseña`);
    }
  }
  
  // Campos faltantes
  const camposFaltantes = camposObligatorios.filter(nombre => {
    const campo = campos[nombre];
    return !campo || campo.vacio;
  });
  
  if (camposFaltantes.length > 0) {
    console.log(`\n❌ CAMPOS FALTANTES: ${camposFaltantes.join(', ')}`);
  } else {
    console.log(`\n✅ TODOS LOS CAMPOS OBLIGATORIOS ESTÁN COMPLETOS`);
  }
  
  return { campos, camposFaltantes };
})();

