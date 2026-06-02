import tempfile, os, zipfile, shutil, traceback
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.models import Job, Client, Tariff
from app.services.parser import parse_excel, compute_amounts
from app.services.generator import generate_invoice_pdf
from pydantic import BaseModel

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

class ItemUpdate(BaseModel):
    receipt:     str = ""
    description: str
    quantity:    str
    cbm:         float

class ClientUpdate(BaseModel):
    id:          str = ""
    name:        str
    phone:       str
    destination: str
    items:       List[ItemUpdate]

class GenerateRequest(BaseModel):
    container_num: str
    load_date:     str
    eta:           str
    clients:       List[ClientUpdate]

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
    suffix = ".xls" if file.filename.endswith(".xls") else ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        raw_clients = parse_excel(tmp_path)
    finally:
        os.unlink(tmp_path)
    rates   = {t.destination: t.rate for t in db.query(Tariff).all()}
    rate_sl = rates.get("SL", 280.0)
    rate_gn = rates.get("GN", 340.0)
    clients_with_amounts = compute_amounts(raw_clients, rate_sl, rate_gn)
    job = Job(container_num=container_num, load_date=load_date, eta=eta, status="pending")
    db.add(job)
    db.flush()
    for c in clients_with_amounts:
        db.add(Client(
            job_id=job.id, name=c["name"], phone=c.get("phone",""),
            phone_key=c.get("phone_key",""), destination=c["destination"],
            total_cbm=c["total_cbm"], freight=c["freight"],
            custom=c["custom"], total_due=c["total_due"],
            items=c["items"], is_merged=c.get("is_merged", False),
        ))
    db.commit()
    db.refresh(job)
    return {
        "job_id": job.id,
        "clients": [
            {"id":c.id,"name":c.name,"phone":c.phone,"destination":c.destination,
             "total_cbm":c.total_cbm,"freight":c.freight,"custom":c.custom,
             "total_due":c.total_due,"is_merged":c.is_merged,"items":c.items}
            for c in db.query(Client).filter(Client.job_id == job.id).all()
        ],
        "rate_sl": rate_sl, "rate_gn": rate_gn,
    }

@router.post("/{job_id}/generate")
async def generate(job_id: str, req: GenerateRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job introuvable")
    rates   = {t.destination: t.rate for t in db.query(Tariff).all()}
    rate_sl = rates.get("SL", 280.0)
    rate_gn = rates.get("GN", 340.0)
    db.query(Client).filter(Client.job_id == job_id).delete()
    for cu in req.clients:
        items     = [i.model_dump() for i in cu.items]
        total_cbm = round(sum(float(i["cbm"]) for i in items), 10)
        rate      = rate_gn if cu.destination == "GN" else rate_sl
        freight   = round((total_cbm * rate) / 2, 10)
        custom    = round((total_cbm * rate) / 2, 10)
        total_due = round(total_cbm * rate, 10)
        db.add(Client(job_id=job_id, name=cu.name, phone=cu.phone,
            destination=cu.destination, total_cbm=total_cbm,
            freight=freight, custom=custom, total_due=total_due, items=items))
    job.container_num = req.container_num
    job.load_date     = req.load_date
    job.eta           = req.eta
    job.status        = "running"
    job.zip_url       = None
    db.commit()
    try:
        clients = db.query(Client).filter(Client.job_id == job_id).all()
        zip_path = tempfile.mktemp(suffix=".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for c in clients:
                rate = rate_gn if c.destination == "GN" else rate_sl
                cd = {
                    "name": c.name, "phone": c.phone,
                    "destination": c.destination,
                    "total_cbm": c.total_cbm, "freight": c.freight,
                    "custom": c.custom, "total_due": c.total_due,
                    "rate": rate, "items": c.items or [],
                }
                pdf = generate_invoice_pdf(cd, job.container_num, job.load_date, job.eta)
                safe = "".join(x if x.isalnum() else "_" for x in c.name)[:28]
                zf.write(pdf, f"Invoice_{safe}_{c.destination}.pdf")
                os.unlink(pdf)
        out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "static", "zips")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{job_id}.zip")
        shutil.move(zip_path, out_path)
        job.zip_url = f"/static/zips/{job_id}.zip"
        job.status  = "done"
        db.commit()
        return {"job_id": job_id, "status": "done", "zip_url": job.zip_url}
    except Exception as e:
        job.status = "failed"
        job.error  = str(e)
        db.commit()
        print(f"[GEN] ERREUR: {traceback.format_exc()}")
        raise HTTPException(500, f"Erreur génération: {str(e)}")

@router.get("/{job_id}/summary")
def download_summary(job_id: str, db: Session = Depends(get_db)):
    from app.services.summary import generate_summary_pdf
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job introuvable")
    clients = db.query(Client).filter(Client.job_id == job_id).all()
    clients_data = [
        {"name":c.name,"phone":c.phone,"destination":c.destination,
         "total_cbm":c.total_cbm,"freight":c.freight,
         "custom":c.custom,"total_due":c.total_due,"items":c.items or []}
        for c in clients
    ]
    job_data = {"container_num":job.container_num,"load_date":job.load_date,"eta":job.eta}
    pdf_path = generate_summary_pdf(job_data, clients_data)
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"Suivi_{job.container_num}.pdf")

@router.get("/{job_id}/clients")
def get_job_clients(job_id: str, db: Session = Depends(get_db)):
    clients = db.query(Client).filter(Client.job_id == job_id).all()
    return [
        {"name":c.name,"phone":c.phone,"destination":c.destination,
         "total_cbm":c.total_cbm,"freight":c.freight,"custom":c.custom,
         "total_due":c.total_due,"items":c.items or []}
        for c in clients
    ]

@router.delete("/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job introuvable")
    db.query(Client).filter(Client.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    return {"deleted": True}

@router.get("/")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(50).all()
    return [
        {"id":j.id,"container_num":j.container_num,"load_date":j.load_date,
         "eta":j.eta,"status":j.status,"zip_url":j.zip_url,
         "created_at":j.created_at.isoformat() if j.created_at else None,
         "nb_clients":db.query(Client).filter(Client.job_id==j.id).count()}
        for j in jobs
    ]