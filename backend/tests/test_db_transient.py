from app.core.db_transient import is_transient_operational_error


def test_is_transient_operational_error_ssl_closed():
    assert is_transient_operational_error(
        Exception("SSL connection has been closed unexpectedly")
    )


def test_is_transient_operational_error_other():
    assert not is_transient_operational_error(Exception("duplicate key value"))
