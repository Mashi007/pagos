import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { createProxyMiddleware } from 'http-proxy-middleware';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const API_URL = process.env.VITE_API_BASE_URL || process.env.VITE_API_URL || 'http://localhost:8080';

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
// PROXY /api -> Backend (Render)
// ============================================
// IMPORTANTE: Proxy debe ir ANTES de servir archivos estáticos
// Capturar TODAS las peticiones a /api (GET, POST, PUT, DELETE, etc.)
if (API_URL) {
  console.log(`➡️  Proxy de /api hacia: ${API_URL}`);
  const proxyMiddleware = createProxyMiddleware({
    target: API_URL,
    changeOrigin: true,
    xfwd: true,
    logLevel: 'debug',
    // Mantener el path completo (/api/v1/... se envía completo al backend)
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
      const targetUrl = `${API_URL}${req.originalUrl || req.url}`;
      console.log(`➡️  [${req.method}] Proxying ${req.originalUrl || req.url} -> ${targetUrl}`);
    },
    onProxyRes: (proxyRes, req, res) => {
      const status = proxyRes.statusCode;
      const emoji = status >= 200 && status < 300 ? '✅' : status >= 400 ? '❌' : '⚠️';
      console.log(`${emoji} [${req.method}] Proxy response: ${status} para ${req.originalUrl || req.url}`);
    }
  });
  
  // Aplicar a todas las rutas que empiecen con /api
  app.use('/api', proxyMiddleware);
} else {
  console.warn('⚠️  API_URL no configurado. Proxy deshabilitado.');
}

// Servir archivos estáticos con cache headers (DESPUÉS del proxy)
app.use(express.static(path.join(__dirname, 'dist'), {
  maxAge: '1d',
  etag: true,
  lastModified: true
}));

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    service: 'rapicredit-frontend',
    version: '1.0.1'
  });
});

// Manejar SPA routing - todas las rutas sirven index.html (el proxy ya atendió /api/*)
app.get('*', (req, res) => {
  // Ignorar rutas de API (deberían ser capturadas por el proxy)
  if (req.path.startsWith('/api')) {
    console.warn(`⚠️  Ruta /api no capturada por proxy: ${req.path}`);
    return res.status(404).json({ error: 'API endpoint not found' });
  }
  // El proxy de /api maneja las APIs; aquí solo servimos la SPA
  console.log(`📄 Sirviendo index.html para ruta: ${req.path}`);
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => {
  console.log('🚀 ==========================================');
  console.log('🚀 Servidor SPA rapicredit-frontend iniciado');
  console.log('🚀 ==========================================');
  console.log(`📡 Puerto: ${PORT}`);
  console.log(`📁 Directorio: ${path.join(__dirname, 'dist')}`);
  console.log(`🌍 Entorno: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🔗 API URL: ${API_URL || 'No configurado'}`);
  console.log('✅ Servidor listo para recibir requests');
});
