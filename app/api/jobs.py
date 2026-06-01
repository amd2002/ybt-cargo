import tempfile, os
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.models import Job, Client, Tariff, JobStatus
from app.services.parser import parse_excel, compute_amounts
from app.workers.tasks import generate_job_pdfs
from pydantic import BaseModel

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# ── Schémas ───────────────────────────────────────────────────────────────────
class ItemUpdate(BaseModel):
    receipt:     str
    description: str
    quantity:    str
    cbm:         float

class ClientUpdate(BaseModel):
    id:          str
    name:        str
    phone:       str
    destination: str   # SL | GN
    items:       List[ItemUpdate]

class GenerateRequest(BaseModel):
    container_num: str
    load_date:     str
    eta:           str
    clients:       List[ClientUpdate]

# ── Upload & parse ─────────────────────────────────────────────────────────────
@router.post("/upload")
async def upload_excel(
    file:          UploadFile = File(...),
    container_num: str        = Form(...),
    load_date:     str        = Form(...),
    eta:           str        = Form(...),
    db:            Session    = Depends(get_db),
):
    if not file.filename.endswith((".xls", ".xlsx")):
        raise HTTPException(400, "Fichier Excel requis (.xls ou .xlsx)")

    # Sauvegarde temporaire
    suffix = ".xls" if file.filename.endswith(".xls") else ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        raw_clients = parse_excel(tmp_path)
    finally:
        os.unlink(tmp_path)

    # Tarifs depuis DB
    rates = {t.destination: t.rate for t in db.query(Tariff).all()}
    rate_sl = rates.get("SL", 280.0)
    rate_gn = rates.get("GN", 340.0)

    clients_with_amounts = compute_amounts(raw_clients, rate_sl, rate_gn)

    # Création du Job (sans lancer la génération)
    job = Job(
        container_num=container_num,
        load_date=load_date,
        eta=eta,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.flush()

    for c in clients_with_amounts:
        client = Client(
            job_id=job.id,
            name=c["name"],
            phone=c.get("phone",""),
            phone_key=c.get("phone_key",""),
            destination=c["destination"],
            total_cbm=c["total_cbm"],
            freight=c["freight"],
            custom=c["custom"],
            total_due=c["total_due"],
            items=c["items"],
            is_merged=c.get("is_merged", False),
        )
        db.add(client)

    db.commit()
    db.refresh(job)

    return {
        "job_id":  job.id,
        "clients": [
            {
                "id":          c.id,
                "name":        c.name,
                "phone":       c.phone,
                "destination": c.destination,
                "total_cbm":   c.total_cbm,
                "freight":     c.freight,
                "custom":      c.custom,
                "total_due":   c.total_due,
                "is_merged":   c.is_merged,
                "items":       c.items,
            }
            for c in db.query(Client).filter(Client.job_id == job.id).all()
        ],
        "rate_sl": rate_sl,
        "rate_gn": rate_gn,
    }

# ── Génération (après corrections UI) ─────────────────────────────────────────
@router.post("/{job_id}/generate")
async def generate(job_id: str, req: GenerateRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job introuvable")

    # Tarifs depuis DB
    rates  = {t.destination: t.rate for t in db.query(Tariff).all()}
    rate_sl = rates.get("SL", 280.0)
    rate_gn = rates.get("GN", 340.0)

    # Mise à jour des clients avec les corrections de l'UI
    db.query(Client).filter(Client.job_id == job_id).delete()
    for cu in req.clients:
        items     = [i.model_dump() for i in cu.items]
        total_cbm = round(sum(float(i["cbm"]) for i in items), 10)
        rate      = rate_gn if cu.destination == "GN" else rate_sl
        freight   = round((total_cbm * rate) / 2, 10)
        custom    = round((total_cbm * rate) / 2, 10)
        total_due = round(total_cbm * rate, 10)
        client    = Client(
            job_id=job_id, name=cu.name, phone=cu.phone,
            destination=cu.destination, total_cbm=total_cbm,
            freight=freight, custom=custom, total_due=total_due, items=items,
        )
        db.add(client)

    job.container_num = req.container_num
    job.load_date     = req.load_date
    job.eta           = req.eta
    job.status        = JobStatus.PENDING
    job.zip_url       = None
    db.commit()

    # Lance la génération en arrière-plan
    generate_job_pdfs.delay(job_id)
    return {"job_id": job_id, "status": "pending"}

# ── Statut du job ─────────────────────────────────────────────────────────────
@router.get("/{job_id}/status")
def job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job introuvable")
    return {
        "status":  job.status,
        "zip_url": job.zip_url,
        "error":   job.error,
    }

# ── Historique ────────────────────────────────────────────────────────────────
@router.get("/")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(50).all()
    return [
        {
            "id":            j.id,
            "container_num": j.container_num,
            "load_date":     j.load_date,
            "eta":           j.eta,
            "status":        j.status,
            "zip_url":       j.zip_url,
            "created_at":    j.created_at.isoformat() if j.created_at else None,
            "nb_clients":    db.query(Client).filter(Client.job_id == j.id).count(),
        }
        for j in jobs
    ]
