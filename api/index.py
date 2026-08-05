import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al sys.path para resolver los módulos (main, database, models, etc.)
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from main import app

# Definición a nivel superior requerida por el builder @vercel/python
handler = app
