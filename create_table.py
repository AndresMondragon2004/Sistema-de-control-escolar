import os

from sqlalchemy import text

from database import engine, Base, SessionLocal
import models  # Carga los 4 modelos para que SQLAlchemy los reconozca
from security import hash_password


def test_connection():
    try:
        print("Intentando conectar a la base de datos...")
        # create_all se encarga de verificar la conexión y crear las tablas que no existan
        Base.metadata.create_all(bind=engine)
        print("Tablas (usuarios, materias, inscripciones, calificaciones) creadas/verificadas.")
        aplicar_restricciones()
        seed_admin()
        print("¡Listo!")
    except Exception as e:
        print(f"Error al conectar con la base de datos: {e}")


def aplicar_restricciones():
    """Limpia inscripciones duplicadas y agrega la restricción UNIQUE si no existe."""
    with engine.begin() as conn:
        # 1) Eliminar las calificaciones de las inscripciones duplicadas (se conserva la de menor id)
        conn.execute(text("""
            DELETE FROM calificaciones
            WHERE id_inscripcion IN (
                SELECT i.id_inscripcion
                FROM inscripciones i
                JOIN inscripciones i2
                  ON i2.id_usuario = i.id_usuario
                 AND i2.id_materia = i.id_materia
                 AND i2.periodo = i.periodo
                 AND i2.id_inscripcion < i.id_inscripcion
            )
        """))
        # 2) Borrar las inscripciones duplicadas (más nuevas)
        conn.execute(text("""
            DELETE FROM inscripciones i
            USING inscripciones i2
            WHERE i2.id_usuario = i.id_usuario
              AND i2.id_materia = i.id_materia
              AND i2.periodo = i.periodo
              AND i2.id_inscripcion < i.id_inscripcion
        """))
        # 3) Agregar la restricción UNIQUE si aún no existe
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_inscripcion_usuario_materia_periodo'
                ) THEN
                    ALTER TABLE inscripciones
                    ADD CONSTRAINT uq_inscripcion_usuario_materia_periodo
                    UNIQUE (id_usuario, id_materia, periodo);
                END IF;
            END $$;
        """))
        print("Restricción UNIQUE de inscripciones verificada.")


def seed_admin():
    """Crea un usuario administrador si no existe ninguno."""
    admin_email = os.getenv("ADMIN_EMAIL", "admin@control.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    db = SessionLocal()
    try:
        existe = db.query(models.Usuario).filter(models.Usuario.rol == "admin").first()
        if existe:
            print(f"Administrador ya existente: {existe.correo}")
            return
        admin = models.Usuario(
            nombre="Administrador",
            correo=admin_email,
            password=hash_password(admin_password),
            rol="admin",
        )
        db.add(admin)
        db.commit()
        print(f"Administrador creado -> correo: {admin_email} | contraseña: {admin_password}")
        print("IMPORTANTE: cámbiala después de iniciar sesión (edita el usuario).")
    finally:
        db.close()


if __name__ == "__main__":
    test_connection()
