path = "app/api/v1/endpoints/pagos.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    'cedula_normalizada = payload.cedula_cliente.strip().upper() if payload.cedula_cliente else ""',
    'cedula_normalizada = (payload.cedula_cliente or "").strip().upper()',
    2,
)

old = """    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Servicio no disponible. Reintente en unos segundos.",
        )"""
new = """    except HTTPException:
        raise
    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Servicio no disponible. Reintente en unos segundos.",
        )
    except Exception as e:
        logger.exception("Batch: error inesperado: %s", e)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}") from e"""
if old in c:
    c = c.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("OK: safe cedula + exception handler")
else:
    print("Block not found - file may already be patched")
