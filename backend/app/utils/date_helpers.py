from datetime import date, timedelta

# backend/app/utils/date_helpers.py
# Utilidades para manejo de fechas

import calendar
from typing import List, Optional
from dateutil.relativedelta import relativedelta


def add_months(start_date: date, months: int) -> date:
    # Suma meses a una fecha
    # Args:
    #     start_date: Fecha inicial
    #     months: Número de meses a sumar
    # Returns:
    #     date: Nueva fecha
    return start_date + relativedelta(months=months)


def add_weeks(start_date: date, weeks: int) -> date:
    # Suma semanas a una fecha
    # Args:
    #     start_date: Fecha inicial
    #     weeks: Número de semanas a sumar
    # Returns:
    #     date: Nueva fecha
    return start_date + timedelta(weeks=weeks)


def calculate_payment_dates(
    start_date: date, num_payments: int, frequency: str
) -> List[date]:
    # Args:
    #     start_date: Fecha del primer pago
    #     frequency: Frecuencia (SEMANAL, QUINCENAL, MENSUAL, BIMENSUAL)
    # Returns:
    #     List[date]: Lista de fechas de vencimiento
    payment_dates = []
    current_date = start_date

    for i in range(num_payments):
        payment_dates.append(current_date)

        if frequency == "SEMANAL":
            current_date = add_weeks(current_date, 1)
        elif frequency == "QUINCENAL":
            current_date = add_weeks(current_date, 2)
        elif frequency == "MENSUAL":
            current_date = add_months(current_date, 1)
        elif frequency == "BIMENSUAL":
            current_date = add_months(current_date, 2)
        elif frequency == "TRIMESTRAL":
            current_date = add_months(current_date, 3)
        else:
            # Por defecto, mensual
            current_date = add_months(current_date, 1)

    return payment_dates


def days_between(date1: date, date2: date) -> int:
    # Args:
    #     date1: Primera fecha
    #     date2: Segunda fecha
    # Returns:
    #     int: Número de días (puede ser negativo si date2 < date1)
    return (date2 - date1).days


def is_overdue(due_date: date, reference_date: Optional[date] = None) -> bool:
    # Verifica si una fecha de vencimiento está vencida
    # Args:
    #     due_date: Fecha de vencimiento
    #     reference_date: Fecha de referencia (por defecto, hoy)
    # Returns:
    #     bool: True si está vencida
    if reference_date is None:
        reference_date = date.today()
    return reference_date > due_date


def days_overdue(due_date: date, reference_date: Optional[date] = None) -> int:
    # Args:
    #     due_date: Fecha de vencimiento
    #     reference_date: Fecha de referencia (por defecto, hoy)
    # Returns:
    #     int: Días de mora (0 si no está vencida)
    if reference_date is None:
        reference_date = date.today()

    days = days_between(due_date, reference_date)
    return max(0, days)


def get_last_day_of_month(year: int, month: int) -> date:
    # Obtiene el último día del mes
    # Args:
    #     year: Año
    #     month: Mes (1-12)
    # Returns:
    #     date: Último día del mes
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def get_first_day_of_month(year: int, month: int) -> date:
    # Obtiene el primer día del mes
    # Args:
    #     year: Año
    #     month: Mes (1-12)
    # Returns:
    #     date: Primer día del mes
    return date(year, month, 1)


def get_month_range(reference_date: Optional[date] = None) -> tuple[date, date]:
    # Obtiene el rango de fechas del mes
    # Args:
    #     reference_date: Fecha de referencia (por defecto, hoy)
    # Returns:
    #     tuple[date, date]: (primer_día, último_día)
    if reference_date is None:
        reference_date = date.today()

    first_day = get_first_day_of_month(reference_date.year, reference_date.month)
    last_day = get_last_day_of_month(reference_date.year, reference_date.month)

    return first_day, last_day


def get_quarter_range(reference_date: Optional[date] = None) -> tuple[date, date]:
    # Obtiene el rango de fechas del trimestre
    # Args:
    #     reference_date: Fecha de referencia (por defecto, hoy)
    # Returns:
    #     tuple[date, date]: (primer_día_trimestre, último_día_trimestre)
    if reference_date is None:
        reference_date = date.today()

    quarter = (reference_date.month - 1) // 3 + 1
    first_month = (quarter - 1) * 3 + 1
    last_month = first_month + 2

    first_day = get_first_day_of_month(reference_date.year, first_month)
    last_day = get_last_day_of_month(reference_date.year, last_month)

    return first_day, last_day


