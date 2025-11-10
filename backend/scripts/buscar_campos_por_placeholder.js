// ============================================
// BUSCAR CAMPOS POR PLACEHOLDER Y LABEL
// Los campos de EmailConfig usan componentes Input sin name/id
// ============================================

(() => {
  console.log('🔍 BUSCANDO CAMPOS POR PLACEHOLDER Y LABEL\n');
  
  // Mapeo de placeholders a nombres de campo
  const mapeoCampos = {
    'smtp.gmail.com': 'smtp_host',
    '587': 'smtp_port',
    'tu-email@gmail.com': 'smtp_user',
    'App Password de Gmail': 'smtp_password',
    'tu-email@gmail.com o usuario@tudominio.com': 'from_email',
    'RapiCredit': 'from_name'
  };
  
  // Buscar todos los inputs
  const todosLosInputs = Array.from(document.querySelectorAll('input, textarea'));
  
  console.log(`📊 Total de inputs encontrados: ${todosLosInputs.length}\n`);
  
  const camposEncontrados = {};
  
  todosLosInputs.forEach((input, index) => {
    const placeholder = input.placeholder || '';
    const tipo = input.type || 'text';
    const valor = tipo === 'password' ? '***' : input.value;
    const vacio = !input.value || input.value.trim() === '';
    const visible = input.offsetParent !== null;
    
    // Buscar label asociado
    let labelTexto = '';
    if (input.id) {
      const label = document.querySelector(`label[for="${input.id}"]`);
      if (label) labelTexto = label.textContent.trim();
    }
    
    if (!labelTexto) {
      // Buscar label padre o anterior
      let elemento = input.previousElementSibling;
      while (elemento && !labelTexto) {
        if (elemento.tagName === 'LABEL') {
          labelTexto = elemento.textContent.trim();
        }
        elemento = elemento.previousElementSibling;
      }
    }
    
    // Identificar campo por placeholder o label
    let nombreCampo = null;
    
    if (placeholder.includes('smtp.gmail.com') || labelTexto.includes('Servidor SMTP')) {
      nombreCampo = 'smtp_host';
    } else if (placeholder.includes('587') || labelTexto.includes('Puerto SMTP')) {
      nombreCampo = 'smtp_port';
    } else if (labelTexto.includes('Email (Usuario') || labelTexto.includes('Usuario Gmail')) {
      nombreCampo = 'smtp_user';
    } else if (labelTexto.includes('Contraseña de Aplicación') || placeholder.includes('App Password')) {
      nombreCampo = 'smtp_password';
    } else if (labelTexto.includes('Email del Remitente') || labelTexto.includes('Remitente')) {
      nombreCampo = 'from_email';
    } else if (labelTexto.includes('Nombre del Remitente')) {
      nombreCampo = 'from_name';
    } else if (placeholder.includes('pruebas@ejemplo.com')) {
      nombreCampo = 'email_pruebas';
    }
    
    if (nombreCampo && visible) {
      camposEncontrados[nombreCampo] = {
        valor: valor,
        vacio: vacio,
        placeholder: placeholder,
        label: labelTexto,
        tipo: tipo
      };
    }
  });
  
  // Buscar checkbox de TLS
  const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'));
  checkboxes.forEach(cb => {
    const label = cb.nextElementSibling;
    if (label && label.textContent.includes('Usar TLS')) {
      camposEncontrados['smtp_use_tls'] = {
        valor: cb.checked ? 'true' : 'false',
        vacio: false,
        placeholder: '',
        label: label.textContent.trim(),
        tipo: 'checkbox'
      };
    }
  });
  
  // Buscar radio buttons de modo_pruebas
  const radios = Array.from(document.querySelectorAll('input[type="radio"][name="ambiente"]'));
  const radioSeleccionado = radios.find(r => r.checked);
  if (radioSeleccionado) {
    camposEncontrados['modo_pruebas'] = {
      valor: radioSeleccionado.value,
      vacio: false,
      placeholder: '',
      label: radioSeleccionado.closest('label')?.textContent.trim() || '',
      tipo: 'radio'
    };
  }
  
  // Mostrar resultados
  console.log('📋 CAMPOS ENCONTRADOS:\n');
  const camposEsperados = ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email', 'from_name', 'smtp_use_tls', 'modo_pruebas', 'email_pruebas'];
  
  camposEsperados.forEach(nombre => {
    const campo = camposEncontrados[nombre];
    if (campo) {
      const estado = campo.vacio ? '❌ VACÍO' : '✅ CON VALOR';
      console.log(`${estado} - ${nombre}:`);
      console.log(`    Valor: ${campo.valor.substring(0, 50)}`);
      console.log(`    Label: ${campo.label || '(sin label)'}`);
      console.log(`    Placeholder: ${campo.placeholder || '(sin placeholder)'}`);
      console.log('');
    } else {
      console.log(`⚠️ ${nombre}: NO ENCONTRADO\n`);
    }
  });
  
  // Buscar botón Guardar
  console.log('🔘 BUSCANDO BOTÓN GUARDAR:\n');
  const todosLosBotones = Array.from(document.querySelectorAll('button'));
  const botonGuardar = todosLosBotones.find(b => {
    const texto = b.textContent.toLowerCase();
    return texto.includes('guardar') || texto.includes('save');
  });
  
  if (botonGuardar) {
    console.log('✅ Botón encontrado:');
    console.log(`   Texto: "${botonGuardar.textContent.trim()}"`);
    console.log(`   Deshabilitado: ${botonGuardar.disabled ? '❌ SÍ' : '✅ NO'}`);
    console.log(`   Visible: ${botonGuardar.offsetParent !== null ? '✅ SÍ' : '❌ NO'}`);
    console.log(`   Opacity: ${window.getComputedStyle(botonGuardar).opacity}`);
    console.log(`   Cursor: ${window.getComputedStyle(botonGuardar).cursor}`);
    console.log(`   Pointer-events: ${window.getComputedStyle(botonGuardar).pointerEvents}`);
  } else {
    console.log('❌ Botón Guardar NO encontrado');
    console.log(`   Total de botones en la página: ${todosLosBotones.length}`);
    console.log('   Botones encontrados:');
    todosLosBotones.slice(0, 10).forEach((b, i) => {
      console.log(`     ${i + 1}. "${b.textContent.trim()}"`);
    });
  }
  
  // Resumen
  console.log('\n' + '='.repeat(60));
  console.log('📊 RESUMEN:');
  console.log(`   Campos encontrados: ${Object.keys(camposEncontrados).length}`);
  console.log(`   Campos vacíos: ${Object.values(camposEncontrados).filter(c => c.vacio).length}`);
  console.log(`   Campos con valor: ${Object.values(camposEncontrados).filter(c => !c.vacio).length}`);
  console.log(`   Botón Guardar: ${botonGuardar ? (botonGuardar.disabled ? '❌ DESHABILITADO' : '✅ HABILITADO') : '❌ NO ENCONTRADO'}`);
  
  return {
    campos: camposEncontrados,
    botonHabilitado: botonGuardar ? !botonGuardar.disabled : false,
    totalCampos: Object.keys(camposEncontrados).length
  };
})();

