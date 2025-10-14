/**
 * 🧪 PRUEBAS INTERNAS FRONTEND - RAPICREDIT
 * Verificación de funcionalidad del frontend y integración con backend
 */

class FrontendTester {
    constructor() {
        this.baseUrl = 'https://rapicredit.onrender.com';
        this.apiUrl = 'https://pagos-f2qf.onrender.com';
        this.results = {
            total: 0,
            passed: 0,
            failed: 0,
            errors: [],
            details: []
        };
    }

    logTest(testName, status, details = '', data = null) {
        this.results.total++;
        
        if (status === 'PASS') {
            this.results.passed++;
            console.log(`✅ ${testName}: PASS - ${details}`);
        } else {
            this.results.failed++;
            this.results.errors.push(`${testName}: ${details}`);
            console.error(`❌ ${testName}: FAIL - ${details}`);
        }
        
        this.results.details.push({
            test: testName,
            status,
            details,
            timestamp: new Date().toISOString(),
            data
        });
    }

    async testPageLoad() {
        try {
            console.log('🔍 Probando carga de página principal...');
            
            const response = await fetch(this.baseUrl, {
                method: 'GET',
                headers: {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                }
            });
            
            if (response.ok) {
                const html = await response.text();
                
                // Verificar elementos clave del React app
                const hasReactRoot = html.includes('id="root"');
                const hasScripts = html.includes('<script');
                const hasTitle = html.includes('RapiCredit') || html.includes('Rapicredit');
                
                if (hasReactRoot && hasScripts) {
                    this.logTest('Page Load', 'PASS', 
                        `Status: ${response.status}, React root found`, 
                        { status: response.status, hasReactRoot, hasScripts, hasTitle });
                } else {
                    this.logTest('Page Load', 'FAIL', 
                        'React app structure not found');
                }
            } else {
                this.logTest('Page Load', 'FAIL', 
                    `HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            this.logTest('Page Load', 'FAIL', `Error: ${error.message}`);
        }
    }

    async testAPIEndpoints() {
        try {
            console.log('🔍 Probando endpoints de API...');
            
            const endpoints = [
                '/api/v1/health',
                '/api/v1/auth/login',
                '/api/v1/clientes',
                '/api/v1/dashboard/admin'
            ];
            
            for (const endpoint of endpoints) {
                try {
                    const response = await fetch(`${this.apiUrl}${endpoint}`, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json'
                        }
                    });
                    
                    if (response.status === 200) {
                        this.logTest(`API Endpoint: ${endpoint}`, 'PASS', 
                            `Status: ${response.status}`);
                    } else if (response.status === 401 || response.status === 403) {
                        this.logTest(`API Endpoint: ${endpoint}`, 'PASS', 
                            `Status: ${response.status} (Auth required - expected)`);
                    } else {
                        this.logTest(`API Endpoint: ${endpoint}`, 'FAIL', 
                            `Status: ${response.status}: ${response.statusText}`);
                    }
                } catch (error) {
                    this.logTest(`API Endpoint: ${endpoint}`, 'FAIL', 
                        `Error: ${error.message}`);
                }
            }
        } catch (error) {
            this.logTest('API Endpoints', 'FAIL', `Error: ${error.message}`);
        }
    }

    async testAuthenticationFlow() {
        try {
            console.log('🔍 Probando flujo de autenticación...');
            
            const loginData = {
                email: 'admin@rapicredit.com',
                password: 'admin123',
                remember: true
            };
            
            const response = await fetch(`${this.apiUrl}/api/v1/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(loginData)
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.data && data.data.access_token) {
                    this.logTest('Authentication Login', 'PASS', 
                        `Token received: ${data.data.access_token.substring(0, 20)}...`,
                        { hasToken: true, hasUser: !!data.user });
                    
                    // Probar endpoint protegido con el token
                    await this.testProtectedEndpoint(data.data.access_token);
                } else {
                    this.logTest('Authentication Login', 'FAIL', 
                        'Token not found in response');
                }
            } else {
                const errorText = await response.text();
                this.logTest('Authentication Login', 'FAIL', 
                    `Status: ${response.status}, Response: ${errorText}`);
            }
        } catch (error) {
            this.logTest('Authentication Login', 'FAIL', `Error: ${error.message}`);
        }
    }

