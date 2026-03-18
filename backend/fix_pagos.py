# Fix pagos.py: add except OperationalError after batch return
path = "app/api/v1/endpoints/pagos.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

insert_after = None
for i, line in enumerate(lines):
    if "ok_count" in line and "fail_count" in line and "return " in line and "results" in line:
        insert_after = i
        break

print("insert_after", insert_after)
if insert_after is not None:
    block = """    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Servicio no disponible. Reintente en unos segundos.",
        )


"""
    new_lines = lines[: insert_after + 1] + [block] + lines[insert_after + 1 :]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("Done")

