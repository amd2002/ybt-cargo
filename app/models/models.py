from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, JSON, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid, enum

def gen_uuid():
    return str(uuid.uuid4())

class JobStatus(str, enum.Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"

class Destination(str, enum.Enum):
    SL = "SL"   # Sierra Leone — 280$/CBM
    GN = "GN"   # Guinée      — 340$/CBM

# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id            = Column(String, primary_key=True, default=gen_uuid)
    username      = Column(String, unique=True, nullable=False)
    hashed_pw     = Column(String, nullable=False)
    is_admin      = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    jobs          = relationship("Job", back_populates="user")

# ── Tariffs (modifiables sans toucher au code) ────────────────────────────────
class Tariff(Base):
    __tablename__ = "tariffs"
    id            = Column(String, primary_key=True, default=gen_uuid)
    destination   = Column(String, nullable=False)   # "SL" | "GN"
    rate          = Column(Float, nullable=False)
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by    = Column(String, ForeignKey("users.id"))

# ── Jobs (un job = un conteneur uploadé) ─────────────────────────────────────
class Job(Base):
    __tablename__ = "jobs"
    id            = Column(String, primary_key=True, default=gen_uuid)
    container_num = Column(String, nullable=False)
    load_date     = Column(String, nullable=False)
    eta           = Column(String, nullable=False)
    status        = Column(String, default=JobStatus.PENDING)
    error         = Column(Text, nullable=True)
    zip_url       = Column(String, nullable=True)   # URL R2 du ZIP final
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    user_id       = Column(String, ForeignKey("users.id"))
    user          = relationship("User", back_populates="jobs")
    clients       = relationship("Client", back_populates="job", cascade="all, delete-orphan")

# ── Clients (extraits de l'Excel, éditables avant génération) ────────────────
class Client(Base):
    __tablename__ = "clients"
    id            = Column(String, primary_key=True, default=gen_uuid)
    job_id        = Column(String, ForeignKey("jobs.id"))
    name          = Column(String, nullable=False)
    phone         = Column(String, default="")
    phone_key     = Column(String, default="")      # numéro normalisé pour dédup
    destination   = Column(String, default="SL")    # SL | GN
    total_cbm     = Column(Float, default=0.0)
    freight       = Column(Float, default=0.0)
    custom        = Column(Float, default=0.0)
    total_due     = Column(Float, default=0.0)
    items         = Column(JSON, default=list)       # [{receipt, description, quantity, cbm}]
    pdf_url       = Column(String, nullable=True)   # URL R2 du PDF individuel
    is_merged     = Column(Boolean, default=False)  # fusionné depuis plusieurs lignes
    job           = relationship("Job", back_populates="clients")
