import os
import secrets
import time

from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from starlette.middleware.sessions import SessionMiddleware

from database import get_db
import models
from security import hash_password, verify_password, es_hash_bcrypt

app = FastAPI(title="Control Escolar Web")
templates = Jinja2Templates(directory="templates")

# Rutas accesibles sin iniciar sesión
RUTAS_PUBLICAS = {"/login"}

# Límite de intentos de inicio de sesión para frenar ataques de fuerza bruta
MAX_INTENTOS_LOGIN = 5
BLOQUEO_SEGUNDOS = 60


@app.middleware("http")
async def seguridad_y_autenticacion(request: Request, call_next):
    """Redirige a /login si no hay sesión y agrega cabeceras de seguridad."""
    if request.url.path not in RUTAS_PUBLICAS and not request.session.get("usuario_id"):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


# Sesiones firmadas con cookies (se agrega al final para que sea la capa más
# externa y la sesión esté disponible dentro del middleware anterior).
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "clave-dev-insegura-cambiar-en-produccion"),
    same_site="lax",
    # En producción (https) conviene activar SESSION_HTTPS_ONLY=true
    https_only=os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true",
)


# ---------------------------------------------------------
# UTILIDADES: CSRF Y SESIÓN
# ---------------------------------------------------------
def asegurar_csrf(request: Request) -> str:
    """Devuelve (y crea si hace falta) el token CSRF almacenado en la sesión."""
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def csrf_protect(request: Request, csrf_token: str = Form(None)):
    """Valida que el formulario envíe el token CSRF de la sesión."""
    token_sesion = request.session.get("csrf_token")
    if not token_sesion or not csrf_token or not secrets.compare_digest(token_sesion, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token CSRF inválido o expirado. Recarga la página e inténtalo de nuevo.",
        )
    return None


def verificar_rol(request: Request, tab: str, *roles: str):
    """Control de acceso por roles: devuelve una redirección con aviso si el
    rol del usuario logueado no está entre los permitidos."""
    if request.session.get("usuario_rol") not in roles:
        return RedirectResponse(
            url=f"/?tab={tab}&error=sin_permiso",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return None


# ---------------------------------------------------------
# AUTENTICACIÓN
# ---------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    if request.session.get("usuario_id"):
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "csrf_token": asegurar_csrf(request),
            "primer_acceso": db.query(models.Usuario).count() == 0,
        },
    )


@app.post("/login")
def login(
    request: Request,
    correo: str = Form(...),
    password: str = Form(...),
    csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    # Bloqueo temporal tras demasiados intentos fallidos
    bloqueado_hasta = request.session.get("bloqueo_hasta", 0)
    if bloqueado_hasta and time.time() < bloqueado_hasta:
        return RedirectResponse(url="/login?error=bloqueado", status_code=status.HTTP_303_SEE_OTHER)

    usuario = db.query(models.Usuario).filter(models.Usuario.correo == correo).first()
    autenticado = False
    if usuario:
        if es_hash_bcrypt(usuario.password):
            autenticado = verify_password(password, usuario.password)
        else:
            # Migración: contraseñas legadas guardadas en texto plano
            autenticado = secrets.compare_digest(usuario.password, password)
            if autenticado:
                usuario.password = hash_password(password)
                db.commit()

    if not autenticado:
        intentos = request.session.get("intentos_fallidos", 0) + 1
        request.session["intentos_fallidos"] = intentos
        if intentos >= MAX_INTENTOS_LOGIN:
            request.session["bloqueo_hasta"] = time.time() + BLOQUEO_SEGUNDOS
            request.session["intentos_fallidos"] = 0
            return RedirectResponse(url="/login?error=bloqueado", status_code=status.HTTP_303_SEE_OTHER)
        return RedirectResponse(url="/login?error=credenciales", status_code=status.HTTP_303_SEE_OTHER)

    request.session["intentos_fallidos"] = 0
    request.session["bloqueo_hasta"] = 0
    request.session["usuario_id"] = usuario.id_usuario
    request.session["usuario_nombre"] = usuario.nombre
    request.session["usuario_rol"] = usuario.rol
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/logout")
def logout(request: Request, csrf: None = Depends(csrf_protect)):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------
# RUTA PRINCIPAL (DASHBOARD SSR)
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, tab: str = "usuarios", db: Session = Depends(get_db)):
    usuarios = db.query(models.Usuario).all()
    materias = db.query(models.Materia).all()
    inscripciones = db.query(models.Inscripcion).all()
    calificaciones = db.query(models.Calificacion).all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "tab_activa": tab,
            "usuarios": usuarios,
            "materias": materias,
            "inscripciones": inscripciones,
            "calificaciones": calificaciones,
            "csrf_token": asegurar_csrf(request),
            "usuario_actual": {
                "nombre": request.session.get("usuario_nombre"),
                "rol": request.session.get("usuario_rol"),
            },
        },
    )


