from pathlib import Path
root = Path(__file__).resolve().parents[1]
lines = root.joinpath("frontend/src/services/api.ts").read_text(encoding="utf-8").splitlines()
for n in (674, 738, 873):
    s = lines[n - 1]
    root.joinpath(f"tools/_line{n}.txt").write_text(s.encode("unicode_escape").decode("ascii"), encoding="ascii")
