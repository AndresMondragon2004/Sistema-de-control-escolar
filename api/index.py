import sys
from pathlib import Path

# Agregar la raíz del proyecto al sys.path para resolver las importaciones
file = Path(__file__).resolve()
parent, root = file.parent, file.parents[1]
sys.path.append(str(root))

try:
    from main import app

    # Vercel Serverless Function handler
    handler = app
except Exception:  # pragma: no cover - ayuda a diagnosticar fallos en Vercel
    import traceback

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="Control Escolar - Error de arranque")

    @app.get("/{path:path}", include_in_schema=False)
    async def error_arranque(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "La función no pudo cargarse. Revisa los logs de Vercel.",
                "detalle": str(traceback.format_exc()),
            },
        )

    handler = app
