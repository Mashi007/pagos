from app.utils.cedula_busqueda import cedula_busqueda_canonica, extraer_caracteres_cedula_busqueda


def test_extraer_quita_separadores():
    assert extraer_caracteres_cedula_busqueda("V-30.081.920") == "V30081920"
    assert extraer_caracteres_cedula_busqueda("125.25.69") == "1252569"


def test_canonica_ve_con_separadores():
    assert cedula_busqueda_canonica("V-30.081.920") == "V30081920"
    assert cedula_busqueda_canonica("v 30 081 920") == "V30081920"


def test_canonica_solo_digitos_prefija_v():
    assert cedula_busqueda_canonica("125.25.69") == "V1252569"


def test_canonica_nombre_no_devuelve_canonica():
    assert cedula_busqueda_canonica("María Pérez") is None
    assert cedula_busqueda_canonica("") is None
