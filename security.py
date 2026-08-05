"""Utilidades de seguridad: hashing y verificación de contraseñas con bcrypt."""
import bcrypt


def hash_password(password: str) -> str:
    """Genera un hash bcrypt seguro para la contraseña."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, stored: str) -> bool:
    """Verifica una contraseña en texto plano contra el hash almacenado."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def es_hash_bcrypt(stored: str) -> bool:
    """Indica si el valor almacenado es un hash bcrypt.

    Los registros creados antes de migrar a bcrypt guardaban la contraseña en
    texto plano; esta función permite detectarlos para migrarlos al iniciar
    sesión (se re-hashea automáticamente tras un login exitoso).
    """
    return stored.startswith("$2")
