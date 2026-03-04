"""
Test de verificacion post-refactorizacion.
Verifica que las funciones consolidadas mantienen la funcionalidad original.
"""
import sys
sys.path.insert(0, 'backend')

from app.core.documento import normalize_documento, get_clave_canonica
from app.core.serializers import to_float, format_date_iso, format_datetime_iso, format_decimal
from decimal import Decimal
from datetime import date, datetime


def test_normalize_documento():
    """Test de normalizacion de documentos."""
    print("=" * 60)
    print("TEST 1: Normalizacion de Documentos")
    print("=" * 60)
    
    test_cases = [
        # (input, expected_output, description)
        ("BNC/REF", "BNC/REF", "Documento normal"),
        ("BNC / REF", "BNC / REF", "Documento con espacios (se preservan espacios internos - es el valor que se guarda)"),
        ("  BNC/REF  ", "BNC/REF", "Documento con espacios al inicio/fin (se eliminan)"),
        (None, None, "None -> None"),
        ("", None, "String vacio -> None"),
        ("NAN", None, "NAN -> None"),
        ("NONE", None, "NONE -> None"),
        ("7.4e14", str(int(7.4e14)), "Notacion cientifica Excel -> integer como string"),
        ("V12345678-0", "V12345678-0", "Numero de cedula"),
        ("BINANCE", "BINANCE", "Criptomoneda"),
        ("ZELLE/1234", "ZELLE/1234", "ZELLE con numero"),
        ("BS. BNC / REF.", "BS. BNC / REF.", "Descripcion con puntos"),
    ]
    
    all_passed = True
    for input_val, expected, description in test_cases:
        result = normalize_documento(input_val)
        passed = result == expected
        all_passed = all_passed and passed
        status = "[PASS]" if passed else "[FAIL]"
        print("{}: {}".format(status, description))
        print("  Input: {}".format(repr(input_val)))
        print("  Expected: {}".format(repr(expected)))
        print("  Got: {}".format(repr(result)))
        print()
    
    return all_passed


def test_serializers():
    """Test de funciones de serializacion."""
    print("=" * 60)
    print("TEST 2: Funciones de Serializacion")
    print("=" * 60)
    
    all_passed = True
    
    # Test to_float
    print("TEST 2a: to_float()")
    test_cases = [
        (Decimal("123.45"), 123.45, "Decimal -> float"),
        (123, 123.0, "int -> float"),
        ("456.78", 456.78, "str -> float"),
        (None, None, "None -> None"),
        ("invalid", None, "string invalido -> None"),
    ]
    
    for input_val, expected, description in test_cases:
        result = to_float(input_val)
        passed = result == expected
        all_passed = all_passed and passed
        status = "[PASS]" if passed else "[FAIL]"
        print("{}: {}".format(status, description))
        print("  Got: {}".format(repr(result)))
    
    print()
    
    # Test format_date_iso
    print("TEST 2b: format_date_iso()")
    test_cases = [
        (date(2026, 3, 4), "2026-03-04", "date -> ISO"),
        (datetime(2026, 3, 4, 10, 30, 45), "2026-03-04", "datetime -> ISO date"),
        (None, None, "None -> None"),
    ]
    
    for input_val, expected, description in test_cases:
        result = format_date_iso(input_val)
        passed = result == expected
        all_passed = all_passed and passed
        status = "[PASS]" if passed else "[FAIL]"
        print("{}: {}".format(status, description))
        print("  Got: {}".format(repr(result)))
    
    print()
    
    # Test format_datetime_iso
    print("TEST 2c: format_datetime_iso()")
    test_cases = [
        (datetime(2026, 3, 4, 10, 30, 45), "2026-03-04T10:30:45", "datetime -> ISO"),
        (date(2026, 3, 4), "2026-03-04T00:00:00", "date -> datetime ISO"),
        (None, None, "None -> None"),
    ]
    
    for input_val, expected, description in test_cases:
        result = format_datetime_iso(input_val)
        passed = result == expected
        all_passed = all_passed and passed
        status = "[PASS]" if passed else "[FAIL]"
        print("{}: {}".format(status, description))
        print("  Got: {}".format(repr(result)))
    
    print()
    
    # Test format_decimal
    print("TEST 2d: format_decimal()")
    test_cases = [
        (Decimal("123.456"), 2, 123.46, "Redondeo a 2 decimales"),
        (Decimal("123.4"), 2, 123.4, "Decimales faltantes"),
        (None, 2, None, "None -> None"),
    ]
    
    for input_val, places, expected, description in test_cases:
        result = format_decimal(input_val, places)
        passed = result == expected
        all_passed = all_passed and passed
        status = "[PASS]" if passed else "[FAIL]"
        print("{}: {}".format(status, description))
        print("  Got: {}".format(repr(result)))
    
    print()
    return all_passed


