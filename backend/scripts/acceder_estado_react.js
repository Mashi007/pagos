// ============================================
// ACCEDER AL ESTADO DE REACT DEL COMPONENTE
// Para verificar los valores reales en el estado
// ============================================

(() => {
  console.log('🔍 ACCEDIENDO AL ESTADO DE REACT\n');
  console.log('='.repeat(60));

  // Buscar el botón Guardar para acceder al componente React
  const botonGuardar = Array.from(document.querySelectorAll('button')).find(
    b => b.textContent.includes('Guardar')
  );

  if (!botonGuardar) {
    console.log('❌ No se encontró el botón Guardar');
    return;
  }

  console.log('✅ Botón Guardar encontrado\n');

  // Intentar acceder al componente React
  const reactKey = Object.keys(botonGuardar).find(key =>
    key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')
  );

  if (!reactKey) {
    console.log('❌ No se pudo acceder al componente React');
    return;
  }

  console.log('✅ Componente React encontrado\n');

  // Navegar por el árbol de React para encontrar el estado
  let fiber = botonGuardar[reactKey];
  let componente = null;

  // Buscar el componente EmailConfig
  for (let i = 0; i < 50 && fiber; i++) {
    if (fiber.memoizedState || fiber.stateNode) {
      const stateNode = fiber.stateNode;
      if (stateNode && stateNode.state) {
        // Puede ser un componente de clase
        componente = stateNode;
        break;
      }
      if (stateNode && stateNode.props) {
        // Puede ser un componente funcional con hooks
        const props = stateNode.props;
        if (props.children || props.onClick) {
          // Buscar en el return del componente
        }
      }
    }

    // Buscar en el return del componente (memoizedProps)
    if (fiber.memoizedProps) {
      const props = fiber.memoizedProps;
      // Intentar encontrar el estado a través de los props
    }

    // Subir al componente padre
    fiber = fiber.return;
  }

  // Método alternativo: buscar inputs y verificar sus valores directamente
  console.log('📋 VERIFICANDO VALORES DIRECTAMENTE EN LOS INPUTS:\n');

  const inputs = Array.from(document.querySelectorAll('input, textarea'))
    .filter(inp => inp.offsetParent !== null);

  const campos = {
    smtp_host: null,
    smtp_port: null,
    smtp_user: null,
    smtp_password: null,
    from_email: null,
    from_name: null,
    smtp_use_tls: null
  };

  // Identificar por posición y tipo
  inputs.forEach((inp, i) => {
    const tipo = inp.type || 'text';
    const valor = inp.value || '';

    // smtp_host - primer input text con "smtp.gmail.com"
    if (i === 0 && valor.includes('smtp')) {
      campos.smtp_host = valor;
      console.log(`✅ smtp_host: "${valor}"`);
    }
    // smtp_port - segundo input text con "587"
    else if (i === 1 && valor === '587') {
      campos.smtp_port = valor;
      console.log(`✅ smtp_port: "${valor}"`);
    }
    // smtp_user - primer input email
    else if (tipo === 'email' && !campos.smtp_user) {
      campos.smtp_user = valor;
      console.log(`✅ smtp_user: "${valor}"`);
    }
    // smtp_password - input password
    else if (tipo === 'password') {
      campos.smtp_password = valor ? '***' : '';
      console.log(`✅ smtp_password: ${valor ? '*** (tiene valor)' : '(vacío)'}`);
    }
    // from_email - segundo input email
    else if (tipo === 'email' && campos.smtp_user) {
      campos.from_email = valor;
      console.log(`✅ from_email: "${valor}"`);
    }
    // from_name - input text con "RapiCredit"
    else if (tipo === 'text' && valor === 'RapiCredit') {
      campos.from_name = valor;
      console.log(`✅ from_name: "${valor}"`);
    }
    // smtp_use_tls - checkbox
    else if (tipo === 'checkbox') {
      const label = inp.nextElementSibling;
      if (label && label.textContent.includes('TLS')) {
        campos.smtp_use_tls = inp.checked ? 'true' : 'false';
        console.log(`✅ smtp_use_tls: ${inp.checked ? 'true' : 'false'}`);
      }
    }
  });

  // Verificar campos obligatorios
  console.log('\n' + '='.repeat(60));
  console.log('📋 RESUMEN DE VALIDACIÓN:\n');

  const camposObligatorios = {
    'smtp_host': campos.smtp_host,
    'smtp_port': campos.smtp_port,
    'smtp_user': campos.smtp_user,
    'smtp_password': campos.smtp_password,
    'from_email': campos.from_email,
    'smtp_use_tls': campos.smtp_use_tls
  };

  const camposFaltantes = [];

  Object.entries(camposObligatorios).forEach(([nombre, valor]) => {
    const vacio = !valor || valor.trim() === '';
    if (vacio) {
      camposFaltantes.push(nombre);
      console.log(`❌ ${nombre}: VACÍO`);
    } else {
      console.log(`✅ ${nombre}: "${valor}"`);
    }
  });

  // Validaciones específicas para Gmail
  if (campos.smtp_host?.includes('gmail.com')) {
    console.log('\n🔍 VALIDACIONES PARA GMAIL:');
    const puerto = parseInt(campos.smtp_port || '0');
    const tls = campos.smtp_use_tls === 'true';

    if (puerto === 587 && !tls) {
      console.log('❌ Puerto 587 requiere TLS habilitado');
      camposFaltantes.push('smtp_use_tls (debe ser true para puerto 587)');
    }

    if (!campos.smtp_password || campos.smtp_password.trim() === '') {
      console.log('❌ Gmail requiere contraseña');
      camposFaltantes.push('smtp_password');
    }
  }

  if (camposFaltantes.length > 0) {
    console.log(`\n❌ CAMPOS FALTANTES: ${camposFaltantes.join(', ')}`);
    console.log('\n💡 RAZÓN POR LA QUE EL BOTÓN ESTÁ DESHABILITADO:');
    console.log(`   Faltan los siguientes campos: ${camposFaltantes.join(', ')}`);
  } else {
    console.log(`\n✅ TODOS LOS CAMPOS OBLIGATORIOS ESTÁN COMPLETOS`);
    console.log('\n⚠️ Si el botón sigue deshabilitado, puede ser un problema de validación en el código React.');
  }

  return { campos, camposFaltantes };
})();

