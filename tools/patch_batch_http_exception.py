from pathlib import Path

P = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
text = P.read_text(encoding="utf-8")
old = """            return {"results": results, "ok_count": ok_count, "fail_count": fail_count}

        except Exception as e:

            db.rollback()

            logger.exception("Batch: error en transaccion unica: %s", e)

            raise HTTPException(status_code=500, detail=f"Error al guardar el lote. Ningun pago fue creado. Detalle: {str(e)}")

    except HTTPException:

        raise"""
new = """            return {"results": results, "ok_count": ok_count, "fail_count": fail_count}

        except HTTPException:

            db.rollback()

            raise

        except Exception as e:

            db.rollback()

            logger.exception("Batch: error en transaccion unica: %s", e)

            raise HTTPException(status_code=500, detail=f"Error al guardar el lote. Ningun pago fue creado. Detalle: {str(e)}")

    except HTTPException:

        raise"""
if old not in text:
    raise SystemExit("batch except anchor not found")
P.write_text(text.replace(old, new, 1), encoding="utf-8")
print("ok")
