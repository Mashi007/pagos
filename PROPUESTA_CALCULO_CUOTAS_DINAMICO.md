# Propuesta: Cálculo Dinámico de Cuotas Basado en Análisis de Riesgo

## Problema Actual

Actualmente el número de cuotas está fijo según la modalidad:
- MENSUAL: 36 cuotas
- QUINCENAL: 72 cuotas
- SEMANAL: 144 cuotas

Pero según **TABLA 9: CONDICIONES SEGÚN NIVEL DE RIESGO**, el plazo máximo debe ajustarse al nivel de riesgo:

| Nivel de Riesgo | Plazo Máximo (meses) |
|----------------|----------------------|
| BAJO | 36 meses |
| MODERADO | 30 meses |
| ALTO | 24 meses |
| CRÍTICO | 18 meses |

## Solución Propuesta

### Opción 1: Flujo en Dos Fases (RECOMENDADA)

**FASE 1: Creación del Préstamo (DRAFT)**
- Usuario ingresa monto y modalidad
- Se asigna un número de cuotas temporal: 
  - MENSUAL: 36 (valor por defecto)
  - QUINCENAL: 72
  - SEMANAL: 144
- Estado: `DRAFT`

**FASE 2: Después de Evaluación de Riesgo**
- Al evaluar el riesgo, se determina el `plazo_maximo`
- Se recalcula el número de cuotas según:
  ```python
  if modalidad == "MENSUAL":
      cuotas_finales = plazo_maximo
  elif modalidad == "QUINCENAL":
      cuotas_finales = plazo_maximo * 2
  elif modalidad == "SEMANAL":
      cuotas_finales = plazo_maximo * 4
  ```
- Se actualiza el préstamo con las cuotas correctas
- Estado: `EN_REVISION` → `APROBADO`/`RECHAZADO`

### Ejemplo de Cálculo Dinámico

```python
def calcular_cuotas_dinamico(
    total: Decimal, 
    modalidad: str, 
    plazo_maximo_meses: int = None  # Si no se especifica, usa valores por defecto
) -> tuple[int, Decimal]:
    """
    Calcula cuotas considerando el plazo máximo del análisis de riesgo.
    
    Args:
        total: Monto total del préstamo
        modalidad: MENSUAL, QUINCENAL, SEMANAL
        plazo_maximo_meses: Plazo máximo en meses (desde evaluación de riesgo)
    
    Returns:
        (numero_cuotas, cuota_periodo)
    """
    # Si hay plazo máximo definido (después de evaluación), usarlo
    if plazo_maximo_meses:
        if modalidad == "MENSUAL":
            cuotas = plazo_maximo_meses
        elif modalidad == "QUINCENAL":
            cuotas = plazo_maximo_meses * 2
        elif modalidad == "SEMANAL":
            cuotas = plazo_maximo_meses * 4
    else:
        # Valores temporales por defecto (antes de evaluación)
        if modalidad == "MENSUAL":
            cuotas = 36
        elif modalidad == "QUINCENAL":
            cuotas = 72
        elif modalidad == "SEMANAL":
            cuotas = 144
    
    cuota_periodo = total / Decimal(cuotas)
    return cuotas, cuota_periodo
```

### Ejemplo Práctico

**Escenario 1: BAJO RIESGO (Plazo máximo: 36 meses)**
- Modalidad: MENSUAL
- Total: $1,000,000
- Cuotas: 36
- Cuota: $1,000,000 ÷ 36 = $27,777.78

**Escenario 2: ALTO RIESGO (Plazo máximo: 24 meses)**
- Modalidad: MENSUAL
- Total: $1,000,000
- Cuotas: 24 (reducido por el riesgo)
- Cuota: $1,000,000 ÷ 24 = $41,666.67

**Escenario 3: QUINCENAL con ALTO RIESGO**
- Modalidad: QUINCENAL
- Total: $1,000,000
- Plazo máximo: 24 meses
- Cuotas: 24 × 2 = 48
- Cuota: $1,000,000 ÷ 48 = $20,833.33

## Implementación

### 1. Actualizar Frontend (CrearPrestamoForm.tsx)

```typescript
// Estado para plazo máximo desde evaluación
const [plazoMaximo, setPlazoMaximo] = useState<number | null>(null)

const calcularCuotas = (total: number, modalidad: string, plazoMax?: number) => {
  let cuotas = 36 // Default MENSUAL
  
  if (plazoMax) {
    // Si ya hay evaluación de riesgo, usar plazo máximo
    if (modalidad === 'QUINCENAL') cuotas = plazoMax * 2
    else if (modalidad === 'SEMANAL') cuotas = plazoMax * 4
    else cuotas = plazoMax
  } else {
    // Valores temporales por defecto
    if (modalidad === 'QUINCENAL') cuotas = 72
    else if (modalidad === 'SEMANAL') cuotas = 144
  }
  
  const cuota = total / cuotas
  setNumeroCuotas(cuotas)
  setCuotaPeriodo(cuota)
}
```

### 2. Actualizar Backend (prestamos.py)

```python
def actualizar_cuotas_segun_riesgo(
    prestamo_id: int,
    plazo_maximo_meses: int,
    db: Session
):
    """
    Actualiza el número de cuotas y cuota_periodo después de evaluación de riesgo.
    """
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    # Recalcular cuotas según plazo máximo
    numero_cuotas, cuota_periodo = calcular_cuotas_dinamico(
        prestamo.total_financiamiento,
        prestamo.modalidad_pago,
        plazo_maximo_meses
    )
    
    # Actualizar préstamo
    prestamo.numero_cuotas = numero_cuotas
    prestamo.cuota_periodo = cuota_periodo
    
    db.commit()
    db.refresh(prestamo)
    
    return prestamo
```

### 3. Flujo de Aprobación

```python
@router.post("/{prestamo_id}/aprobar-con-condiciones")
def aprobar_prestamo_con_condiciones(
    prestamo_id: int,
    datos_aprobacion: dict,  # {plazo_maximo, tasa_interes, etc}
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aprueba un préstamo y aplica condiciones según riesgo"""
    
    prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
    
    # 1. Actualizar cuotas según plazo máximo
    actualizar_cuotas_segun_riesgo(prestamo_id, datos_aprobacion['plazo_maximo'], db)
    
    # 2. Aplicar tasa de interés
    prestamo.tasa_interes = datos_aprobacion['tasa_interes']
    prestamo.fecha_base_calculo = datos_aprobacion.get('fecha_base_calculo')
    
    # 3. Cambiar estado
    prestamo.estado = "APROBADO"
    prestamo.usuario_aprobador = current_user.email
    prestamo.fecha_aprobacion = datetime.utcnow()
    
    db.commit()
    
    # 4. Generar tabla de amortización
    if prestamo.fecha_base_calculo:
        generar_amortizacion(prestamo, prestamo.fecha_base_calculo, db)
    
    return prestamo
```

## Ventajas de esta Solución

✅ **Flexible**: Se adapta al nivel de riesgo del cliente
✅ **Justo**: Clientes de bajo riesgo obtienen plazos más largos
✅ **Protegido**: Clientes de alto riesgo tienen plazos más cortos
✅ **Mantenible**: Fácil de ajustar las condiciones
✅ **Trazable**: Se guarda en auditoría cómo se calcularon las cuotas

## Próximos Pasos

1. Implementar `calcular_cuotas_dinamico()` en backend
2. Actualizar `EvaluacionRiesgoForm` para mostrar el plazo máximo sugerido
3. Modificar flujo de aprobación para recalcular cuotas
4. Actualizar frontend para mostrar cuotas "temporales" vs "finales"

