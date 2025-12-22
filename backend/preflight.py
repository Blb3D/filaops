from importlib import util as _util
import os

def have(modname: str) -> bool:
    return _util.find_spec(modname) is not None

mods = [
    "requests",
    "jwt", "cryptography", "email_validator", "multipart", "passlib",
    "sqlalchemy", "fastapi", "alembic", "psycopg2",
]

# Only require Google libs if explicitly enabled
enable_gdrive = os.getenv("ENABLE_GOOGLE_DRIVE", "false").strip().lower() in {"1","true","yes","on"}
if enable_gdrive:
    mods += ["googleapiclient.discovery", "google.oauth2.credentials", "google_auth_oauthlib.flow"]

missing = [m for m in mods if not have(m)]
print("Missing:", missing if missing else "None")
