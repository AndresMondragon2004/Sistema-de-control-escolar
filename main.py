from fastapi import FastAPI, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import get_db
import models

app = FastAPI(title="Control Escolar Web")
templates = Jinja2Templates(directory="templates")

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
            "calificaciones": calificaciones
        }
    )

# ---------------------------------------------------------
# CRUD: USUARIOS
# ---------------------------------------------------------
@app.post("/usuarios/crear")
def crear_usuario(
    nombre: str = Form(...),
    correo: str = Form(...),
    password: str = Form(...),
    rol: str = Form(...),
    db: Session = Depends(get_db)
):
    nuevo_usuario = models.Usuario(nombre=nombre, correo=correo, password=password, rol=rol)
    try:
        db.add(nuevo_usuario)
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url="/?tab=usuarios&error=correo_existe", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/?tab=usuarios", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/usuarios/eliminar/{id_usuario}")
def eliminar_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = db.get(models.Usuario, id_usuario)
    if usuario:
        db.delete(usuario)
        db.commit()
    return RedirectResponse(url="/?tab=usuarios", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/usuarios/editar/{id_usuario}")
def editar_usuario(
    id_usuario: int,
    nombre: str = Form(...),
    correo: str = Form(...),
    rol: str = Form(...),
    db: Session = Depends(get_db)
):
    usuario = db.get(models.Usuario, id_usuario)
    if not usuario:
        return RedirectResponse(url="/?tab=usuarios&error=no_encontrado", status_code=status.HTTP_303_SEE_OTHER)

    usuario.nombre = nombre
    usuario.correo = correo
    usuario.rol = rol
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
    clave: str = Form(...),
    nombre_mat: str = Form(...),
    creditos: int = Form(...),
    db: Session = Depends(get_db)
):
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
    id_materia: int,
    clave: str = Form(...),
    nombre_mat: str = Form(...),
    creditos: int = Form(...),
    db: Session = Depends(get_db)
):
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
def eliminar_materia(id_materia: int, db: Session = Depends(get_db)):
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
    id_usuario: int = Form(...),
    id_materia: int = Form(...),
    periodo: str = Form(...),
    db: Session = Depends(get_db)
):
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
    id_inscripcion: int,
    id_usuario: int = Form(...),
    id_materia: int = Form(...),
    periodo: str = Form(...),
    db: Session = Depends(get_db)
):
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
def eliminar_inscripcion(id_inscripcion: int, db: Session = Depends(get_db)):
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
    id_calificacion: int,
    parcial_1: float = Form(...),
    parcial_2: float = Form(...),
    parcial_3: float = Form(...),
    db: Session = Depends(get_db)
):
    calif = db.get(models.Calificacion, id_calificacion)
    if calif:
        calif.parcial_1 = parcial_1
        calif.parcial_2 = parcial_2
        calif.parcial_3 = parcial_3
        calif.promedio_final = round((parcial_1 + parcial_2 + parcial_3) / 3, 2)
        db.commit()
    return RedirectResponse(url="/?tab=calificaciones", status_code=status.HTTP_303_SEE_OTHER)
