import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Carga las variables del archivo .env (solo para desarrollo local; en Vercel
# las variables se configuran en Settings -> Environment Variables).
load_dotenv()

# URL de conexión a Supabase (PostgreSQL). Se lee SIEMPRE de la variable de
# entorno DATABASE_URL: localmente desde .env (ver .env.example) y en la nube
# desde el panel del proyecto. Nunca se debe hardcodear la URL con credenciales.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "Falta la variable de entorno DATABASE_URL. "
        "Copia .env.example a .env y define la URL de conexión, "
        "o configúrala en Vercel (Settings -> Environment Variables)."
    )

# Corrección de protocolo para compatibilidad con SQLAlchemy si viene con postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Crear el motor de conexión
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Fábrica de sesiones para interactuar con la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base declarativa
class Base(DeclarativeBase):
    pass

# Dependencia para obtener la sesión en los endpoints de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
