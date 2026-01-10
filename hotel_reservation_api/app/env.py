import os
from dotenv import load_dotenv


# Clase de datos para definir las variables de entorno
class EnvSettings:
    """
    Clase para definir las variables de entorno requeridas.
    """

    SECRET_KEY: str
    DEBUG: bool
    ALLOWED_HOSTS: list[str]
    DB_NAME: str
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_PORT: str
    MONGO_DB_NAME: str
    MONGO_HOST: str
    MONGO_PORT: str
    MONGO_USER: str
    MONGO_PASSWORD: str
    JWT_ACCESS_MINUTES: float
    JWT_REFRESH_DAYS: float

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# Obtiene las variables de entorno desde un archivo .env
load_dotenv()
# Valida que las variables requeridas estén presentes
required_vars: list[str] = [
    "SECRET_KEY",
    "DEBUG",
    "ALLOWED_HOSTS",
    "DB_NAME",
    "DB_USER",
    "DB_PASS",
    "DB_HOST",
    "DB_PORT",
    "MONGO_DB_NAME",
    "MONGO_HOST",
    "MONGO_PORT",
    "MONGO_USER",
    "MONGO_PASSWORD",
    "JWT_ACCESS_MINUTES",
    "JWT_REFRESH_DAYS",
    "REFRESH_TOKEN_COOKIE_NAME",
    "PROD_FLAG",
]

for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"La variable de entorno {var} es requerida.")

# Crea un diccionario con las variables de entorno
env_settings = {
    var: os.getenv(var) for var in required_vars
}

# Convierte las variables al tipo adecuado
env_settings["DEBUG"] = env_settings["DEBUG"] == "True"
env_settings["PROD_FLAG"] = env_settings["PROD_FLAG"] == "True"


