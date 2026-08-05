from typing import List, Optional
from sqlalchemy import String, ForeignKey, DECIMAL, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

# 1. Entidad Usuarios
class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    correo: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relación uno a muchos hacia Inscripciones
    inscripciones: Mapped[List["Inscripcion"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")

# 2. Entidad Materias
class Materia(Base):
    __tablename__ = "materias"

    id_materia: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clave: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nombre_mat: Mapped[str] = mapped_column(String(100), nullable=False)
    creditos: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relación uno a muchos hacia Inscripciones
    inscripciones: Mapped[List["Inscripcion"]] = relationship(back_populates="materia", cascade="all, delete-orphan")

# 3. Entidad Intermedia Inscripciones
class Inscripcion(Base):
    __tablename__ = "inscripciones"
    __table_args__ = (
        # Evita que un alumno se inscriba dos veces en la misma materia y periodo
        UniqueConstraint("id_usuario", "id_materia", "periodo", name="uq_inscripcion_usuario_materia_periodo"),
    )

    id_inscripcion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id_usuario", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    id_materia: Mapped[int] = mapped_column(ForeignKey("materias.id_materia", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    periodo: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relaciones inversas
    usuario: Mapped["Usuario"] = relationship(back_populates="inscripciones")
    materia: Mapped["Materia"] = relationship(back_populates="inscripciones")
    calificaciones: Mapped[List["Calificacion"]] = relationship(back_populates="inscripcion", cascade="all, delete-orphan")

# 4. Entidad Calificaciones
class Calificacion(Base):
    __tablename__ = "calificaciones"

    id_calificacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_inscripcion: Mapped[int] = mapped_column(ForeignKey("inscripciones.id_inscripcion", ondelete="CASCADE"), nullable=False)
    parcial_1: Mapped[float] = mapped_column(DECIMAL(4, 2), default=0.00)
    parcial_2: Mapped[float] = mapped_column(DECIMAL(4, 2), default=0.00)
    parcial_3: Mapped[float] = mapped_column(DECIMAL(4, 2), default=0.00)
    promedio_final: Mapped[float] = mapped_column(DECIMAL(4, 2), default=0.00)

    # Relación inversa
    inscripcion: Mapped["Inscripcion"] = relationship(back_populates="calificaciones")
