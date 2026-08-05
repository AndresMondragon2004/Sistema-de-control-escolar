# 🎓 Control Escolar UMB — Sistema Web de Gestión Escolar

Sistema web **full-stack** para el control escolar: gestión de **usuarios** (alumnos, docentes y administradores), **materias**, **inscripciones** y **calificaciones**, con un dashboard moderno, autenticación por sesiones y control de acceso por roles.

Construido con **Python (FastAPI)**, **SQLAlchemy**, **PostgreSQL (Supabase)** y **Jinja2 + Tailwind CSS**, desplegable en **Vercel**.

---

## ✨ Funcionalidades

### CRUD completo (4 entidades)
| Entidad | Crear | Leer | Editar | Eliminar |
|---------|:-----:|:----:|:------:|:--------:|
| **Usuarios** (alumno/docente/admin) | ✅ | ✅ | ✅ | ✅ |
| **Materias** (clave, nombre, créditos) | ✅ | ✅ | ✅ | ✅ |
| **Inscripciones** (alumno ↔ materia + periodo) | ✅ | ✅ | ✅ | ✅ |
| **Calificaciones** (3 parciales + promedio) | ✅ | ✅ | ✅ | — |

### Detalles de funcionamiento
- **Promedio automático**: al guardar los 3 parciales se recalcula `promedio_final` (0–10) con insignia de color (verde ≥ 8, ámbar < 8).
- **Calificación automática**: al inscribir a un alumno se crea su registro de calificaciones en `0.00`.
- **Prevención de duplicados**: no se permite inscribir al mismo alumno en la misma materia y periodo (a nivel de aplicación **y** con restricción `UNIQUE` en la base de datos).
- **Bajas en cascada**: al eliminar un usuario o materia se eliminan sus inscripciones y calificaciones; al eliminar una inscripción se eliminan sus calificaciones.
- **Formularios con validación**: patrones de entrada (solo letras, claves en mayúsculas, créditos 1–10, calificaciones 0–10), modal de confirmación para eliminar y modales de edición.
- **Estados vacíos**: mensajes y avisos útiles cuando no hay alumnos, materias o registros.

---

## 🔐 Seguridad

- **Autenticación por sesiones**: cookies firmadas con `itsdangerous` (Starlette `SessionMiddleware`), `SameSite=Lax` y flag `Secure` configurable (`SESSION_HTTPS_ONLY`).
- **Contraseñas hasheadas** con **bcrypt** (nunca se almacenan en texto plano).
  - *Migración automática*: las contraseñas legadas guardadas en texto plano se re-hashean al primer inicio de sesión exitoso.
- **Protección CSRF**: token por sesión validado en **todos** los endpoints `POST` (responde `403` si falta o no coincide).
- **Control de acceso por roles**:

| Rol | Usuarios | Materias | Inscripciones | Calificaciones |
|-----|:--------:|:--------:|:-------------:|:--------------:|
| `admin` | ✅ | ✅ | ✅ | ✅ |
| `docente` | ❌ | ✅ | ✅ | ✅ |
| `alumno` | ❌ | ❌ | ❌ | ❌ (solo lectura) |

