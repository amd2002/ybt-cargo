from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from app.core.database import Base, engine
from app.api.jobs import router as jobs_router
from app.api.tariffs import router_tariffs, router_auth
from app.models.models import Tariff
from app.core.database import SessionLocal
from pathlib import Path

# Créer les tables au démarrage
Base.metadata.create_all(bind=engine)

# Insérer les tarifs par défaut si absents
def init_tariffs():
    db = SessionLocal()
    try:
        for dest, rate in [("SL", 280.0), ("GN", 340.0)]:
            if not db.query(Tariff).filter(Tariff.destination == dest).first():
                db.add(Tariff(destination=dest, rate=rate))
        db.commit()
    finally:
        db.close()

app = FastAPI(title="YBT Cargo Manager", version="1.0.0")

@app.on_event("startup")
def startup():
    init_tariffs()

# Static files & templates
static_path = Path(__file__).parent.parent / "frontend" / "static"
templates_path = Path(__file__).parent.parent / "frontend" / "templates"

app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
templates = Jinja2Templates(directory=str(templates_path))

# Routers
app.include_router(jobs_router)
app.include_router(router_tariffs)
app.include_router(router_auth)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health():
    return {"status": "ok"}
