import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# URL de conexión a Supabase (PostgreSQL)
# Se intenta obtener desde variables de entorno o usa una por defecto para pruebas locales
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres.tsawzmfvjgsikjtvsmfs:dLcCG8PKIh60muMF@aws-1-us-west-2.pooler.supabase.com:6543/postgres")

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