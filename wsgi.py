import sys

path = '/home/KoAung/files_vault_bot'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