- **Anti fuerza bruta**: tras 5 intentos de inicio de sesión fallidos se bloquea temporalmente por 60 segundos.
- **Cabeceras de seguridad**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`.
- **Credenciales fuera del código**: toda la configuración sensible se lee de variables de entorno (`.env` en local, panel de Vercel en la nube).

---

## 🧰 Tecnologías

| Capa | Tecnología |
|------|------------|
| Backend | Python 3, **FastAPI**, **Uvicorn** |
| ORM | **SQLAlchemy 2** (modelos con `Mapped`/`mapped_column`) |
| Base de datos | **PostgreSQL** en **Supabase** (`psycopg2-binary`) |
| Plantillas | **Jinja2** (SSR) |
| Frontend | **Tailwind CSS** (CDN), **Font Awesome**, **Google Fonts (Inter)** |
| Seguridad | **bcrypt**, `itsdangerous` (sesiones), token CSRF, `python-dotenv` |
| Despliegue | **Vercel** (`vercel.json` + `api/index.py`) |

---

## 📁 Estructura del proyecto

```
control-escolar-web/
├── main.py              # Aplicación FastAPI: rutas, autenticación, CSRF, roles
├── models.py            # Modelos SQLAlchemy (Usuario, Materia, Inscripcion, Calificacion)
├── database.py          # Motor de BD, sesiones y dependencia get_db
├── security.py          # Hashing y verificación de contraseñas (bcrypt)
├── create_table.py      # Inicialización: tablas, constraint UNIQUE y admin inicial
├── requirements.txt     # Dependencias de Python
├── .env.example         # Plantilla de variables de entorno (local)
├── .env                 # Variables locales (NO se sube al repositorio)
├── vercel.json          # Configuración de despliegue en Vercel
├── api/
│   └── index.py         # Handler serverless de Vercel
└── templates/
    ├── base.html        # Layout principal (header con usuario, logout, footer)
    ├── index.html       # Dashboard con 4 pestañas (CRUD completo)
    └── login.html       # Página de inicio de sesión
```

---

## 🗄️ Modelo de datos

```
usuarios ──1──< inscripciones >──1── materias
                │
                └──1──< calificaciones
```

| Tabla | Campos |
|-------|--------|
| `usuarios` | `id_usuario` (PK), `nombre`, `correo` (unique), `password` (hash bcrypt), `rol` (`alumno`/`docente`/`admin`) |
| `materias` | `id_materia` (PK), `clave` (unique), `nombre_mat`, `creditos` |
| `inscripciones` | `id_inscripcion` (PK), `id_usuario` (FK), `id_materia` (FK), `periodo` — **UNIQUE** (`id_usuario`, `id_materia`, `periodo`) |
| `calificaciones` | `id_calificacion` (PK), `id_inscripcion` (FK, ON DELETE CASCADE), `parcial_1`, `parcial_2`, `parcial_3`, `promedio_final` |

---

## 🚀 Instalación y ejecución local

### 1. Requisitos
- Python 3.10+ (el proyecto se probó con Python 3.14)
- Una base de datos PostgreSQL (se recomienda **Supabase**, plan gratuito)

### 2. Clonar e instalar dependencias

```bash
git clone <url-del-repositorio>
cd control-escolar-web

# Crear entorno virtual (recomendado)
python -m venv venv

# Activar (Windows)
venv\Scripts\activate
# Activar (macOS/Linux)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
# 1) Copiar la plantilla
cp .env.example .env        # Windows: copy .env.example .env

# 2) Editar .env con tus datos
```

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL **<sup>1</sup>** | `postgresql://usuario:clave@host.supabase.com:6543/postgres` |
| `SESSION_SECRET` | Clave para firmar las cookies de sesión <sup>2</sup> | `x7K...generada` |
| `SESSION_HTTPS_ONLY` | `true` si el sitio usa https (producción) | `false` en local |
| `ADMIN_EMAIL` | Correo del admin inicial (opcional) | `admin@control.com` |
| `ADMIN_PASSWORD` | Contraseña del admin inicial (opcional) | `admin123` |

<sup>1</sup> Consíguela en Supabase → *Project Settings → Database → Connection string (URI)*.
<sup>2</sup> Genérala con: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

### 4. Inicializar la base de datos (una sola vez)

```bash
python create_table.py
```

Este script:
1. Crea/verifica las 4 tablas.
2. **Limpia inscripciones duplicadas** (conserva la de menor id y elimina sus calificaciones).
3. Agrega la restricción `UNIQUE (id_usuario, id_materia, periodo)` si no existe.
4. **Crea el administrador inicial** si no existe ningún `admin`.

### 5. Ejecutar la aplicación

```bash
uvicorn main:app --reload
```

Abre **http://localhost:8000** → serás redirigido a `/login`.

