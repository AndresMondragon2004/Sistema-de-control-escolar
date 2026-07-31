import sys
from pathlib import Path

# Agregar la raíz del proyecto al sys.path para resolver las importaciones
file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

from main import app

# Vercel Serverless Function handler
handler = app


