"""
Script d'initialisation : crée les tables et le premier utilisateur admin.
Usage : python scripts/init_db.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import Base, engine, SessionLocal
from app.models.models import User, Tariff
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init():
    print("Création des tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Tarifs par défaut
    for dest, rate in [("SL", 280.0), ("GN", 340.0)]:
        if not db.query(Tariff).filter(Tariff.destination == dest).first():
            db.add(Tariff(destination=dest, rate=rate))
            print(f"  Tarif {dest} = ${rate}/CBM créé")

    # Utilisateur admin par défaut
    if not db.query(User).filter(User.username == "admin").first():
        admin = User(
            username="admin",
            hashed_pw=pwd_ctx.hash("ybt2024!"),
            is_admin=True,
        )
        db.add(admin)
        print("  Utilisateur admin créé (mot de passe: ybt2024!)")
        print("  ⚠️  Changez le mot de passe après le premier login !")

    db.commit()
    db.close()
    print("✓ Initialisation terminée.")

if __name__ == "__main__":
    init()
