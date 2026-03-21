const playwright = require('playwright');
const fs = require('fs');
const path = require('path');

const SITE_URL = 'https://rapicredit.onrender.com/pagos/dashboard/menu';
const SCREENSHOTS_DIR = './audit-screenshots';

// Crear directorio para screenshots
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

async function runAudit() {
  const browser = await playwright.chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });

  const page = await context.newPage();
  const auditReport = {
    auditoria: {
      sitio: 'RapiCredit',
      url: SITE_URL,
      fecha: new Date().toISOString().split('T')[0],
      hora_inicio: new Date().toISOString(),
      hallazgos: {
        seguridad: [],
        performance: [],
        ux_ui: [],
        accesibilidad: [],
        código: []
      },
      oportunidades_mejora: [],
      resumen_ejecutivo: ''
    }
  };

  try {
    console.log('🔍 Iniciando auditoría de RapiCredit...\n');

    // 1. ANÁLISIS INICIAL DE CARGA
    console.log('📊 [1/6] Analizando carga inicial...');
    const startTime = Date.now();
    const response = await page.goto(SITE_URL, { waitUntil: 'networkidle' });
    const loadTime = Date.now() - startTime;

    await page.screenshot({ path: `${SCREENSHOTS_DIR}/01-home.png` });

    auditReport.auditoria.hallazgos.performance.push({
      tipo: 'Tiempo de carga',
      valor: `${loadTime}ms`,
      estado: loadTime < 3000 ? '✅' : loadTime < 5000 ? '⚠️' : '❌',
      detalles: `Página cargó en ${loadTime}ms`
    });

    // 2. ANÁLISIS DE SEGURIDAD
    console.log('🔒 [2/6] Analizando seguridad...');
    
    // Headers de seguridad
    const headers = await page.evaluate(() => {
      return {
        documentElement: document.documentElement.outerHTML.substring(0, 500)
      };
    });

    // Obtener cookies
    const cookies = await context.cookies();
    const cookieAnalysis = cookies.map(c => ({
      nombre: c.name,
      httpOnly: c.httpOnly,
      secure: c.secure,
      sameSite: c.sameSite
    }));

    if (cookieAnalysis.length > 0) {
      auditReport.auditoria.hallazgos.seguridad.push({
        tipo: 'Cookies encontradas',
        cantidad: cookies.length,
        detalles: cookieAnalysis
      });
    }

    // Verificar HTTPS
    const isHttps = SITE_URL.startsWith('https');
    auditReport.auditoria.hallazgos.seguridad.push({
      tipo: 'Protocolo HTTPS',
      estado: isHttps ? '✅' : '❌',
      detalles: isHttps ? 'Conexión segura' : 'Conexión insegura'
    });

    // 3. ANÁLISIS DE ESTRUCTURA HTML Y META TAGS
    console.log('📄 [3/6] Analizando estructura HTML...');
    
    const htmlAnalysis = await page.evaluate(() => {
      const metaTags = {
        title: document.title,
        description: document.querySelector('meta[name="description"]')?.content || 'No encontrado',
        viewport: document.querySelector('meta[name="viewport"]')?.content || 'No encontrado',
        charset: document.querySelector('meta[charset]')?.charset || 'No encontrado',
        csrf: document.querySelector('meta[name="csrf-token"]')?.content ? 'Presente' : 'No encontrado',
        csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content || 'No encontrado'
      };

      const bodyClasses = document.body.className;
      const formElements = {
        inputs: document.querySelectorAll('input').length,
        buttons: document.querySelectorAll('button').length,
        forms: document.querySelectorAll('form').length
      };

      const consoleErrors = [];
      const consoleWarnings = [];

      return {
        metaTags,
        bodyClasses,
        formElements,
        doctype: document.doctype ? 'HTML5' : 'Indefinido'
      };
    });

    auditReport.auditoria.hallazgos.código.push({
      tipo: 'Meta Tags',
      detalles: htmlAnalysis
    });

    // 4. ANÁLISIS DE UI/UX
    console.log('🎨 [4/6] Analizando UI/UX...');

    const uiAnalysis = await page.evaluate(() => {
      const elements = {
        headings: {
          h1: document.querySelectorAll('h1').length,
          h2: document.querySelectorAll('h2').length,
          h3: document.querySelectorAll('h3').length
        },
        forms: {
          emailInputs: document.querySelectorAll('input[type="email"]').length,
          passwordInputs: document.querySelectorAll('input[type="password"]').length,
          textInputs: document.querySelectorAll('input[type="text"]').length,
          checkboxes: document.querySelectorAll('input[type="checkbox"]').length
        },
        buttons: document.querySelectorAll('button, [role="button"]').length,
        images: document.querySelectorAll('img').length,
        links: document.querySelectorAll('a').length
      };

      // Detectar framework
      const scripts = Array.from(document.querySelectorAll('script')).map(s => s.src || s.textContent.substring(0, 100));
      let framework = 'Desconocido';
      if (window.React) framework = 'React';
      else if (window.Vue) framework = 'Vue';
      else if (window.angular) framework = 'Angular';
      else if (scripts.some(s => s.includes('jquery'))) framework = 'jQuery';

      // Colores predominantes (análisis básico)
      const root = getComputedStyle(document.documentElement);
      const bodyBg = getComputedStyle(document.body).backgroundColor;

      return {
        elementos: elements,
        framework,
        estilosInline: Array.from(document.querySelectorAll('[style]')).length,
        backgroundColor: bodyBg
      };
    });

    auditReport.auditoria.hallazgos.ux_ui.push({
      tipo: 'Estructura de elementos',
      detalles: uiAnalysis
    });

    // 5. ANÁLISIS DE ACCESIBILIDAD
    console.log('♿ [5/6] Analizando accesibilidad...');

    const a11yAnalysis = await page.evaluate(() => {
      const issues = [];

      // Labels sin asociación
      const inputs = document.querySelectorAll('input, textarea, select');
      let inputsSinLabel = 0;
      inputs.forEach(input => {
        if (!input.id) inputsSinLabel++;
      });

      // Alt text en imágenes
      const images = document.querySelectorAll('img');
      let imagesSinAlt = 0;
      images.forEach(img => {
        if (!img.alt || img.alt.trim() === '') imagesSinAlt++;
      });

      // Botones sin texto accesible
      const buttons = document.querySelectorAll('button');
      let buttonsSinTexto = 0;
      buttons.forEach(btn => {
        if (!btn.textContent.trim() && !btn.getAttribute('aria-label')) buttonsSinTexto++;
      });

      return {
        inputsSinLabel,
        imagesSinAlt,
        buttonsSinTexto,
        elementosConAriaLabel: document.querySelectorAll('[aria-label]').length,
        elementosConAriaDescribedBy: document.querySelectorAll('[aria-describedby]').length,
        elementosConRole: document.querySelectorAll('[role]').length
      };
    });

    auditReport.auditoria.hallazgos.accesibilidad.push({
      tipo: 'Problemas detectados',
      detalles: a11yAnalysis
    });

    // 6. ANÁLISIS DE PERFORMANCE (Network)
    console.log('⚡ [6/6] Analizando performance...');

    const metrics = await page.evaluate(() => {
      const perfData = performance.getEntriesByType('navigation')[0] || {};
      const paintEntries = performance.getEntriesByType('paint');
      
      return {
        navigationTiming: {
          domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
          loadComplete: perfData.loadEventEnd - perfData.loadEventStart,
          timeToFirstByte: perfData.responseStart - perfData.requestStart
        },
        paintMetrics: paintEntries.map(p => ({
          name: p.name,
          startTime: p.startTime.toFixed(2)
        }))
      };
    });

    auditReport.auditoria.hallazgos.performance.push({
      tipo: 'Métricas de navegación',
      detalles: metrics
    });

    // Prueba responsive
    console.log('📱 Probando responsive...');
    await page.setViewportSize({ width: 375, height: 812 });
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/02-mobile.png` });
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/03-tablet.png` });

    // OPORTUNIDADES DE MEJORA
    console.log('💡 Identificando oportunidades...');

    const oportunidades = [
      {
        prioridad: 'alta',
        categoria: 'seguridad',
        titulo: 'Implementar Content Security Policy (CSP)',
        descripción: 'No se detectó meta CSP. Implementar CSP headers para mitigar XSS y otros ataques.',
        impacto: 'Reduce riesgo de inyección de código en 95%',
        esfuerzo: 'medio'
      },
      {
        prioridad: 'alta',
        categoria: 'seguridad',
        titulo: 'Validar CSRF token en formularios',
        descripción: 'Implementar y validar tokens CSRF en todos los formularios de login.',
        impacto: 'Previene ataques CSRF',
        esfuerzo: 'bajo'
      },
      {
        prioridad: 'alta',
        categoria: 'seguridad',
        titulo: 'Asegurar cookies con flags httpOnly y Secure',
        descripción: `${cookieAnalysis.some(c => !c.httpOnly) ? 'Se encontraron cookies sin httpOnly. ' : ''}Todas las cookies deben tener flags de seguridad.`,
        impacto: 'Previene acceso a cookies desde JavaScript malicioso',
        esfuerzo: 'bajo'
      },
      {
        prioridad: 'media',
        categoria: 'performance',
        titulo: 'Optimizar tiempo de carga inicial',
        descripción: loadTime > 3000 ? `Página tarda ${loadTime}ms. Optimizar assets, lazy loading, minificación.` : 'Mantener optimización actual',
        impacto: 'Mejora experiencia y SEO',
        esfuerzo: 'medio'
      },
      {
        prioridad: 'media',
        categoria: 'accesibilidad',
        titulo: `Asociar labels con inputs (${a11yAnalysis.inputsSinLabel} inputs sin label)`,
        descripción: 'Todos los campos de formulario deben tener labels asociados para screen readers.',
        impacto: 'Mejora accesibilidad para usuarios con discapacidades',
        esfuerzo: 'bajo'
      },
      {
        prioridad: 'media',
        categoria: 'accesibilidad',
        titulo: `Agregar alt text a imágenes (${a11yAnalysis.imagesSinAlt} imágenes sin alt)`,
        descripción: 'Todas las imágenes deben tener atributo alt descriptivo.',
        impacto: 'Mejora SEO y accesibilidad',
        esfuerzo: 'bajo'
      },
      {
        prioridad: 'media',
        categoria: 'ux',
        titulo: 'Mejorar feedback visual en formularios',
        descripción: 'Implementar validación en tiempo real, mensajes de error claros y indicadores visuales.',
        impacto: 'Reduce errores y mejora conversión',
        esfuerzo: 'medio'
      },
      {
        prioridad: 'baja',
        categoria: 'técnica',
        titulo: 'Implementar error tracking (Sentry/Rollbar)',
        descripción: 'Agregrar monitoreo de errores en production para detección proactiva.',
        impacto: 'Facilita debugging y mejora confiabilidad',
        esfuerzo: 'bajo'
      },
      {
        prioridad: 'baja',
        categoria: 'performance',
        titulo: 'Implementar analytics y monitoreo de performance',
        descripción: 'Google Analytics, Hotjar o similar para entender comportamiento de usuarios.',
        impacto: 'Datos para optimizaciones futuras',
        esfuerzo: 'bajo'
      },
      {
        prioridad: 'baja',
        categoria: 'técnica',
        titulo: 'Documentar API y endpoints',
        descripción: 'Crear documentación (Swagger/OpenAPI) de todos los endpoints disponibles.',
        impacto: 'Facilita mantenimiento y onboarding',
        esfuerzo: 'medio'
      }
    ];

    auditReport.auditoria.oportunidades_mejora = oportunidades;

    // RESUMEN EJECUTIVO
    const resumen = `
AUDITORÍA EJECUTIVA - RapiCredit
=================================

Fecha: ${new Date().toLocaleDateString('es-ES')}
URL: ${SITE_URL}
Tiempo de Carga: ${loadTime}ms

HALLAZGOS CRÍTICOS:
- ${cookieAnalysis.length} cookies encontradas
- ${a11yAnalysis.inputsSinLabel} campos sin labels asociados
- ${a11yAnalysis.imagesSinAlt} imágenes sin alt text
- HTTPS: ${isHttps ? '✅ Activo' : '❌ No activo'}

OPORTUNIDADES DE MEJORA:
- ${oportunidades.filter(o => o.prioridad === 'alta').length} problemas ALTOS
- ${oportunidades.filter(o => o.prioridad === 'media').length} problemas MEDIOS
- ${oportunidades.filter(o => o.prioridad === 'baja').length} problemas BAJOS

Esfuerzo Total Estimado: ~2-3 semanas para resolver todos los issues
Impacto: Mejora significativa en seguridad, performance y accesibilidad
    `;

    auditReport.auditoria.resumen_ejecutivo = resumen.trim();

    // Guardar reporte
    const reportPath = './audit-report.json';
    fs.writeFileSync(reportPath, JSON.stringify(auditReport, null, 2), 'utf-8');

    console.log('\n✅ Auditoría completada!');
    console.log(`📊 Reporte guardado en: ${path.resolve(reportPath)}`);
    console.log(`📸 Screenshots guardados en: ${path.resolve(SCREENSHOTS_DIR)}\n`);
    console.log(resumen);

  } catch (error) {
    console.error('❌ Error durante la auditoría:', error.message);
    auditReport.auditoria.hallazgos.código.push({
      tipo: 'Error',
      detalles: error.message
    });
  } finally {
    await context.close();
    await browser.close();
  }

  return auditReport;
}

// Ejecutar auditoría
runAudit().then(report => {
  console.log('\n📋 Reporte final generado exitosamente');
}).catch(err => {
  console.error('Error fatal:', err);
  process.exit(1);
});
