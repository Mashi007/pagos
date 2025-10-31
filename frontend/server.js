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
if (API_URL) {
  console.log(`➡️  Proxy de /api hacia: ${API_URL}`);
  app.use(
    '/api',
    createProxyMiddleware({
      target: API_URL,
      changeOrigin: true,
      xfwd: true,
      logLevel: 'debug',
      onError: (err, req, res) => {
        console.error('❌ Error en proxy:', err.message);
        res.status(502).json({
          error: 'Proxy error',
          message: err.message,
          target: API_URL
        });
      },
      onProxyReq: (proxyReq, req, res) => {
        console.log(`➡️  Proxying ${req.method} ${req.path} -> ${API_URL}${req.path}`);
      },
      onProxyRes: (proxyRes, req, res) => {
        console.log(`✅ Proxy response: ${proxyRes.statusCode} para ${req.path}`);
      }
    })
  );
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