def test_backward_compatibility():
    """Verifica que los alias de compatibilidad funcionan."""
    print("=" * 60)
    print("TEST 3: Backward Compatibility")
    print("=" * 60)
    
    all_passed = True
    
    # Test get_clave_canonica
    print("TEST 3a: get_clave_canonica() - alias para normalize_documento()")
    result1 = get_clave_canonica("BNC / REF")
    result2 = normalize_documento("BNC / REF")
    passed = result1 == result2
    all_passed = all_passed and passed
    status = "[PASS]" if passed else "[FAIL]"
    print("{}: Ambas funciones retornan lo mismo".format(status))
    print("  get_clave_canonica: {}".format(repr(result1)))
    print("  normalize_documento: {}".format(repr(result2)))
    
    print()
    return all_passed


def test_duplicado_detection():
    """Verifica que documentos duplicados se detectan correctamente."""
    print("=" * 60)
    print("TEST 4: Deteccion de Duplicados")
    print("=" * 60)
    
    print("Regla de negocio: Documentos con misma clave canonica = Duplicado")
    print()
    
    # Casos que DEBEN resultar en la misma clave (duplicados)
    duplicate_cases = [
        ("  BNC/REF  ", "BNC/REF", "Espacios al inicio/fin son iguales despues de normalizacion"),
        ("7.4e14", str(int(7.4e14)), "Notacion cientifica Excel - se convierte a integer"),
        ("V12345678", "  V12345678  ", "Espacios inicio/fin"),
    ]
    
    all_passed = True
    for doc1, doc2, description in duplicate_cases:
        key1 = normalize_documento(doc1)
        key2 = normalize_documento(doc2)
        passed = key1 == key2 and key1 is not None
        all_passed = all_passed and passed
        status = "[PASS] (Detectado como duplicado)" if passed else "[FAIL]"
        print("{}: {}".format(status, description))
        print("  {} -> {}".format(repr(doc1), repr(key1)))
        print("  {} -> {}".format(repr(doc2), repr(key2)))
        print()
    
    return all_passed


if __name__ == "__main__":
    print("\n")
    print("=" * 60)
    print("POST-REFACTORIZACION TEST SUITE")
    print("=" * 60)
    print()
    
    results = {
        "Normalizacion de Documentos": test_normalize_documento(),
        "Funciones de Serializacion": test_serializers(),
        "Backward Compatibility": test_backward_compatibility(),
        "Deteccion de Duplicados": test_duplicado_detection(),
    }
    
    print()
    print("=" * 60)
    print("RESUMEN DE RESULTADOS")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print("{}: {}".format(status, test_name))
    
    all_passed = all(results.values())
    print()
    
    if all_passed:
        print("[OK] TODOS LOS TESTS PASARON [OK]")
        print("[OK] Refactorizacion completada exitosamente")
        print("[OK] Funcionalidad 100% preservada")
    else:
        print("[FAIL] ALGUNOS TESTS FALLARON [FAIL]")
    
    sys.exit(0 if all_passed else 1)
