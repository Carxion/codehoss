import getpass
import os

print(f"running as {getpass.getuser()} (uid {os.getuid()})")
