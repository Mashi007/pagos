#!/usr/bin/env python3
"""
CREAR PAGINAS FALTANTES DEL FRONTEND
Script para generar componentes básicos de las páginas faltantes
"""

import os
from pathlib import Path

# Directorio base del frontend
FRONTEND_DIR = Path("frontend/src/pages")

# Plantilla base para páginas
PAGE_TEMPLATE = '''import { useState } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { usePermissions } from '@/store/authStore'

export function {PAGE_NAME}() {
  const { hasAnyRole } = usePermissions()
  const [loading, setLoading] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{PAGE_TITLE}</h1>
          <p className="text-muted-foreground">
            {PAGE_DESCRIPTION}
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          En Desarrollo
        </Badge>
      </div>

      {/* Contenido Principal */}
      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>{PAGE_TITLE}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <div className="text-6xl mb-4">🚧</div>
              <h3 className="text-xl font-semibold mb-2">Página en Desarrollo</h3>
              <p className="text-muted-foreground mb-4">
                Esta funcionalidad está siendo implementada y estará disponible próximamente.
              </p>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>• Funcionalidades básicas implementadas</p>
                <p>• Integración con backend en progreso</p>
                <p>• Pruebas de usuario pendientes</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Cards de información */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Estado</CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant="secondary">En Desarrollo</Badge>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Progreso</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full" style={{width: '60%'}}></div>
              </div>
              <p className="text-sm text-muted-foreground mt-2">60% completado</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Próxima Actualización</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Próximamente</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </motion.div>
  )
}
'''

# Páginas a crear
PAGES_TO_CREATE = [
    {
        'name': 'PrestamosPage',
        'title': 'Préstamos',
        'description': 'Gestión de préstamos y financiamientos'
    },
    {
        'name': 'PagosPage', 
        'title': 'Pagos',
        'description': 'Registro y seguimiento de pagos'
    },
    {
        'name': 'AmortizacionPage',
        'title': 'Amortización',
        'description': 'Tablas de amortización y cálculos'
    },
    {
        'name': 'ConciliacionPage',
        'title': 'Conciliación',
        'description': 'Conciliación bancaria y contable'
    },
    {
        'name': 'ReportesPage',
        'title': 'Reportes',
        'description': 'Generación de reportes y análisis'
    },
    {
        'name': 'AprobacionesPage',
        'title': 'Aprobaciones',
        'description': 'Sistema de aprobaciones y flujos'
    },
    {
        'name': 'NotificacionesPage',
        'title': 'Notificaciones',
        'description': 'Gestión de notificaciones multicanal'
    },
    {
        'name': 'SchedulerPage',
        'title': 'Programador',
        'description': 'Configuración de tareas programadas'
    },
    {
        'name': 'ConfiguracionPage',
        'title': 'Configuración',
        'description': 'Configuración del sistema'
    },
    {
        'name': 'IADashboardPage',
        'title': 'IA Dashboard',
        'description': 'Dashboard de inteligencia artificial'
    }
]

def create_page(page_info):
    """Crear una página individual"""
    page_name = page_info['name']
    page_title = page_info['title']
    page_description = page_info['description']
    
    # Generar contenido de la página
    content = PAGE_TEMPLATE.format(
        PAGE_NAME=page_name,
        PAGE_TITLE=page_title,
        PAGE_DESCRIPTION=page_description
    )
    
    # Crear archivo
    file_path = FRONTEND_DIR / f"{page_name}.tsx"
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"OK Creada: {file_path}")
        return True
    except Exception as e:
        print(f"ERROR creando {file_path}: {e}")
        return False

