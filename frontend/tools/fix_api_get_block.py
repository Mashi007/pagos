from pathlib import Path

p = Path(__file__).resolve().parent.parent / 'src' / 'services' / 'api.ts'
raw = p.read_text(encoding='utf-8', errors='replace')
ends_nl = raw.endswith('\n')
lines = raw.splitlines()
# 0-based: line 860 -> index 859
lines[859] = '        `Request failed with status ${response.status}`'
lines[867] = '      error.code = `ERR_HTTP_${response.status}`'
out = '\n'.join(lines)
if ends_nl:
    out += '\n'
p.write_text(out, encoding='utf-8')
print('OK', repr(lines[859]))
print('OK', repr(lines[867]))
