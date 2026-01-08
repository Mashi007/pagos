"""Ejemplo de cómo se calculan las cuotas para un préstamo"""
from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta

def calcular_cuotas_ejemplo():
    """Ejemplo de cálculo de cuotas usando el método francés"""
    
    print("=" * 70)
    print("EJEMPLO: CALCULO DE CUOTAS POR PRESTAMO")
    print("=" * 70)
    
    # Datos del préstamo
    total_financiamiento = Decimal("10000.00")
    numero_cuotas = 12
    modalidad = "MENSUAL"
    tasa_interes_anual = Decimal("12.00")  # 12% anual
    fecha_base = date(2025, 1, 15)
    
    # Calcular cuota fija
    cuota_periodo = total_financiamiento / Decimal(numero_cuotas)
    
    # Calcular tasa mensual
    tasa_mensual = tasa_interes_anual / Decimal(100) / Decimal(12)
    
    print(f"\nDATOS DEL PRESTAMO:")
    print(f"  Total financiamiento: ${total_financiamiento:,.2f}")
    print(f"  Número de cuotas: {numero_cuotas}")
    print(f"  Modalidad: {modalidad}")
    print(f"  Tasa de interés anual: {tasa_interes_anual}%")
    print(f"  Tasa mensual: {tasa_mensual * 100:.2f}%")
    print(f"  Cuota fija: ${cuota_periodo:,.2f}")
    print(f"  Fecha base: {fecha_base}")
    
    print(f"\n{'Cuota':<6} {'Fecha Venc':<12} {'Saldo Inicial':<15} {'Interés':<12} {'Capital':<12} {'Saldo Final':<15}")
    print("-" * 80)
    
    saldo_capital = total_financiamiento
    total_interes = Decimal("0.00")
    
    for numero_cuota in range(1, numero_cuotas + 1):
        # Calcular fecha de vencimiento
        if modalidad == "MENSUAL":
            fecha_vencimiento = fecha_base + relativedelta(months=numero_cuota)
        else:
            # Para QUINCENAL o SEMANAL usaría timedelta
            fecha_vencimiento = fecha_base  # Simplificado para ejemplo
        
        # Calcular interés
        monto_interes = saldo_capital * tasa_mensual
        
        # Calcular capital
        monto_capital = cuota_periodo - monto_interes
        
        # Actualizar saldo
        saldo_inicial = saldo_capital
        saldo_capital = saldo_capital - monto_capital
        saldo_final = saldo_capital
        
        total_interes += monto_interes
        
        print(f"{numero_cuota:<6} {str(fecha_vencimiento):<12} ${saldo_inicial:>13,.2f} ${monto_interes:>10,.2f} ${monto_capital:>10,.2f} ${saldo_final:>13,.2f}")
    
    print("-" * 80)
    print(f"\nRESUMEN:")
    print(f"  Total financiamiento: ${total_financiamiento:,.2f}")
    print(f"  Total intereses: ${total_interes:,.2f}")
    print(f"  Total a pagar: ${total_financiamiento + total_interes:,.2f}")
    print(f"  Cuota fija: ${cuota_periodo:,.2f}")
    print(f"  Total cuotas: {numero_cuotas}")
    
    print("\n" + "=" * 70)
    print("OBSERVACIONES:")
    print("  - El monto de la cuota es FIJO para todas las cuotas")
    print("  - El interés DISMINUYE en cada cuota (porque el saldo disminuye)")
    print("  - El capital AUMENTA en cada cuota (porque interés disminuye)")
    print("  - El saldo de capital DISMINUYE progresivamente")
    print("=" * 70)

if __name__ == "__main__":
    calcular_cuotas_ejemplo()
