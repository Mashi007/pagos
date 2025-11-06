import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { existsSync, readdirSync } from 'fs';
import { createProxyMiddleware } from 'http-proxy-middleware';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
// URL del backend - Prioridad: API_BASE_URL (runtime) > VITE_API_BASE_URL (build-time fallback) > VITE_API_URL > localhost
// ⚠️ IMPORTANTE: En Render, DEBE estar configurada la variable API_BASE_URL (SIN prefijo VITE_)
// Las variables VITE_* solo funcionan durante el build, NO en runtime de Node.js
// Si falta API_BASE_URL, el proxy no funcionará y verás 404 en las peticiones /api/*
const API_URL = process.env.API_BASE_URL || process.env.VITE_API_BASE_URL || process.env.VITE_API_URL || 'http://localhost:8000';

// Log de la URL configurada para debug
console.log(`🔍 API_URL configurado: ${API_URL || 'NO CONFIGURADO'}`);
console.log(`🔍 API_BASE_URL (runtime): ${process.env.API_BASE_URL || 'NO SET'}`);
console.log(`🔍 VITE_API_BASE_URL (build-time): ${process.env.VITE_API_BASE_URL || 'NO SET'}`);
console.log(`🔍 VITE_API_URL (build-time): ${process.env.VITE_API_URL || 'NO SET'}`);

// ============================================
// SECURITY HEADERS - OWASP Best Practices
// ============================================
app.disable('x-powered-by');

// Middleware para security headers
app.use((req, res, next) => {
  // Prevenir MIME sniffing
  res.setHeader('X-Content-Type-Options', 'nosniff');
  
  // Prevenir clickjacking
  res.setHeader('X-Frame-Options', 'DENY');
  
  // XSS Protection
  res.setHeader('X-XSS-Protection', '1; mode=block');
  
  // HSTS - Solo en producción
  if (process.env.NODE_ENV === 'production') {
    res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  }
  
  // Content Security Policy
  res.setHeader(
    'Content-Security-Policy',
    "default-src 'self'; " +
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; " +
    "style-src 'self' 'unsafe-inline'; " +
    "img-src 'self' data: https:; " +
    "font-src 'self' data:; " +
    "connect-src 'self' " + API_URL
  );
  
  // Referrer Policy
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  
  // Permissions Policy
  res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');
  
  next();
});

// ============================================
// LOGGING MIDDLEWARE - Para debug de peticiones
// ============================================
// Reducir logging en producción para mejorar rendimiento
// En Render, PORT siempre está configurado, así que si PORT existe y NODE_ENV no es 'development', es producción
const isDevelopment = process.env.NODE_ENV === 'development';
const isProduction = process.env.NODE_ENV === 'production' || 
                     (process.env.PORT && process.env.NODE_ENV !== 'development');

// Log de diagnóstico solo al inicio
if (!isDevelopment) {
  console.log(`🔇 Logging reducido en producción (NODE_ENV=${process.env.NODE_ENV || 'undefined'}, PORT=${process.env.PORT || 'undefined'})`);
}

app.use((req, res, next) => {
  // Solo loggear en desarrollo - en producción no loggear nada para mejorar rendimiento
  if (isDevelopment && req.path.startsWith('/api')) {
    console.log(`📥 [${req.method}] Petición API recibida: ${req.path}`);
  }
  // En producción, no loggear nada aquí para reducir overhead
  next();
});