> **Primer acceso:** `admin@control.com` / `admin123` (el aviso solo aparece cuando la base está vacía). **Cámbiala** desde Usuarios → Editar.

---

## ☁️ Despliegue en Vercel

El proyecto ya incluye `vercel.json` (función serverless en `api/index.py`).

1. Sube el proyecto a un repositorio de GitHub/GitLab.
2. En Vercel: **Add New → Project** e importa el repositorio.
   - *Framework Preset*: **Other**
   - *Build Command*: vacío · *Output Directory*: vacío
3. En **Settings → Environment Variables** agrega:
   - `DATABASE_URL` (la URL de Supabase)
   - `SESSION_SECRET` (clave aleatoria nueva)
   - `SESSION_HTTPS_ONLY` → `true`
   - `ADMIN_EMAIL` / `ADMIN_PASSWORD` (opcionales)
4. Despliega ✅

> El archivo `.env` está en `.gitignore` y **no** se sube al repositorio; en producción las variables se configuran desde el panel de Vercel.

---

## 🧪 Pruebas

La aplicación se validó de forma automatizada con `TestClient` (FastAPI) y una base **SQLite en memoria** (sobreescribiendo `get_db`), cubriendo:

- Hashing y verificación bcrypt (incluida la migración de contraseñas en texto plano).
- Redirección a `/login` sin sesión.
- Rechazo CSRF (token ausente o inválido → `403`).
- Login/logout, bloqueo tras 5 intentos fallidos.
- CRUD completo de usuarios, materias, inscripciones y calificaciones (crear, editar, eliminar, duplicados).
- Control de acceso por roles (admin, docente, alumno).

---

## 🔌 Endpoints principales

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/` | Dashboard (pestañas) | Cualquier sesión |
| GET | `/login` | Página de inicio de sesión | Público |
| POST | `/login` | Iniciar sesión | Público (CSRF) |
| POST | `/logout` | Cerrar sesión | Sesión |
| POST | `/usuarios/crear` · `/editar/{id}` · `/eliminar/{id}` | CRUD usuarios | `admin` |
| POST | `/materias/crear` · `/editar/{id}` · `/eliminar/{id}` | CRUD materias | `admin`, `docente` |
| POST | `/inscripciones/crear` · `/editar/{id}` · `/eliminar/{id}` | CRUD inscripciones | `admin`, `docente` |
| POST | `/calificaciones/actualizar/{id}` | Actualizar parciales y promedio | `admin`, `docente` |

Todas las rutas `POST` exigen el token CSRF de la sesión.

---

## 🛠️ Solución de problemas

| Problema | Solución |
|----------|----------|
| `Falta la variable de entorno DATABASE_URL` | Crea el `.env` a partir de `.env.example` y completa la URL. |
| `Error al conectar con la base de datos` al correr `create_table.py` | Verifica la URL y que la IP/región de Supabase permita la conexión. |
| No recuerdas la contraseña del admin | Ejecuta de nuevo `create_table.py` (no crea otro admin si ya existe); borra el `admin` o cámbiala desde la BD. |
| Cookie de sesión no persiste en producción | Activa `SESSION_HTTPS_ONLY=true` y usa un `SESSION_SECRET` fijo (si cambia, se invalidan las sesiones). |
| `403` al enviar un formulario | La sesión expiró o el token CSRF cambió: recarga la página e intenta de nuevo. |

---

## 🔒 Recomendaciones de seguridad adicionales

- **Rota la contraseña de Supabase** si la URL con credenciales estuvo expuesta en el repositorio (como en versiones anteriores de este proyecto).
- Usa un `SESSION_SECRET` largo y único por entorno; **no** reutilices el de desarrollo en producción.
- Considera cifrar el tráfico con https (Vercel lo hace automáticamente) y activar `SESSION_HTTPS_ONLY=true`.
- Para un despliegue real, evalúa agregar: recuperación de contraseña, registro de auditoría y límites de concurrencia.

---

## 📄 Licencia

Proyecto académico: *Programación Web con Bases de Datos* — UMB, © 2026.
