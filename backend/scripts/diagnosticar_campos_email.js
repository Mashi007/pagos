// ============================================
// DIAGNOSTICAR CAMPOS DE CONFIGURACIÓN EMAIL
// Este código identifica qué campos están vacíos o tienen problemas
// ============================================

(() => {
  console.log('🔍 Analizando campos del formulario de email...\n');

  // Buscar todos los inputs
  const inputs = document.querySelectorAll('input[type="text"], input[type="password"], input[type="email"], textarea');

  const camposVacios = [];
  const camposConValor = [];

  inputs.forEach((input, index) => {
    const info = {
      index,
      value: input.value,
      name: input.name || '(sin name)',
      id: input.id || '(sin id)',
      placeholder: input.placeholder || '(sin placeholder)',
      type: input.type || input.tagName.toLowerCase(),
      label: null,
      required: input.hasAttribute('required'),
      disabled: input.disabled,
      visible: input.offsetParent !== null
    };

    // Intentar encontrar el label asociado
    if (input.id) {
      const label = document.querySelector(`label[for="${input.id}"]`);
      if (label) {
        info.label = label.textContent.trim();
      }
    }

    // Si no hay label por for, buscar el label padre
    if (!info.label) {
      const labelParent = input.closest('label');
      if (labelParent) {
        info.label = labelParent.textContent.trim();
      }
    }

    // Buscar label anterior
    if (!info.label) {
      let prev = input.previousElementSibling;
      while (prev && !info.label) {
        if (prev.tagName === 'LABEL') {
          info.label = prev.textContent.trim();
        }
        prev = prev.previousElementSibling;
      }
    }

    // Verificar si está vacío
    const isEmpty = !input.value || input.value.trim() === '';

    if (isEmpty && info.visible) {
      camposVacios.push(info);
    } else if (!isEmpty && info.visible) {
      camposConValor.push(info);
    }
  });

  console.log('📋 RESUMEN DE CAMPOS:\n');

  if (camposVacios.length > 0) {
    console.log('❌ CAMPOS VACÍOS:');
    camposVacios.forEach(campo => {
      console.log(`  - ${campo.label || campo.placeholder || campo.name || campo.id}`);
      console.log(`    Tipo: ${campo.type}, Name: ${campo.name}, ID: ${campo.id}`);
      console.log(`    Requerido: ${campo.required ? 'Sí' : 'No'}`);
      console.log('');
    });
  } else {
    console.log('✅ No hay campos vacíos visibles\n');
  }

  if (camposConValor.length > 0) {
    console.log('✅ CAMPOS CON VALOR:');
    camposConValor.forEach(campo => {
      const valorOculto = campo.type === 'password' ? '***' : campo.value.substring(0, 30);
      console.log(`  - ${campo.label || campo.placeholder || campo.name || campo.id}: ${valorOculto}`);
    });
    console.log('');
  }

  // Buscar el botón Guardar
  const botonGuardar = Array.from(document.querySelectorAll('button')).find(
    b => b.textContent.includes('Guardar') || b.textContent.includes('guardar')
  );

  if (botonGuardar) {
    console.log('🔘 ESTADO DEL BOTÓN GUARDAR:');
    console.log(`  - Habilitado: ${!botonGuardar.disabled ? 'Sí ✅' : 'No ❌'}`);
    console.log(`  - Visible: ${botonGuardar.offsetParent !== null ? 'Sí ✅' : 'No ❌'}`);
    console.log(`  - Clases: ${botonGuardar.className}`);
    console.log(`  - Estilos: opacity=${window.getComputedStyle(botonGuardar).opacity}`);
    console.log('');

    // Intentar encontrar el componente React para ver el estado de validación
    const reactKey = Object.keys(botonGuardar).find(key =>
      key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')
    );

    if (reactKey) {
      console.log('⚛️ Componente React encontrado');
    }
  } else {
    console.log('❌ No se encontró el botón Guardar');
  }

  // Buscar mensajes de error o validación
  const mensajesError = document.querySelectorAll('[role="alert"], .error, .text-red, [class*="error"]');
  if (mensajesError.length > 0) {
    console.log('⚠️ MENSAJES DE ERROR ENCONTRADOS:');
    mensajesError.forEach((msg, i) => {
      if (msg.textContent.trim()) {
        console.log(`  ${i + 1}. ${msg.textContent.trim()}`);
      }
    });
  }

  return {
    camposVacios: camposVacios.length,
    camposConValor: camposConValor.length,
    botonHabilitado: botonGuardar ? !botonGuardar.disabled : false
  };
})();

