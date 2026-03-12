# Fix broken `r`n in notificaciones_tabs.py
path = r"app\api\v1\endpoints\notificaciones_tabs.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
# Replace literal backtick-r-backtick-n with newline
bad = chr(96) + "r" + chr(96) + "n"
if bad in c:
    c = c.replace(bad, "\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("OK: replaced backtick-r-backtick-n with newline")
else:
    print("Literal not found")
