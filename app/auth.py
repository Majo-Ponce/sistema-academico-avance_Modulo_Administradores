from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.schemas import LoginRequest, Token
from app.security import verify_password, create_access_token

router = APIRouter(tags=["Autenticación"])


@router.post("/login", response_model=Token)
def login(credenciales: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == credenciales.email).first()

    if not usuario or not verify_password(credenciales.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": usuario.email, "rol": usuario.rol.value}
    )
    return Token(access_token=access_token)