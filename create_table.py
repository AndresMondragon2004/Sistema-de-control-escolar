from database import engine, Base
import models  # Carga los 4 modelos para que SQLAlchemy los reconozca

def test_connection():
    try:
        print("Intentando conectar a Supabase...")
        # create_all se encarga de verificar la conexión y crear las tablas que no existan
        Base.metadata.create_all(bind=engine)
        print("¡Conexión exitosa! Las tablas (usuarios, materias, inscripciones, calificaciones) han sido creadas/verificadas en Supabase.")
    except Exception as e:
        print(f"Error al conectar con la base de datos: {e}")

if __name__ == "__main__":
    test_connection()