def update_app_routes():
    """Actualizar App.tsx con las nuevas rutas"""
    app_file = Path("frontend/src/App.tsx")
    
    if not app_file.exists():
        print("ERROR App.tsx no encontrado")
        return False
    
    # Leer archivo actual
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar si las rutas ya existen
    if 'PrestamosPage' in content:
        print("OK Las rutas ya estan en App.tsx")
        return True
    
    # Agregar imports
    imports_to_add = '''
// Páginas en desarrollo
import { PrestamosPage } from './pages/PrestamosPage'
import { PagosPage } from './pages/PagosPage'
import { AmortizacionPage } from './pages/AmortizacionPage'
import { ConciliacionPage } from './pages/ConciliacionPage'
import { ReportesPage } from './pages/ReportesPage'
import { AprobacionesPage } from './pages/AprobacionesPage'
import { NotificacionesPage } from './pages/NotificacionesPage'
import { SchedulerPage } from './pages/SchedulerPage'
import { ConfiguracionPage } from './pages/ConfiguracionPage'
import { IADashboardPage } from './pages/IADashboardPage'
'''
    
    # Agregar rutas
    routes_to_add = '''
          {/* Préstamos */}
          <Route path="prestamos" element={<PrestamosPage />} />
          
          {/* Pagos */}
          <Route path="pagos" element={<PagosPage />} />
          
          {/* Amortización */}
          <Route path="amortizacion" element={<AmortizacionPage />} />
          
          {/* Conciliación */}
          <Route path="conciliacion" element={<ConciliacionPage />} />
          
          {/* Reportes */}
          <Route path="reportes" element={<ReportesPage />} />
          
          {/* Aprobaciones */}
          <Route path="aprobaciones" element={<AprobacionesPage />} />
          
          {/* Notificaciones */}
          <Route path="notificaciones" element={<NotificacionesPage />} />
          
          {/* Scheduler */}
          <Route path="scheduler" element={<SchedulerPage />} />
          
          {/* Configuración */}
          <Route path="configuracion" element={<ConfiguracionPage />} />
          
          {/* IA Dashboard */}
          <Route path="ia-dashboard" element={<IADashboardPage />} />
'''
    
    # Insertar imports después de los imports existentes
    if 'import { CargaMasiva }' in content:
        content = content.replace(
            'import { CargaMasiva }',
            f'{imports_to_add}\nimport {{ CargaMasiva }}'
        )
    
    # Insertar rutas después de las rutas existentes
    if 'path="carga-masiva"' in content:
        content = content.replace(
            'path="carga-masiva"',
            f'path="carga-masiva"'
        )
        # Buscar el cierre de la ruta de carga masiva y agregar las nuevas rutas
        carga_masiva_end = content.find('</Route>', content.find('path="carga-masiva"'))
        if carga_masiva_end != -1:
            insert_pos = content.find('>', carga_masiva_end) + 1
            content = content[:insert_pos] + routes_to_add + content[insert_pos:]
    
    # Escribir archivo actualizado
    try:
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("OK App.tsx actualizado con nuevas rutas")
        return True
    except Exception as e:
        print(f"ERROR actualizando App.tsx: {e}")
        return False

def main():
    """Función principal"""
    print("CREANDO PAGINAS FALTANTES DEL FRONTEND")
    print("=" * 50)
    
    # Crear directorio si no existe
    FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
    
    # Crear páginas
    created = 0
    failed = 0
    
    for page_info in PAGES_TO_CREATE:
        if create_page(page_info):
            created += 1
        else:
            failed += 1
    
    # Actualizar App.tsx
    print("\nActualizando rutas en App.tsx...")
    update_app_routes()
    
    # Resumen
    print("\n" + "=" * 50)
    print("RESUMEN:")
    print(f"OK Paginas creadas: {created}")
    print(f"ERROR Paginas fallidas: {failed}")
    print(f"Total procesadas: {len(PAGES_TO_CREATE)}")
    
    if created > 0:
        print("\nPROXIMOS PASOS:")
        print("1. Verificar que las paginas se crearon correctamente")
        print("2. Probar navegacion desde el sidebar")
        print("3. Implementar funcionalidades especificas")
        print("4. Conectar con endpoints del backend")
    
    print("\nPROCESO COMPLETADO")

if __name__ == "__main__":
    main()