def get_year_range(year: Optional[int] = None) -> tuple[date, date]:
    # Obtiene el rango de fechas del año
    # Args:
    #     year: Año (por defecto, año actual)
    # Returns:
    #     tuple[date, date]: (primer_día_año, último_día_año)
    if year is None:
        year = date.today().year

    first_day = date(year, 1, 1)
    last_day = date(year, 12, 31)

    return first_day, last_day


def is_business_day(check_date: date, holidays: List[date] = None) -> bool:
    # Args:
    #     check_date: Fecha a verificar
    #     holidays: Lista de fechas feriadas
    # Returns:
    #     bool: True si es día hábil
    # Verificar si es fin de semana (sábado=5, domingo=6)
    if check_date.weekday() >= 5:
        return False

    # Verificar si es feriado
    if holidays and check_date in holidays:
        return False

    return True


def next_business_day(start_date: date, holidays: List[date] = None) -> date:
    # Obtiene el siguiente día hábil
    # Args:
    #     start_date: Fecha inicial
    #     holidays: Lista de fechas feriadas
    # Returns:
    #     date: Siguiente día hábil
    next_day = start_date + timedelta(days=1)
    while not is_business_day(next_day, holidays):
        next_day += timedelta(days=1)
    return next_day


def calculate_interest_days(
    start_date: date, end_date: date, day_count_convention: str = "ACT/365"
) -> int:
    # Calcula días para cálculo de intereses según convención
    # Args:
    #     start_date: Fecha inicial
    #     end_date: Fecha final
    #     day_count_convention: Convención (30/360, ACT/360, ACT/365)
    # Returns:
    #     int: Número de días según convención
    if day_count_convention == "30/360":
        # Convención 30/360 (cada mes tiene 30 días)
        d1 = min(start_date.day, 30)
        d2 = min(end_date.day, 30)
        days = (
            (end_date.year - start_date.year) * 360
            + (end_date.month - start_date.month) * 30
            + (d2 - d1)
        )
        return days
    elif day_count_convention == "ACT/360":
        # Días reales / 360
        return (end_date - start_date).days
    elif day_count_convention == "ACT/365":
        # Días reales / 365
        return (end_date - start_date).days
    else:
        # Por defecto, días reales
        return (end_date - start_date).days


def format_date_es(date_obj: date) -> str:
    # Formatea fecha en español
    # Args:
    #     date_obj: Fecha a formatear
    # Returns:
    #     str: Fecha formateada (ej: "15 de enero de 2024")
    months_es = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }

    return f"{date_obj.day} de {months_es[date_obj.month]} de {date_obj.year}"


def get_age_in_days(birth_date: date, reference_date: date = None) -> int:
    # Calcula la edad en días
    # Args:
    #     birth_date: Fecha de nacimiento
    #     reference_date: Fecha de referencia (por defecto, hoy)
    # Returns:
    #     int: Edad en días
    if reference_date is None:
        reference_date = date.today()

    return (reference_date - birth_date).days


def get_notification_dates(
    due_date: date, days_before: List[int]
) -> List[tuple[date, str]]:
    # Calcula fechas para envío de notificaciones
    # Args:
    #     due_date: Fecha de vencimiento
    #     days_before: Lista de días antes del vencimiento para notificar
    # Returns:
    #     List[tuple[date, str]]: Lista de (fecha_notificación, tipo)
    notification_dates = []

    for days in sorted(days_before, reverse=True):
        notification_date = due_date - timedelta(days=days)

        if days > 1:
            notification_type = f"RECORDATORIO_{days}D"
        elif days == 1:
            notification_type = "RECORDATORIO_1D"
        else:
            notification_type = "VENCIMIENTO_HOY"

        notification_dates.append((notification_date, notification_type))

    return notification_dates


def calculate_days_in_period(start_date: date, end_date: date, frequency: str) -> int:
    # Calcula el numero esperado de dias en un periodo segun frecuencia
    if frequency == "SEMANAL":
        return 7
    elif frequency == "QUINCENAL":
        return 15
    elif frequency == "MENSUAL":
        return 30
    elif frequency == "BIMENSUAL":
        return 60
    elif frequency == "TRIMESTRAL":
        return 90
    else:
        return (end_date - start_date).days
