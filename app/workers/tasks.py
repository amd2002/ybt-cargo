import os
import zipfile
import tempfile
from celery import Celery
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import Job, Client, JobStatus
from app.services.generator import generate_invoice_pdf
from app.services.storage import upload_file

celery_app = Celery(
    "ybt_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,   # 1 tâche à la fois par worker = stable
    task_acks_late=True,
)

@celery_app.task(bind=True, max_retries=2)
def generate_job_pdfs(self, job_id: str):
    """
    Tâche asynchrone :
    1. Récupère les clients du job depuis la DB
    2. Génère un PDF par client
    3. Upload chaque PDF sur R2
    4. Crée un ZIP global et l'upload
    5. Met à jour le statut du job
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.status = JobStatus.RUNNING
        db.commit()

        clients = db.query(Client).filter(Client.job_id == job_id).all()
        pdf_paths = []

        with tempfile.TemporaryDirectory() as tmp_dir:

            for client in clients:
                client_dict = {
                    "name":      client.name,
                    "phone":     client.phone,
                    "destination": client.destination,
                    "total_cbm": client.total_cbm,
                    "freight":   client.freight,
                    "custom":    client.custom,
                    "total_due": client.total_due,
                    "rate":      client.freight * 2 / client.total_cbm if client.total_cbm else 280,
                    "items":     client.items or [],
                }

                pdf_path = generate_invoice_pdf(
                    client_dict,
                    job.container_num,
                    job.load_date,
                    job.eta,
                )

                # Upload PDF individuel
                safe_name = "".join(c if c.isalnum() else "_" for c in client.name)[:28]
                r2_key    = f"jobs/{job_id}/{safe_name}_{client.destination}.pdf"
                pdf_url   = upload_file(pdf_path, r2_key)
                client.pdf_url = pdf_url
                pdf_paths.append((pdf_path, f"Invoice_{safe_name}_{client.destination}.pdf"))
                os.unlink(pdf_path)

            db.commit()

            # Créer le ZIP
            zip_path = os.path.join(tmp_dir, f"YBT_{job.container_num}.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Re-télécharger depuis R2 pour le ZIP (ou garder en mémoire)
                for client in clients:
                    if client.pdf_url:
                        import urllib.request
                        pdf_data = urllib.request.urlopen(client.pdf_url).read()
                        safe = "".join(c if c.isalnum() else "_" for c in client.name)[:28]
                        zf.writestr(f"Invoice_{safe}_{client.destination}.pdf", pdf_data)

            zip_key = f"jobs/{job_id}/YBT_{job.container_num}.zip"
            zip_url = upload_file(zip_path, zip_key)

            job.zip_url = zip_url
            job.status  = JobStatus.DONE
            db.commit()

    except Exception as exc:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error  = str(exc)
            db.commit()
        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()
