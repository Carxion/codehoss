import time
from pathlib import Path

beat = Path("/tmp/heartbeat")
while True:
    beat.write_text(str(time.time()))
    time.sleep(1)
