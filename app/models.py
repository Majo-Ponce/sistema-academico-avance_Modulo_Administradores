import enum
from sqlalchemy import Column, Integer, String, Enum
from app.database import Base  # Ajusta este import a tu módulo de conexión SQLite

class RolEnum(str, enum.Enum):
    ADMINISTRADOR = "administrador"
    DOCENTE = "docente"
    ESTUDIANTE = "estudiante"

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    rol = Column(Enum(RolEnum), nullable=False)