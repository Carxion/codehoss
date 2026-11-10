import time

print("starting up...", flush=True)
time.sleep(1)
raise SystemExit("lost the connection to something important; exiting")
