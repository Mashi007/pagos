from pathlib import Path
lines = Path(__file__).resolve().parents[1].joinpath("frontend/src/services/api.ts").read_text(encoding="utf-8").splitlines()
s = lines[575]
Path(__file__).resolve().parents[1].joinpath("tools/_line576.txt").write_text(s.encode("unicode_escape").decode("ascii"), encoding="ascii")
