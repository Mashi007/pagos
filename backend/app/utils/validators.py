# backend/app/utils/validators.py
"""

import re
from decimal import Decimal
from typing import Optional

# Constantes de validación
MIN_DNI_LENGTH = 7
MAX_DNI_LENGTH = 11
MAX_CUOTAS = 360
MAX_TASA_INTERES = 100
MAX_PERCENTAGE_INGRESO = 40
DEFAULT_TOLERANCE_PAYMENT = 0.01
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MIN_CUENTA_LENGTH = 8
MAX_CUENTA_LENGTH = 20


def validate_dni(dni: str) -> bool:
    """
    Valida formato de DNI/Cédula
    Args:
        dni: Número de documento
    Returns:
        bool: True si es válido
    """
    if not dni:
        return False

    dni_clean = dni.replace(" ", "").replace("-", "")

    if not dni_clean.isdigit():
        return False

    if len(dni_clean) < MIN_DNI_LENGTH or len(dni_clean) > MAX_DNI_LENGTH:
        return False

    return True


def validate_phone(phone: str) -> bool:
    """
    Valida formato de teléfono venezolano
    Ejemplo: +584121234567
    Args:
        phone: Número de teléfono
    Returns:
        bool: True si es válido
    """
    if not phone:
        return False

    phone_clean = re.sub(r"[\s\-\(\)]", "", phone)

    pattern = r"^\+58[1-9]\d{9}$"
    return bool(re.match(pattern, phone_clean))


def validate_email(email: str) -> bool:
    """
    Valida formato de email
    Args:
        email: Dirección de email
    Returns:
        bool: True si es válido
    """
    if not email:
        return False

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_ruc(ruc: str) -> bool:
    """
    Valida formato de RUC paraguayo
    Args:
        ruc: Número de RUC
    Returns:
        bool: True si es válido
    """
    if not ruc:
        return False

    ruc_clean = ruc.replace(" ", "")

    pattern = r"^\d{8}-\d$"
    if not re.match(pattern, ruc_clean):
        return False

    # NOTA: Implementar algoritmo de validación de dígito verificador
    return True


    """
    Args:
        amount: Monto a validar
    Returns:
        bool: True si es válido
    """
    if amount is None:
        return False

    return amount > Decimal("0")


def validate_percentage(percentage: Decimal) -> bool:
    """
    Valida que un porcentaje esté entre 0 y 100
    Args:
        percentage: Porcentaje a validar
    Returns:
        bool: True si es válido
    """
    if percentage is None:
        return False

    return Decimal("0") <= percentage <= Decimal("100")


def validate_date_range(start_date: date, end_date: date) -> bool:
    """
    Valida que una fecha de inicio sea menor o igual a la fecha de fin
    Args:
        start_date: Fecha de inicio
        end_date: Fecha de fin
    Returns:
        bool: True si es válido
    """
    if not start_date or not end_date:
        return False

    return start_date <= end_date


def validate_future_date(check_date: date) -> bool:
    """
    Valida que una fecha sea futura
    Args:
        check_date: Fecha a validar
    Returns:
        bool: True si es válido
    """
    if not check_date:
        return False

    return check_date > date.today()


def validate_past_date(check_date: date) -> bool:
    """
    Valida que una fecha sea pasada
    Args:
        check_date: Fecha a validar
    Returns:
        bool: True si es válido
    """
    if not check_date:
        return False

    return check_date < date.today()


def validate_date_not_future(check_date: date) -> bool:
    """
    Valida que una fecha no sea futura (hoy o antes)
    Args:
        check_date: Fecha a validar
    Returns:
        bool: True si es válido
    """
    if not check_date:
        return False

    return check_date <= date.today()


def validate_cuotas(numero_cuotas: int) -> bool:
    """
    Valida número de cuotas
    Args:
        numero_cuotas: Número de cuotas
    Returns:
        bool: True si es válido (entre 1 y MAX_CUOTAS)
    """
    if numero_cuotas is None:
        return False

    return 1 <= numero_cuotas <= MAX_CUOTAS


def validate_tasa_interes(tasa: Decimal) -> bool:
    """
    Valida tasa de interés
    Args:
        tasa: Tasa de interés anual
    Returns:
        bool: True si es válido (entre 0 y MAX_TASA_INTERES)
    """
    if tasa is None:
        return False

    return Decimal("0") <= tasa <= Decimal(str(MAX_TASA_INTERES))


def sanitize_string(text: Optional[str]) -> Optional[str]:
    """
    Sanitiza un string removiendo caracteres especiales
    Args:
        text: Texto a sanitizar
    Returns:
        Optional[str]: Texto sanitizado
    """
    if not text:
        return None

    text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
    text = " ".join(text.split())
    return text.strip()


def sanitize_html(text: Optional[str]) -> Optional[str]:
    """
    Sanitiza HTML para prevenir XSS
    Args:
        text: Texto que puede contener HTML
    Returns:
    """
    if not text:
        return None

    import html

    # Escapar caracteres HTML
    text = html.escape(text)

    text = re.sub(r"[<>]", "", text)

    text = re.sub(
        r"<script.*?>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL
    )
    text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)
    text = re.sub(r"on\w+\s*=", "", text, flags=re.IGNORECASE)

    return text.strip()


def format_dni(dni: str) -> str:
    """
    Ejemplo: 12345678 -> 1.234.567-8
    Args:
        dni: DNI sin formato
    Returns:
        str: DNI formateado
    """
    if not dni:
        return dni

    dni_clean = dni.replace(".", "").replace("-", "").strip()

    if len(dni_clean) >= 7:
        formatted = ""
        for i, char in enumerate(dni_clean[:-1]):
            if i > 0 and (len(dni_clean) - i - 1) % 3 == 0:
                formatted += "."
            formatted += char

        formatted += "-" + dni_clean[-1]
        return formatted

    return dni_clean


def format_phone(phone: str) -> str:
    """
    Formatea teléfono
    Ejemplo: 0981234567 -> (0981) 234-567
    Args:
        phone: Teléfono sin formato
    Returns:
        str: Teléfono formateado
    """
    if not phone:
        return phone

    phone_clean = re.sub(r"[\s\-\(\)]", "", phone)

    if phone_clean.startswith("+595"):
        # +595 981 234567
        phone_clean = phone_clean[4:]
        return f"+595 {phone_clean[:3]} {phone_clean[3:]}"
    elif phone_clean.startswith("0"):
        # 0981 234567
        return f"({phone_clean[:4]}) {phone_clean[4:7]}-{phone_clean[7:]}"
    else:
        # 981 234567
        return f"{phone_clean[:3]} {phone_clean[3:6]}-{phone_clean[6:]}"


def validate_cuenta_bancaria(cuenta: str) -> bool:
    """
    Valida formato de cuenta bancaria
    Args:
        cuenta: Número de cuenta
    Returns:
        bool: True si es válido
    """
    if not cuenta:
        return False

    cuenta_clean = cuenta.replace(" ", "").replace("-", "")

    if not cuenta_clean.isdigit():
        return False

    if (
        len(cuenta_clean) < MIN_CUENTA_LENGTH
        or len(cuenta_clean) > MAX_CUENTA_LENGTH
    ):
        return False

    return True


def validate_codigo_prestamo(codigo: str) -> bool:
    """
    Valida formato de código de préstamo
    Formato esperado: PREST-YYYYMMDD-XXXX
    Args:
        codigo: Código de préstamo
    Returns:
        bool: True si es válido
    """
    if not codigo:
        return False

    pattern = r"^PREST-\d{8}-\d{4}$"
    return bool(re.match(pattern, codigo))


def validate_monto_vs_ingreso(
    monto_cuota: Decimal,
    ingreso_mensual: Decimal,
    max_percentage: Decimal = Decimal(str(MAX_PERCENTAGE_INGRESO)),
) -> bool:
    """
    Valida que el monto de cuota no supere un porcentaje del ingreso
    Args:
        monto_cuota: Monto de la cuota
        ingreso_mensual: Ingreso mensual del cliente
        max_percentage: Porcentaje máximo permitido
    Returns:
        bool: True si es válido
    """
    if not monto_cuota or not ingreso_mensual:
        return False

    if ingreso_mensual <= 0:
        return False

    percentage = (monto_cuota / ingreso_mensual) * Decimal("100")
    return percentage <= max_percentage


def validate_payment_amount(
    payment_amount: Decimal,
    expected_amount: Decimal,
    tolerance: Decimal = Decimal(str(DEFAULT_TOLERANCE_PAYMENT)),
) -> bool:
    """
    Valida que un monto de pago sea válido con respecto al esperado
    Args:
        payment_amount: Monto pagado
        expected_amount: Monto esperado
        tolerance: Tolerancia permitida
    Returns:
        bool: True si es válido
    """
    if not payment_amount or not expected_amount:
        return False

    difference = abs(payment_amount - expected_amount)
    return difference <= tolerance or payment_amount >= expected_amount


def _validate_password_length(password: str) -> tuple[bool, str]:
    """Validar longitud de contraseña"""
    if not password:
        return False, "La contraseña es requerida"

    if len(password) < MIN_PASSWORD_LENGTH:
        return (
            False,
            "caracteres",
        )

    if len(password) > MAX_PASSWORD_LENGTH:
        return (
            False,
            "La contraseña no puede tener más de "
            f"{MAX_PASSWORD_LENGTH} caracteres",
        )

    return True, ""


def _validate_password_patterns(password: str) -> tuple[bool, str]:
    if not re.search(r"[a-z]", password):
        return (
            False,
        )

    if not re.search(r"[A-Z]", password):
        return (
            False,
        )

    if not re.search(r"\d", password):

    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\/?]', password):
        return (
            False,
        )

    if " " in password:

    return True, ""


def _validate_password_weak_patterns(password: str) -> tuple[bool, str]:
    """Validar patrones débiles comunes"""
    weak_patterns = [
        r"123456",  # Secuencia numérica
        r"abcde",  # Secuencia alfabética
        r"password",  # Palabra común
        r"qwerty",  # Teclado
    ]

    password_lower = password.lower()
    for pattern in weak_patterns:
        if re.search(pattern, password_lower):
            return False, "La contraseña contiene patrones débiles comunes"

    return True, ""


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Valida la fortaleza de una contraseña
    Args:
        password: Contraseña a validar
    Returns:
        tuple[bool, str]: (es_valida, mensaje_error)
    """
    # Validar longitud
    is_valid, message = _validate_password_length(password)
    if not is_valid:
        return is_valid, message

    is_valid, message = _validate_password_patterns(password)
    if not is_valid:
        return is_valid, message

    # Validar patrones débiles
    is_valid, message = _validate_password_weak_patterns(password)
    if not is_valid:
        return is_valid, message

    return True, "Contraseña válida"


def normalize_text(text: str) -> str:
    """
    Normaliza texto para búsquedas
    Args:
        text: Texto a normalizar
    Returns:
        str: Texto normalizado
    """
    if not text:
        return ""

    # Convertir a minúsculas
    text = text.lower()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
        "ü": "u",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9\s]", "", text)

    text = " ".join(text.split())

    return text
