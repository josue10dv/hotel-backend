import os
from dotenv import load_dotenv
# Obtiene las variables de entorno desde un archivo .env
load_dotenv()
# Valida que las variables requeridas estén presentes
required_vars = [
    'SECRET_KEY',
    'DEBUG',
    'ALLOWED_HOSTS',
    'DB_NAME',
    'DB_USER',
    'DB_PASS',
    'DB_HOST',
    'DB_PORT',
    'JWT_ACCESS_MINUTES',
    'JWT_REFRESH_DAYS'
]

for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"La variable de entorno {var} es requerida.")
    
# Crea un diccionario con las variables de entorno
env_settings = {var: os.getenv(var) for var in required_vars}