// ============================================
// PROXY /api -> Backend (Render)
// ============================================
// IMPORTANTE: Proxy debe ir ANTES de servir archivos estáticos
// Usar app.use('/api', ...) para que Express maneje el routing
// Esto asegura que SOLO rutas /api pasen por el proxy
if (API_URL && API_URL !== 'http://localhost:8000') {
  console.log(`➡️  Proxy de /api hacia: ${API_URL}`);
  const proxyMiddleware = createProxyMiddleware({
    target: API_URL,
    changeOrigin: true,
    xfwd: true,
    logLevel: isDevelopment ? 'info' : 'warn', // Reducir verbosidad en producción
    // IMPORTANTE: Cuando usamos app.use('/api', ...), Express elimina el /api del req.path
    // Ejemplo: /api/v1/clientes -> req.path = /v1/clientes
    // Necesitamos reconstruirlo: /v1/clientes -> /api/v1/clientes
    pathRewrite: (path, req) => {
      // El path que llega ya NO tiene /api (Express lo eliminó cuando usamos app.use('/api', ...))
      // Ejemplo: /api/v1/modelos-vehiculos -> path recibido = /v1/modelos-vehiculos
      // Necesitamos agregar /api de vuelta: /v1/modelos-vehiculos -> /api/v1/modelos-vehiculos
      // IMPORTANTE: El query string se preserva automáticamente por http-proxy-middleware
      // NO debemos agregarlo manualmente aquí
      const rewritten = `/api${path}`;
      // Solo loggear en desarrollo
      if (isDevelopment) {
        console.log(`🔄 Path rewrite: "${path}" -> "${rewritten}"`);
      }
      return rewritten;
    },
    // Seguir redirects del backend (3xx)
    followRedirects: true,
    // No cambiar el protocolo
    secure: true,
    onError: (err, req, res) => {
      console.error(`❌ Error en proxy para ${req.method} ${req.originalUrl || req.url}:`, err.message);
      if (!res.headersSent) {
        res.status(502).json({
          error: 'Proxy error',
          message: err.message,
          target: API_URL,
          path: req.path,
          originalUrl: req.originalUrl,
          method: req.method
        });
      }
    },
    onProxyReq: (proxyReq, req, res) => {
      // Este callback se ejecuta DESPUÉS del pathRewrite
      // El proxyReq ya tiene el path reescrito y el query string se preserva automáticamente
      // IMPORTANTE: NO debemos modificar el query string manualmente - http-proxy-middleware lo maneja
      
      // Solo loggear detalles en desarrollo
      if (isDevelopment) {
        const queryString = proxyReq.path.includes('?') ? proxyReq.path.split('?')[1] : '';
        console.log(`➡️  [${req.method}] Proxying: ${req.path}`);
        console.log(`   Target: ${API_URL}${proxyReq.path}`);
      }
      
      // Asegurar que los headers se copien correctamente
      const authHeader = req.headers.authorization || req.headers.Authorization;
      if (authHeader) {
        proxyReq.setHeader('Authorization', authHeader);
      }
      
      // Copiar otros headers importantes
      if (req.headers.cookie) {
        proxyReq.setHeader('Cookie', req.headers.cookie);
      }
      
      // Configurar timeout para evitar peticiones colgadas
      proxyReq.setTimeout(60000); // 60 segundos
    },
    onProxyRes: (proxyRes, req, res) => {
      const status = proxyRes.statusCode;
      // Solo loggear errores en producción, todo en desarrollo
      if (!isDevelopment && status >= 400) {
        const emoji = status >= 400 ? '❌' : '⚠️';
        console.log(`${emoji} [${req.method}] ${status} ${req.path}`);
        if (status === 404) {
          console.error(`   ❌ ERROR 404 - El backend no encontró la ruta: ${API_URL}${proxyRes.req?.path || req.path}`);
        }
      } else if (isDevelopment) {
        const emoji = status >= 200 && status < 300 ? '✅' : status >= 400 ? '❌' : '⚠️';
        console.log(`${emoji} [${req.method}] Proxy response: ${status} para ${req.originalUrl || req.url}`);
      }
    },
    onProxyError: (err, req, res) => {
      console.error(`❌ ERROR en proxy durante la petición: ${err.message}`);
      console.error(`   URL: ${req.originalUrl || req.url}`);
      console.error(`   Target: ${API_URL}`);
      console.error(`   Stack: ${err.stack}`);
      if (!res.headersSent) {
        res.status(502).json({
          error: 'Proxy error',
          message: err.message,
          target: API_URL,
          path: req.path
        });
      }
    }
  });
  
  // IMPORTANTE: Usar app.use('/api', ...) para que Express maneje el routing
  // Esto asegura que SOLO rutas que empiecen con /api pasen por el proxy
  // Las rutas como /clientes, /assets/*.js, etc. NO pasarán por aquí
  app.use('/api', proxyMiddleware);
  
  // También registrar explícitamente para debug
  console.log('✅ Proxy middleware registrado para rutas /api/*');
} else {
  console.warn('⚠️  API_URL no configurado. Proxy deshabilitado.');
}

// ============================================
// VALIDACIONES PREVIAS
// ============================================
// Validar que el directorio dist existe antes de configurar el servidor
const distPath = path.join(__dirname, 'dist');
const indexPath = path.join(distPath, 'index.html');