# ---------------------------------------------------------
# CRUD: USUARIOS
# ---------------------------------------------------------
@app.post("/usuarios/crear")
def crear_usuario(
    request: Request,
    nombre: str = Form(...),
    correo: str = Form(...),
    password: str = Form(...),
    rol: str = Form(...),
    csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    respuesta = verificar_rol(request, "usuarios", "admin")
    if respuesta:
        return respuesta

    nuevo_usuario = models.Usuario(nombre=nombre, correo=correo, password=hash_password(password), rol=rol)
    try:
        db.add(nuevo_usuario)
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url="/?tab=usuarios&error=correo_existe", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/?tab=usuarios", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/usuarios/eliminar/{id_usuario}")
def eliminar_usuario(request: Request, id_usuario: int, csrf: None = Depends(csrf_protect), db: Session = Depends(get_db)):
    respuesta = verificar_rol(request, "usuarios", "admin")
    if respuesta:
        return respuesta

    usuario = db.get(models.Usuario, id_usuario)
    if usuario:
        db.delete(usuario)
        db.commit()
    return RedirectResponse(url="/?tab=usuarios", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/usuarios/editar/{id_usuario}")
def editar_usuario(
    request: Request,
    id_usuario: int,
    nombre: str = Form(...),
    correo: str = Form(...),
    rol: str = Form(...),
    password: str = Form(""),
    csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    respuesta = verificar_rol(request, "usuarios", "admin")
    if respuesta:
        return respuesta

    usuario = db.get(models.Usuario, id_usuario)
    if not usuario:
        return RedirectResponse(url="/?tab=usuarios&error=no_encontrado", status_code=status.HTTP_303_SEE_OTHER)

    usuario.nombre = nombre
    usuario.correo = correo
    usuario.rol = rol
    # La contraseña solo cambia si el campo no viene vacío
    if password.strip():
        usuario.password = hash_password(password)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url="/?tab=usuarios&error=correo_existe", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/?tab=usuarios", status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------
# CRUD: MATERIAS
# ---------------------------------------------------------
@app.post("/materias/crear")
def crear_materia(
    request: Request,
    clave: str = Form(...),
    nombre_mat: str = Form(...),
    creditos: int = Form(...),
    csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    respuesta = verificar_rol(request, "materias", "admin", "docente")
    if respuesta:
        return respuesta

    nueva_materia = models.Materia(clave=clave, nombre_mat=nombre_mat, creditos=creditos)
    try:
        db.add(nueva_materia)
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url="/?tab=materias&error=clave_existe", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/?tab=materias", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/materias/editar/{id_materia}")
def editar_materia(
    request: Request,
    id_materia: int,
    clave: str = Form(...),
    nombre_mat: str = Form(...),
    creditos: int = Form(...),
    csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    respuesta = verificar_rol(request, "materias", "admin", "docente")
    if respuesta:
        return respuesta

    materia = db.get(models.Materia, id_materia)
    if not materia:
        return RedirectResponse(url="/?tab=materias&error=no_encontrado", status_code=status.HTTP_303_SEE_OTHER)

    materia.clave = clave
    materia.nombre_mat = nombre_mat
    materia.creditos = creditos
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url="/?tab=materias&error=clave_existe", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/?tab=materias", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/materias/eliminar/{id_materia}")
def eliminar_materia(request: Request, id_materia: int, csrf: None = Depends(csrf_protect), db: Session = Depends(get_db)):
    respuesta = verificar_rol(request, "materias", "admin", "docente")
    if respuesta:
        return respuesta

    materia = db.get(models.Materia, id_materia)
    if materia:
        db.delete(materia)
        db.commit()
    return RedirectResponse(url="/?tab=materias", status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------
# CRUD: INSCRIPCIONES
# ---------------------------------------------------------
@app.post("/inscripciones/crear")
def crear_inscripcion(
    request: Request,
    id_usuario: int = Form(...),
    id_materia: int = Form(...),
    periodo: str = Form(...),
    csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    respuesta = verificar_rol(request, "inscripciones", "admin", "docente")
    if respuesta:
        return respuesta

    # Evitar inscripciones duplicadas (mismo alumno, materia y periodo)
    duplicada = db.query(models.Inscripcion).filter(
        models.Inscripcion.id_usuario == id_usuario,
        models.Inscripcion.id_materia == id_materia,
        models.Inscripcion.periodo == periodo
    ).first()
    if duplicada:
        return RedirectResponse(url="/?tab=inscripciones&error=inscripcion_duplicada", status_code=status.HTTP_303_SEE_OTHER)

    nueva_inscripcion = models.Inscripcion(id_usuario=id_usuario, id_materia=id_materia, periodo=periodo)
    db.add(nueva_inscripcion)
    db.flush()

    # Crear calificación automática inicializada en 0.00
    nueva_calif = models.Calificacion(id_inscripcion=nueva_inscripcion.id_inscripcion, parcial_1=0, parcial_2=0, parcial_3=0, promedio_final=0)
    db.add(nueva_calif)
    db.commit()
    return RedirectResponse(url="/?tab=inscripciones", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/inscripciones/editar/{id_inscripcion}")
def editar_inscripcion(
    request: Request,
    id_inscripcion: int,
    id_usuario: int = Form(...),
    id_materia: int = Form(...),
    periodo: str = Form(...),
    csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    respuesta = verificar_rol(request, "inscripciones", "admin", "docente")
    if respuesta:
        return respuesta

    inscripcion = db.get(models.Inscripcion, id_inscripcion)
    if not inscripcion:
        return RedirectResponse(url="/?tab=inscripciones&error=no_encontrado", status_code=status.HTTP_303_SEE_OTHER)

    # Evitar duplicados ignorando el registro que se está editando
    duplicada = db.query(models.Inscripcion).filter(
        models.Inscripcion.id_usuario == id_usuario,
        models.Inscripcion.id_materia == id_materia,
        models.Inscripcion.periodo == periodo,
        models.Inscripcion.id_inscripcion != id_inscripcion
    ).first()
    if duplicada:
        return RedirectResponse(url="/?tab=inscripciones&error=inscripcion_duplicada", status_code=status.HTTP_303_SEE_OTHER)

    inscripcion.id_usuario = id_usuario
    inscripcion.id_materia = id_materia
    inscripcion.periodo = periodo
    db.commit()
    return RedirectResponse(url="/?tab=inscripciones", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/inscripciones/eliminar/{id_inscripcion}")
def eliminar_inscripcion(request: Request, id_inscripcion: int, csrf: None = Depends(csrf_protect), db: Session = Depends(get_db)):
    respuesta = verificar_rol(request, "inscripciones", "admin", "docente")
    if respuesta:
        return respuesta

    inscripcion = db.get(models.Inscripcion, id_inscripcion)
    if inscripcion:
        # Las calificaciones asociadas se eliminan en cascada
        db.delete(inscripcion)
        db.commit()
    return RedirectResponse(url="/?tab=inscripciones", status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------
# CRUD: CALIFICACIONES (UPDATE)
# ---------------------------------------------------------
@app.post("/calificaciones/actualizar/{id_calificacion}")
def actualizar_calificacion(
    request: Request,
    id_calificacion: int,
    parcial_1: float = Form(...),
    parcial_2: float = Form(...),
    parcial_3: float = Form(...),
    csrf: None = Depends(csrf_protect),
    db: Session = Depends(get_db),
):
    respuesta = verificar_rol(request, "calificaciones", "admin", "docente")
    if respuesta:
        return respuesta

    calif = db.get(models.Calificacion, id_calificacion)
    if calif:
        calif.parcial_1 = parcial_1
        calif.parcial_2 = parcial_2
        calif.parcial_3 = parcial_3
        calif.promedio_final = round((parcial_1 + parcial_2 + parcial_3) / 3, 2)
        db.commit()
    return RedirectResponse(url="/?tab=calificaciones", status_code=status.HTTP_303_SEE_OTHER)
