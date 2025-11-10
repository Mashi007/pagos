// ============================================
// CÓDIGO PARA HABILITAR BOTÓN GUARDAR
// Copiar y pegar en la consola del navegador (F12 → Console)
// ============================================

// Método 1: Buscar por texto
const buscarBotonPorTexto = () => {
  const buttons = Array.from(document.querySelectorAll('button'));
  const guardarButton = buttons.find(b => 
    b.textContent.includes('Guardar') || 
    b.textContent.includes('guardar') ||
    b.textContent.includes('Guardar Configuración')
  );
  return guardarButton;
};

// Método 2: Buscar por clase o atributos
const buscarBotonPorAtributos = () => {
  // Buscar botones con clase que contenga "blue" o "save"
  const buttons = Array.from(document.querySelectorAll('button'));
  return buttons.find(b => 
    b.className.includes('blue') || 
    b.className.includes('bg-blue') ||
    b.getAttribute('type') === 'button'
  );
};

// Método 3: Buscar todos los botones y mostrar información
const diagnosticarBotones = () => {
  const buttons = Array.from(document.querySelectorAll('button'));
  console.log('Total de botones encontrados:', buttons.length);
  buttons.forEach((btn, index) => {
    console.log(`Botón ${index + 1}:`, {
      texto: btn.textContent.trim(),
      disabled: btn.disabled,
      visible: btn.offsetParent !== null,
      clases: btn.className,
      estilos: window.getComputedStyle(btn).display
    });
  });
  return buttons;
};

// Ejecutar diagnóstico primero
console.log('🔍 Diagnosticando botones...');
const todosLosBotones = diagnosticarBotones();

// Intentar encontrar el botón de Guardar
let botonGuardar = buscarBotonPorTexto();

if (!botonGuardar) {
  console.log('⚠️ No se encontró por texto, buscando por atributos...');
  botonGuardar = buscarBotonPorAtributos();
}

if (botonGuardar) {
  console.log('✅ Botón encontrado:', botonGuardar);
  console.log('Estado actual:', {
    disabled: botonGuardar.disabled,
    visible: botonGuardar.offsetParent !== null,
    texto: botonGuardar.textContent.trim()
  });
  
  // Habilitar el botón
  botonGuardar.disabled = false;
  botonGuardar.style.opacity = '1';
  botonGuardar.style.cursor = 'pointer';
  botonGuardar.style.pointerEvents = 'auto';
  
  // Asegurar que sea visible
  botonGuardar.style.display = 'flex';
  botonGuardar.style.visibility = 'visible';
  
  console.log('✅ Botón habilitado y visible');
  console.log('Nuevo estado:', {
    disabled: botonGuardar.disabled,
    visible: botonGuardar.offsetParent !== null
  });
  
  // Hacer scroll hasta el botón
  botonGuardar.scrollIntoView({ behavior: 'smooth', block: 'center' });
  
} else {
  console.log('❌ No se encontró el botón de Guardar');
  console.log('💡 Intenta hacer scroll hacia abajo en la página para ver si el botón está más abajo');
}

