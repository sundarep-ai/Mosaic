import os
from dotenv import load_dotenv

load_dotenv()

USER_A = "Praveen"
USER_B = "Nina"

USER_A_LOGIN = "sundarep"
USER_B_LOGIN = "niumont"

USER_A_PASSWORD = os.getenv("USER_A_PASSWORD", "")
USER_B_PASSWORD = os.getenv("USER_B_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")
