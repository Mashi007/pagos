# Fix SyntaxError: unexpected character after line continuation character
# Replace (pr.referencia_interna or \") with (pr.referencia_interna or "")
path = "app/api/v1/endpoints/pagos.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()
# The file has backslash-quote which in Python is wrong
c = c.replace(' or \\"\\")[:100]', ' or "")[:100]')
with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("Fixed.")
