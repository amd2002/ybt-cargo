from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models.models import Tariff, User
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from app.core.config import settings

router_tariffs = APIRouter(prefix="/api/tariffs", tags=["tariffs"])
router_auth    = APIRouter(prefix="/api/auth",    tags=["auth"])

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Auth ──────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

@router_auth.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not pwd_ctx.verify(req.password, user.hashed_pw):
        raise HTTPException(401, "Identifiants incorrects")
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)},
        settings.SECRET_KEY, algorithm="HS256"
    )
    return {"access_token": token, "username": user.username, "is_admin": user.is_admin}

# ── Tariffs ───────────────────────────────────────────────────────────────────
class TariffUpdate(BaseModel):
    destination: str
    rate:        float

@router_tariffs.get("/")
def get_tariffs(db: Session = Depends(get_db)):
    tariffs = db.query(Tariff).all()
    return [{"destination": t.destination, "rate": t.rate} for t in tariffs]

@router_tariffs.put("/")
def update_tariff(req: TariffUpdate, db: Session = Depends(get_db)):
    t = db.query(Tariff).filter(Tariff.destination == req.destination).first()
    if t:
        t.rate = req.rate
    else:
        db.add(Tariff(destination=req.destination, rate=req.rate))
    db.commit()
    return {"destination": req.destination, "rate": req.rate}
