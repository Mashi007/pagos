"""
ARQUITECTURA DE SERVICIOS DE PRÉSTAMOS
=====================================

Descripción General
-------------------
Los servicios de préstamos se han modularizado siguiendo el patrón de pagos.py
para mejorar la mantenibilidad, testabilidad y separación de responsabilidades.

Estructura de Directorios
------------------------
backend/app/services/prestamos/
├── __init__.py                      # Exporta servicios y excepciones
├── prestamos_excepciones.py         # Excepciones específicas
├── prestamos_validacion.py          # Reglas de validación
├── prestamos_calculo.py             # Cálculos financieros
├── amortizacion_service.py          # Gestión de amortizaciones
├── prestamos_service.py             # Servicio principal
└── adaptador_compatibility.py       # Compatibilidad con código legado


Componentes Principales
-----------------------

1. PRESTAMOS_EXCEPCIONES.PY
   - PrestamoNotFoundError: Préstamo no existe
   - PrestamoValidationError: Error de validación
   - PrestamoStateError: Transición de estado inválida
   - ClienteConErrorError: Cliente con errores registrados
   - AmortizacionCalculoError: Error en cálculos de amortización
   - Más excepciones específicas para diferentes casos

2. PRESTAMOS_VALIDACION.PY
   Validaciones implementadas:
   - Existencia de cliente y verificación de errores
   - Validación de montos y cálculos numéricos
   - Validación de número de cuotas (1-360)
   - Validación de tasa de interés
   - Validación de modalidades de pago (MENSUAL, QUINCENAL, SEMANAL, DIARIA)
   - Validación de estados y transiciones permitidas
   - Validación de fechas
   - Validación de cédula única por cliente
   - Validación de códigos ML de riesgo
   - Validación de probabilidades ML

3. PRESTAMOS_CALCULO.PY
   Cálculos financieros implementados:
   - Conversión de divisas (pesos ↔ dólares)
   - Interés simple y compuesto
   - Cálculo de cuota fija (sistema francés)
   - Interés por período
   - Amortización de capital
   - Tasa efectiva anual (TEA)
   - Cálculo de VAT/IVA

4. AMORTIZACION_SERVICE.PY (CRÍTICO)
   Funciones principales:
   - generar_tabla_amortizacion(): Crea calendario completo
   - obtener_tabla_amortizacion(): Recupera tabla existente
   - registrar_pago_cuota(): Registra abonos a cuotas
   - calcular_estado_amortizacion(): Estado general del préstamo
   - obtener_cuotas_vencidas(): Cuotas atrasadas
   - obtener_cuotas_proximas(): Próximas a vencer
   - calcular_interes_penalizacion_atraso(): Penalización por mora
   - regenerar_amortizacion_desde(): Recalcula desde cuota específica

5. PRESTAMOS_SERVICE.PY (ORQUESTADOR)
   Operaciones principales:
   - crear_prestamo(): Crea préstamo con validaciones completas
   - obtener_prestamo(): Recupera un préstamo
   - actualizar_prestamo(): Actualiza campos
   - cambiar_estado_prestamo(): Cambio de estado con transiciones validadas
   - obtener_prestamos_cliente(): Todos los préstamos de un cliente
   - obtener_prestamos_vencidos(): Préstamos con cuotas atrasadas
   - generar_tabla_amortizacion(): Crea/regenera tabla
   - registrar_pago_cuota(): Registra pagos de cuotas
   - obtener_estadistica_prestamos(): Estadísticas generales

6. ADAPTADOR_COMPATIBILITY.PY (COMPATIBILIDAD)
   Funciones de compatibilidad:
   - con_manejo_errores_prestamos: Decorador para endpoints
   - obtener_servicio_prestamos: Factory function
   - AdaptadorPrestamosLegacy: Interfaz compatible con código legacy
   - Funciones auxiliares para Depends()


Estados del Préstamo (State Machine)
------------------------------------

DRAFT
  ↓ ENVIADO, CANCELADO
ENVIADO
  ↓ APROBADO, RECHAZADO, DRAFT
APROBADO
  ↓ ACTIVO, RECHAZADO
RECHAZADO
  ↓ (final)
ACTIVO
  ↓ PAGADO, SUSPENDIDO, CANCELADO
PAGADO
  ↓ (final)
CANCELADO
  ↓ (final)
SUSPENDIDO
  ↓ ACTIVO, CANCELADO


Modalidades de Pago
-------------------
- MENSUAL: 30 días entre cuotas
- QUINCENAL: 15 días entre cuotas
- SEMANAL: 7 días entre cuotas
- DIARIA: 1 día entre cuotas


Cálculo de Amortización (Sistema Francés)
------------------------------------------

La fórmula utilizada es:

    C = P * [i(1+i)^n] / [(1+i)^n - 1]

Donde:
- C = Cuota fija
- P = Principal (monto del préstamo)
- i = Tasa de interés por período
- n = Número de períodos

Cada cuota se descompone en:
- Cuota = Interés + Amortización
- Donde el interés disminuye y la amortización aumenta en cada período


Integración con Modelos
-----------------------

Modelos utilizados:
- Prestamo: Información principal del préstamo
- Cuota: Detalle de cada cuota del calendario
- CuotaPago: Historial de pagos realizados
- Cliente: Información del cliente
- TasaCambioDiaria: Tasas de cambio para conversiones
- ClienteConError: Registro de errores de clientes


Validaciones de Negocio
-----------------------

1. Creación de Préstamo:
   - Cliente debe existir y no tener errores
   - Monto debe ser positivo
   - Número de cuotas entre 1 y 360
   - Tasa entre 0 y 100%
   - Modalidad debe ser válida
   - Cédula coherente con cliente

2. Cambio de Estado:
   - Solo transiciones permitidas por state machine
   - DRAFT → ENVIADO (solo cambios)
   - ENVIADO → APROBADO (genera tabla amortización)
   - APROBADO → ACTIVO (autorizado)
   - ACTIVO → PAGADO (cuando está completamente pagado)

3. Registro de Pagos:
   - Cuota debe existir
   - Monto pagado debe ser positivo
   - Se actualiza estado (PENDIENTE, PARCIAL, PAGADO)

4. Regeneración de Amortización:
   - Se mantienen pagos realizados
   - Se recalculan cuotas pendientes
   - Permite ajustar tasas


Uso en Endpoints
----------------

Ejemplo 1: Crear Préstamo
```python
from app.services.prestamos import obtener_servicio_prestamos

@router.post("/prestamos")
def crear_prestamo(datos: dict, db: Session = Depends(get_db)):
    service = obtener_servicio_prestamos(db)
    prestamo = service.crear_prestamo(datos)
    return prestamo
```

Ejemplo 2: Con Decorador de Manejo de Errores
```python
from app.services.prestamos import con_manejo_errores_prestamos

@router.get("/prestamos/{prestamo_id}")
@con_manejo_errores_prestamos
def obtener_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
    service = obtener_servicio_prestamos(db)
    prestamo = service.obtener_prestamo(prestamo_id)
    return prestamo
```

Ejemplo 3: Usar Adaptador Legacy
```python
from app.services.prestamos import AdaptadorPrestamosLegacy

@router.get("/prestamos/{prestamo_id}/resumen")
def obtener_resumen(prestamo_id: int, db: Session = Depends(get_db)):
    adaptador = AdaptadorPrestamosLegacy(db)
    resumen = adaptador.obtener_resumen_prestamo(prestamo_id)
    if resumen is None:
        raise HTTPException(status_code=404)
    return resumen
```


Compatibilidad
---------------

IMPORTANTE: NO HAY RUPTURA DE API

Todos los endpoints existentes continuarán funcionando:
- Misma estructura de respuestas
- Mismos campos en JSON
- Misma validación de datos
- Mismos códigos de error HTTP

Los servicios se utilizan internamente bajo el capó para:
- Mejorar la lógica de negocio
- Facilitar testing
- Permitir reutilización de código
- Separar responsabilidades


Testing
-------

La suite de pruebas incluye:
- Pruebas unitarias de validación
- Pruebas de cálculos financieros
- Pruebas de amortización
- Pruebas del servicio principal
- Pruebas del adaptador de compatibilidad
- Pruebas de casos edge

Ejecutar tests:
```bash
pytest tests/unit/services/prestamos/test_prestamos_service.py -v
```


Roadmap Futuro
---------------

Mejoras planeadas:
1. Refactorizar endpoints para usar servicios directamente
2. Agregar soporte para diferentes tipos de amortización (alemán, italiano)
3. Implementar ajustes por inflación
4. Agregar seguimiento de comisiones
5. Implementar alertas por cuotas vencidas
6. Agregar reportes de amortización
7. Mejorar logging y auditoría
"""
