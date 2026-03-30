import os
from dotenv import load_dotenv

load_dotenv()

# ── User configuration ────────────────────────────────────────────
# Edit these four values to personalize the app for your household.
# The frontend fetches these names automatically — no other files to change.
USER_A = "User A"              # Display name for user A
USER_B = "User B"              # Display name for user B

USER_A_LOGIN = "usera"         # Login username for user A
USER_B_LOGIN = "userb"         # Login username for user B
# ──────────────────────────────────────────────────────────────────

# Passwords and secret key are loaded from backend/.env (see .env.example)
USER_A_PASSWORD = os.getenv("USER_A_PASSWORD", "")
USER_B_PASSWORD = os.getenv("USER_B_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. "
        "Add a long random string to backend/.env (see .env.example)."
    )