if (!existsSync(distPath)) {
  console.error(`❌ ERROR CRÍTICO: Directorio dist no encontrado en: ${distPath}`);
  console.error('   Asegúrate de que el build se completó correctamente.');
  process.exit(1);
}

if (!existsSync(indexPath)) {
  console.error(`❌ ERROR CRÍTICO: index.html no encontrado en: ${indexPath}`);
  console.error('   Asegúrate de que el build se completó correctamente.');
  process.exit(1);
}

console.log(`📁 Directorio de archivos estáticos: ${distPath}`);
console.log(`✅ Validaciones previas completadas`);

// ============================================
// SERVIR ARCHIVOS ESTÁTICOS
// ============================================
// Servir archivos estáticos con cache headers (DESPUÉS del proxy)
// IMPORTANTE: Esto debe servir archivos .js, .css, .html, etc. con los MIME types correctos
// Estos archivos son PARTE DE LA SPA (React), NO del backend

const staticOptions = {
  maxAge: '1d',
  etag: true,
  lastModified: true,
  setHeaders: (res, filePath) => {
    // Asegurar MIME types correctos para archivos JavaScript
    if (filePath.endsWith('.js')) {
      res.setHeader('Content-Type', 'application/javascript; charset=utf-8');
    }
    // Log cuando se sirve un archivo estático (solo en desarrollo)
    if (isDevelopment && filePath.includes('/assets/')) {
      console.log(`📦 Sirviendo archivo estático: ${filePath}`);
    }
  },
  // Callback cuando no se encuentra el archivo
  fallthrough: true // Continuar al siguiente middleware si el archivo no existe
};

// ✅ Verificar que los archivos de assets existen antes de servir
const assetsPath = path.join(distPath, 'assets');
if (existsSync(assetsPath)) {
  const assetFiles = readdirSync(assetsPath);
  console.log(`✅ Directorio assets encontrado: ${assetsPath}`);
  console.log(`📦 Total de archivos en assets: ${assetFiles.length}`);
  // Log los primeros 10 archivos para debugging
  if (assetFiles.length > 0) {
    console.log(`📦 Primeros archivos: ${assetFiles.slice(0, 10).join(', ')}`);
  }
} else {
  console.error(`❌ Directorio assets NO encontrado: ${assetsPath}`);
  console.error(`❌ Esto causará que los módulos JavaScript no se carguen correctamente`);
}

// Middleware para loggear peticiones de archivos estáticos
app.use((req, res, next) => {
  // Solo loggear en desarrollo - en producción estos logs son ruido
  if (isDevelopment && (req.path.startsWith('/assets/') || req.path.endsWith('.js') || req.path.endsWith('.css') || req.path.endsWith('.svg'))) {
    console.log(`📦 Frontend: Petición de archivo estático recibida: ${req.method} ${req.path}`);
  }
  next();
});

app.use(express.static(distPath, staticOptions));

// Health check endpoint - IMPORTANTE para Render
// Render usa esto para verificar que el servicio está vivo
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    service: 'rapicredit-frontend',
    version: '1.0.1'
  });
});

// También responder a HEAD requests (usado por Render)
app.head('/health', (req, res) => {
  res.status(200).end();
});