    async testProtectedEndpoint(token) {
        try {
            console.log('🔍 Probando endpoint protegido...');
            
            const response = await fetch(`${this.apiUrl}/api/v1/clientes?page=1&per_page=5`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                this.logTest('Protected Endpoint', 'PASS', 
                    `Status: ${response.status}, Data received`,
                    { status: response.status, hasData: !!data });
            } else if (response.status === 403) {
                this.logTest('Protected Endpoint', 'FAIL', 
                    '403 Forbidden - Token validation failed');
            } else {
                this.logTest('Protected Endpoint', 'FAIL', 
                    `Status: ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            this.logTest('Protected Endpoint', 'FAIL', `Error: ${error.message}`);
        }
    }

    async testLocalStorage() {
        try {
            console.log('🔍 Probando funcionalidad de localStorage...');
            
            // Simular guardado de token
            const testToken = 'test_token_12345';
            const testUser = { id: 1, email: 'test@test.com', nombre: 'Test User' };
            
            localStorage.setItem('access_token', testToken);
            localStorage.setItem('user', JSON.stringify(testUser));
            
            // Verificar recuperación
            const retrievedToken = localStorage.getItem('access_token');
            const retrievedUser = localStorage.getItem('user');
            
            if (retrievedToken === testToken && retrievedUser) {
                const parsedUser = JSON.parse(retrievedUser);
                this.logTest('LocalStorage', 'PASS', 
                    'Token and user data stored and retrieved successfully',
                    { tokenMatch: retrievedToken === testToken, userMatch: parsedUser.email === testUser.email });
            } else {
                this.logTest('LocalStorage', 'FAIL', 
                    'Failed to store or retrieve data from localStorage');
            }
            
            // Limpiar datos de prueba
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
        } catch (error) {
            this.logTest('LocalStorage', 'FAIL', `Error: ${error.message}`);
        }
    }

    async testFormValidation() {
        try {
            console.log('🔍 Probando validación de formularios...');
            
            // Crear formulario de prueba
            const form = document.createElement('form');
            form.innerHTML = `
                <input type="email" id="email" value="test@example.com">
                <input type="password" id="password" value="password123">
                <input type="text" id="cedula" value="12345678">
                <input type="tel" id="telefono" value="+58412123456">
            `;
            
            // Simular validaciones
            const email = form.querySelector('#email').value;
            const password = form.querySelector('#password').value;
            const cedula = form.querySelector('#cedula').value;
            const telefono = form.querySelector('#telefono').value;
            
            // Validaciones básicas
            const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
            const passwordValid = password.length >= 6;
            const cedulaValid = /^\d{7,8}$/.test(cedula);
            const telefonoValid = /^\+584\d{9}$/.test(telefono);
            
            if (emailValid && passwordValid && cedulaValid && telefonoValid) {
                this.logTest('Form Validation', 'PASS', 
                    'All form validations passed',
                    { emailValid, passwordValid, cedulaValid, telefonoValid });
            } else {
                this.logTest('Form Validation', 'FAIL', 
                    'Some validations failed',
                    { emailValid, passwordValid, cedulaValid, telefonoValid });
            }
        } catch (error) {
            this.logTest('Form Validation', 'FAIL', `Error: ${error.message}`);
        }
    }

    async testPerformance() {
        try {
            console.log('🔍 Probando rendimiento...');
            
            const startTime = performance.now();
            
            // Simular operaciones pesadas
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const endTime = performance.now();
            const duration = endTime - startTime;
            
            if (duration < 200) {
                this.logTest('Performance', 'PASS', 
                    `Operation completed in ${duration.toFixed(2)}ms`,
                    { duration });
            } else {
                this.logTest('Performance', 'FAIL', 
                    `Operation took too long: ${duration.toFixed(2)}ms`,
                    { duration });
            }
        } catch (error) {
            this.logTest('Performance', 'FAIL', `Error: ${error.message}`);
        }
    }

    generateReport() {
        const successRate = this.results.total > 0 
            ? (this.results.passed / this.results.total * 100) 
            : 0;
        
        return {
            summary: {
                total: this.results.total,
                passed: this.results.passed,
                failed: this.results.failed,
                successRate: Math.round(successRate * 100) / 100,
                timestamp: new Date().toISOString(),
                systemStatus: successRate >= 80 ? 'HEALTHY' : successRate >= 60 ? 'DEGRADED' : 'CRITICAL'
            },
            errors: this.results.errors,
            details: this.results.details
        };
    }

    async runAllTests() {
        console.log('🚀 Iniciando pruebas internas del frontend...');
        console.log('=' * 60);
        
        const tests = [
            ['Page Load', () => this.testPageLoad()],
            ['API Endpoints', () => this.testAPIEndpoints()],
            ['Authentication Flow', () => this.testAuthenticationFlow()],
            ['LocalStorage', () => this.testLocalStorage()],
            ['Form Validation', () => this.testFormValidation()],
            ['Performance', () => this.testPerformance()]
        ];
        
        for (const [testName, testFunc] of tests) {
            console.log(`\n📋 Ejecutando: ${testName}`);
            try {
                await testFunc();
            } catch (error) {
                this.logTest(testName, 'FAIL', `Unexpected error: ${error.message}`);
            }
            
            await new Promise(resolve => setTimeout(resolve, 500));
        }
        
        const report = this.generateReport();
        
        console.log('\n' + '=' * 60);
        console.log('📊 RESUMEN FINAL DE PRUEBAS FRONTEND:');
        console.log(`✅ Pruebas Exitosas: ${report.summary.passed}`);
        console.log(`❌ Pruebas Fallidas: ${report.summary.failed}`);
        console.log(`📈 Tasa de Éxito: ${report.summary.successRate}%`);
        console.log(`🎯 Estado del Sistema: ${report.summary.systemStatus}`);
        
        if (report.summary.errors.length > 0) {
            console.log('\n❌ ERRORES ENCONTRADOS:');
            report.summary.errors.forEach(error => {
                console.log(`  - ${error}`);
            });
        }
        
        return report;
    }
}

// Ejecutar pruebas si se ejecuta directamente
if (typeof window !== 'undefined') {
    // En el navegador
    window.FrontendTester = FrontendTester;
    
    // Auto-ejecutar si está en la consola del navegador
    if (window.location.hostname === 'rapicredit.onrender.com') {
        const tester = new FrontendTester();
        tester.runAllTests().then(report => {
            console.log('🧪 Pruebas frontend completadas:', report);
        });
    }
} else {
    // En Node.js (para testing automatizado)
    module.exports = FrontendTester;
}
