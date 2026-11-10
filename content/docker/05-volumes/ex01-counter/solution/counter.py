from pathlib import Path

log = Path("/data/visits.txt")
log.parent.mkdir(parents=True, exist_ok=True)
with log.open("a") as f:
    f.write("visit\n")
print(f"visit number {len(log.read_text().splitlines())}")