// Manejar SPA routing - todas las rutas sirven index.html (el proxy ya atendió /api/*)
// IMPORTANTE: Esto debe ir DESPUÉS del proxy y express.static
// Solo maneja rutas que NO son archivos estáticos ni APIs
// IMPORTANTE: NO es una página estática - es una SPA que hace peticiones dinámicas al backend
app.get('*', (req, res) => {
  // Solo procesar si NO es una ruta de API
  // Las rutas de API ya fueron manejadas por el proxy
  if (req.path.startsWith('/api')) {
    // Esto no debería pasar si el proxy está funcionando correctamente
    console.warn(`⚠️  Ruta /api no capturada por proxy: ${req.method} ${req.path}`);
    return res.status(404).json({ error: 'API endpoint not found' });
  }
  
  // ✅ CRÍTICO: Si es una ruta de assets y no se encontró el archivo, devolver 404
  // NO servir index.html para archivos de assets que no existen
  // IMPORTANTE: No devolver JSON para archivos estáticos, solo 404 simple
  // NOTA: Es normal que algunos archivos no se encuentren después de un nuevo build
  // (el navegador puede tener cache del index.html anterior con hashes antiguos)
  if (req.path.startsWith('/assets/')) {
    // Solo loggear en desarrollo - en producción es ruido normal
    if (isDevelopment) {
      console.error(`❌ Archivo estático no encontrado: ${req.path}`);
    }
    // Determinar el tipo MIME apropiado basado en la extensión
    if (req.path.endsWith('.js')) {
      res.type('application/javascript');
    } else if (req.path.endsWith('.css')) {
      res.type('text/css');
    }
    return res.status(404).send('Not Found');
  }
  
  // ✅ También devolver 404 para otros archivos estáticos que no existen (favicon, imágenes, etc.)
  const staticFileExtensions = ['.js', '.css', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.eot'];
  const isStaticFile = staticFileExtensions.some(ext => req.path.endsWith(ext));
  if (isStaticFile) {
    // Solo loggear en desarrollo - en producción es ruido normal
    if (isDevelopment) {
      console.error(`❌ Archivo estático no encontrado: ${req.path}`);
    }
    // Establecer tipo MIME apropiado según la extensión
    if (req.path.endsWith('.js')) {
      res.type('application/javascript');
    } else if (req.path.endsWith('.css')) {
      res.type('text/css');
    } else if (req.path.endsWith('.svg')) {
      res.type('image/svg+xml');
    }
    return res.status(404).send('Not Found');
  }
  
  // Si llegamos aquí, NO es un archivo estático
  // Es una ruta de la SPA (como /clientes, /dashboard) → servir index.html
  // React Router manejará la ruta en el cliente
  // Solo loggear en desarrollo
  if (isDevelopment) {
    console.log(`📄 Frontend (SPA): Sirviendo index.html para ruta: ${req.method} ${req.path}`);
  }
  res.sendFile(indexPath, (err) => {
    if (err) {
      console.error(`❌ Error sirviendo index.html para ${req.method} ${req.path}:`, err);
      if (!res.headersSent) {
        res.status(404).send('Página no encontrada');
      }
    }
  });
});

// ============================================
// INICIALIZACIÓN DEL SERVIDOR
// ============================================
const PORT = process.env.PORT || 3000;

// Validar que PORT está configurado
if (!process.env.PORT) {
  console.warn(`⚠️  PORT no configurado, usando puerto por defecto: ${PORT}`);
} else {
  console.log(`✅ PORT configurado: ${PORT}`);
}

// Iniciar servidor con manejo de errores
try {
  const server = app.listen(PORT, '0.0.0.0', () => {
    console.log('🚀 ==========================================');
    console.log('🚀 Servidor SPA rapicredit-frontend iniciado');
    console.log('🚀 ==========================================');
    console.log(`📡 Puerto: ${PORT}`);
    console.log(`📁 Directorio: ${distPath}`);
    console.log(`🌍 Entorno: ${process.env.NODE_ENV || 'development'}`);
    console.log(`🔗 API URL: ${API_URL || 'No configurado'}`);
    console.log(`✅ Servidor escuchando en 0.0.0.0:${PORT}`);
    console.log('✅ Servidor listo para recibir requests');
  });

  // Manejar errores del servidor
  server.on('error', (err) => {
    console.error('❌ ERROR al iniciar servidor:', err);
    console.error(`   Código: ${err.code}`);
    console.error(`   Mensaje: ${err.message}`);
    if (err.code === 'EADDRINUSE') {
      console.error(`   Puerto ${PORT} ya está en uso`);
    }
    process.exit(1);
  });

  // Health check para Render
  server.on('listening', () => {
    const address = server.address();
    console.log(`✅ Servidor escuchando correctamente en puerto ${address.port}`);
  });
} catch (error) {
  console.error('❌ ERROR CRÍTICO al crear servidor:', error);
  console.error(error.stack);
  process.exit(1);
}

// Manejar errores no capturados
process.on('uncaughtException', (err) => {
  console.error('❌ ERROR no capturado:', err);
  console.error('Stack trace:', err.stack);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ PROMESA RECHAZADA NO MANEJADA:', reason);
  if (reason instanceof Error) {
    console.error('Stack trace:', reason.stack);
  }
  process.exit(1);
});
