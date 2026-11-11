import base64
import binascii
from datetime import date
from typing import Literal
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
from app.models import RolEnum

EstadoEstudiante = Literal["ACTIVO", "INACTIVO", "GRADUADO"]
EstadoDocente = Literal["ACTIVO", "INACTIVO"]
EstadoSeccion = Literal["ABIERTA", "CERRADA", "FINALIZADA"]
EstadoMatricula = Literal["MATRICULADA", "CANCELADA"]
EstadoAsistencia = Literal["PRESENTE", "AUSENTE", "TARDANZA", "JUSTIFICADO"]
RolUsuario = Literal["ADMIN", "DOCENTE"]


class MensajeRespuesta(BaseModel):
    mensaje: str


class UsuarioLogin(BaseModel):
    usuario: str = Field(
        min_length=3,
        max_length=120,
        validation_alias=AliasChoices("usuario", "email"),
    )
    clave: str = Field(
        min_length=4,
        max_length=100,
        validation_alias=AliasChoices("clave", "password"),
    )


class UsuarioRespuesta(BaseModel):
    id: int
    usuario: str
    nombre_completo: str
    rol: RolUsuario
    docente_id: int | None = None
    cambiar_password: bool = False
    debe_cambiar_password: bool = False


class LoginRespuesta(UsuarioRespuesta):
    """Respuesta de /auth/login: datos del usuario + token JWT.

    Hereda de UsuarioRespuesta para no romper a quien ya lea
    `rol`, `usuario`, etc. directamente de la respuesta, y agrega el
    token que el frontend guarda con guardarSesion() (frontend/auth.js).
    """

    access_token: str
    token_type: str = "bearer"


class AdministradorEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usuario: str = Field(min_length=3, max_length=120)
    nombre: str = Field(min_length=2, max_length=120)
    email: EmailStr
    activo: bool = True


class AdministradorRespuesta(BaseModel):
    id: int
    usuario: str
    nombre: str
    email: EmailStr
    activo: bool
    cambiar_password: bool
    debe_cambiar_password: bool


class CambioPasswordEntrada(BaseModel):
    clave_actual: str = Field(min_length=1, max_length=100)
    clave_nueva: str = Field(min_length=8, max_length=100)


class CarreraEntrada(BaseModel):
    codigo: str = Field(min_length=2, max_length=10)
    nombre: str = Field(min_length=4, max_length=120)
    duracion_anios: int = Field(ge=1, le=10)
    activo: bool = True


class CarreraRespuesta(CarreraEntrada):
    id: int


class EstudianteEntrada(BaseModel):
    cuenta: str = Field(min_length=5, max_length=20)
    nombres: str = Field(min_length=2, max_length=80)
    apellidos: str = Field(min_length=2, max_length=80)
    correo: EmailStr
    telefono: str | None = Field(default=None, max_length=25)
    fecha_nacimiento: date
    carrera_id: int = Field(gt=0)
    estado: EstadoEstudiante = "ACTIVO"

    @field_validator("fecha_nacimiento")
    @classmethod
    def validar_fecha_nacimiento(cls, valor: date) -> date:
        if valor >= date.today():
            raise ValueError("La fecha de nacimiento debe ser anterior a hoy")
        return valor


class EstudianteRespuesta(EstudianteEntrada):
    id: int
    carrera_codigo: str
    carrera_nombre: str


class DocenteEntrada(BaseModel):
    numero_empleado: str = Field(min_length=3, max_length=20)
    nombres: str = Field(min_length=2, max_length=80)
    apellidos: str = Field(min_length=2, max_length=80)
    correo: EmailStr
    especialidad: str = Field(min_length=3, max_length=120)
    estado: EstadoDocente = "ACTIVO"
    clave: str | None = Field(default=None, min_length=8, max_length=100, exclude=True)


class DocenteRespuesta(DocenteEntrada):
    id: int


class PerfilDocenteEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombres: str = Field(min_length=2, max_length=80)
    apellidos: str = Field(min_length=2, max_length=80)
    numero_identidad: str | None = Field(default=None, max_length=30)
    fecha_nacimiento: date | None = None
    nacionalidad: str | None = Field(default=None, max_length=80)
    tipo_nacionalidad: str | None = Field(default=None, max_length=80)
    fecha_ingreso: date | None = None
    foto_perfil: str | None = Field(default=None, max_length=2_800_000)

    @field_validator(
        "numero_identidad", "nacionalidad", "tipo_nacionalidad", mode="before"
    )
    @classmethod
    def normalizar_textos_opcionales(cls, valor):
        if valor is None:
            return None
        texto = str(valor).strip()
        return texto or None

    @field_validator("fecha_nacimiento", "fecha_ingreso")
    @classmethod
    def validar_fechas_no_futuras(cls, valor: date | None) -> date | None:
        if valor is not None and valor > date.today():
            raise ValueError("La fecha no puede ser futura")
        return valor

    @field_validator("foto_perfil")
    @classmethod
    def validar_foto_perfil(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        prefijos = {
            "data:image/jpeg;base64,": "jpeg",
            "data:image/png;base64,": "png",
            "data:image/webp;base64,": "webp",
        }
        prefijo = next((item for item in prefijos if valor.startswith(item)), None)
        if prefijo is None:
            raise ValueError("La fotografía debe ser JPG, PNG o WEBP")
        try:
            contenido = base64.b64decode(valor[len(prefijo):], validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError("La fotografía no contiene datos válidos") from error
        if not contenido or len(contenido) > 2 * 1024 * 1024:
            raise ValueError("La fotografía no puede superar 2 MB")
        tipo = prefijos[prefijo]
        if tipo == "jpeg":
            firma_valida = contenido.startswith(b"\xff\xd8\xff")
        elif tipo == "png":
            firma_valida = contenido.startswith(b"\x89PNG\r\n\x1a\n")
        else:
            firma_valida = contenido.startswith(b"RIFF") and contenido[8:12] == b"WEBP"
        if not firma_valida:
            raise ValueError("El contenido de la fotografía no coincide con su formato")
        return valor


class AsignaturaEntrada(BaseModel):
    codigo: str = Field(min_length=3, max_length=15)
    nombre: str = Field(min_length=3, max_length=120)
    unidades_valorativas: int = Field(ge=1, le=8)
    carrera_ids: list[int] | None = Field(default=None, min_length=1)
    carrera_id: int | None = Field(default=None, gt=0)
    requisito_id: int | None = Field(default=None, gt=0)
    activo: bool = True

    @model_validator(mode="after")
    def validar_carreras(self):
        if self.carrera_ids is None and self.carrera_id is not None:
            self.carrera_ids = [self.carrera_id]
        if not self.carrera_ids:
            raise ValueError("Seleccione al menos una carrera")
        if any(carrera_id <= 0 for carrera_id in self.carrera_ids):
            raise ValueError("Los identificadores de carrera deben ser positivos")
        if len(set(self.carrera_ids)) != len(self.carrera_ids):
            raise ValueError("No se puede seleccionar una carrera más de una vez")
        self.carrera_id = self.carrera_ids[0]
        return self


class AsignaturaRespuesta(BaseModel):
    id: int
    codigo: str
    nombre: str
    unidades_valorativas: int
    carrera_id: int
    carrera_ids: list[int]
    carrera_nombre: str
    carrera_nombres: list[str]
    requisito_id: int | None = None
    requisito_codigo: str | None = None
    activo: bool


class PeriodoEntrada(BaseModel):
    anio: int = Field(ge=2020, le=2100)
    numero: int = Field(ge=1, le=4)
    fecha_inicio: date
    fecha_fin: date
    activo: bool = False

    @field_validator("fecha_fin")
    @classmethod
    def validar_fecha_fin(cls, valor: date, info):
        inicio = info.data.get("fecha_inicio")
        if inicio and valor <= inicio:
            raise ValueError("La fecha final debe ser posterior a la fecha inicial")
        return valor


class PeriodoRespuesta(PeriodoEntrada):
    id: int
    nombre: str


class AulaEntrada(BaseModel):
    codigo: str = Field(min_length=2, max_length=20)
    edificio: str = Field(min_length=2, max_length=80)
    capacidad: int = Field(ge=1, le=200)
    activo: bool = True


class AulaRespuesta(AulaEntrada):
    id: int


class SeccionEntrada(BaseModel):
    codigo: str = Field(min_length=2, max_length=10)
    asignatura_id: int = Field(gt=0)
    docente_id: int = Field(gt=0)
    periodo_id: int = Field(gt=0)
    aula_id: int | None = Field(default=None, gt=0)
    dias: str = Field(min_length=2, max_length=30, examples=["LU-MI"])
    hora_inicio: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    hora_fin: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    cupo_maximo: int = Field(ge=1, le=200)
    estado: EstadoSeccion = "ABIERTA"

    @field_validator("hora_fin")
    @classmethod
    def validar_horario(cls, valor: str, info):
        inicio = info.data.get("hora_inicio")
        if inicio and valor <= inicio:
            raise ValueError("La hora final debe ser posterior a la hora inicial")
        return valor


class SeccionRespuesta(SeccionEntrada):
    id: int
    asignatura_codigo: str
    asignatura_nombre: str
    docente_nombre: str
    periodo_nombre: str
    aula_codigo: str | None = None
    matriculados: int
    cupos_disponibles: int


class MatriculaEntrada(BaseModel):
    estudiante_id: int = Field(gt=0)
    seccion_id: int = Field(gt=0)


class MatriculaRespuesta(BaseModel):
    id: int
    estudiante_id: int
    estudiante_cuenta: str
    estudiante_nombre: str
    seccion_id: int
    asignatura_codigo: str
    asignatura_nombre: str
    seccion_codigo: str
    periodo_nombre: str
    fecha_matricula: str
    estado: EstadoMatricula


class CalificacionEntrada(BaseModel):
    primer_parcial: float = Field(ge=0, le=100)
    segundo_parcial: float = Field(ge=0, le=100)
    tercer_parcial: float = Field(ge=0, le=100)
    observacion: str | None = Field(default=None, max_length=250)


class ParcialEntrada(BaseModel):
    parcial: Literal[1, 2, 3]
    nota: float = Field(ge=0, le=100)


class AsistenciaSesionEntrada(BaseModel):
    fecha: date


class AsistenciaRegistroEntrada(BaseModel):
    matricula_id: int = Field(gt=0)
    estado: EstadoAsistencia


class AsistenciaRegistrosEntrada(BaseModel):
    registros: list[AsistenciaRegistroEntrada]


class CalificacionRespuesta(CalificacionEntrada):
    id: int
    matricula_id: int
    primer_parcial: float | None = None
    segundo_parcial: float | None = None
    tercer_parcial: float | None = None
    nota_final: float | None = None
    resultado: Literal["APROBADA", "REPROBADA"] | None = None

#
class UsuarioBase(BaseModel):
    email: EmailStr
    rol: RolEnum

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioOut(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    sub: str | None = None
    rol: RolEnum | None = None