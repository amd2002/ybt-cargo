# YBT Cargo Manager

Application web de génération automatique de factures cargo pour YBT International Ocean Freight & Logistic.

## Ce que fait l'application

- Upload d'un fichier Excel YBT → analyse automatique des clients
- Regroupement des clients par numéro de téléphone (fusion des doublons)
- Détection automatique de la destination : Sierra Leone (SL) ou Guinée (GN)
- Double tarif : SL = $280/CBM · GN = $340/CBM (modifiable depuis l'interface)
- Calcul exact sans arrondi : Freight = (CBM × tarif) ÷ 2 · Custom = (CBM × tarif) ÷ 2
- Édition manuelle des clients avant génération
- Génération PDF des factures avec logo YBT
- Téléchargement ZIP de toutes les factures
- Liste terrain PDF pour les agents (colonnes statut/signature)
- Historique des conteneurs avec détails et suppression (PIN)

## Stack technique

- **Backend** : FastAPI + Python 3.11
- **Base de données** : PostgreSQL (Supabase)
- **Génération PDF** : ReportLab
- **Frontend** : HTML/CSS/JS vanilla
- **Hébergement** : Local (Windows)

## Installation sur Windows

### Prérequis
- Python 3.11
- Git

### Étapes

```bash
git clone https://github.com/amd2002/ybt-cargo.git
cd ybt-cargo

py -3.11 -m venv venv
venv\Scripts\activate

pip install fastapi==0.111.0 uvicorn[standard]==0.29.0 sqlalchemy==2.0.30 alembic==1.13.1 python-multipart==0.0.9 pandas==2.2.2 xlrd==2.0.1 openpyxl==3.1.2 python-docx==1.1.2 jinja2==3.1.4 pydantic==2.7.1 pydantic-settings==2.2.1 python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4 httpx==0.27.0 boto3==1.34.110 psycopg2-binary celery==5.3.6 redis==5.0.4 reportlab pillow bcrypt==4.0.1
```

### Configuration

Créer un fichier `.env` dans le dossier `ybt-app` :

```
DATABASE_URL=postgresql://postgres.XXXX:MOTDEPASSE@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres
SECRET_KEY=ybt-cargo-secret-2024-xK9m
RATE_SIERRA_LEONE=280
RATE_GUINEE=340
REDIS_URL=redis://localhost:6379/0
```

### Initialisation base de données

```bash
python scripts/init_db.py
```

### Lancement

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Ou double-clic sur `C:\ybt-cargo\start_ybt.bat`

Accès : **http://localhost:8000**

Accès réseau local : **http://172.20.10.2:8000**

## Utilisation

1. Ouvrir http://localhost:8000
2. Renseigner le n° conteneur, date chargement, ETA
3. Uploader le fichier Excel YBT
4. Corriger les clients si nécessaire (CBM, destination, nom)
5. Cliquer **Générer les PDFs**
6. Télécharger le ZIP des factures
7. Télécharger la liste terrain pour les agents

## Modifier les tarifs

Cliquer **⚙ Tarifs** en haut à droite de l'interface.

## PIN de suppression

Le PIN par défaut est `1234`. Pour le changer, modifier la ligne 4 de `frontend/static/js/app.js` :
```javascript
const DELETE_PIN = "1234";
```

## Structure du projet

```
ybt-app/
├── app/
│   ├── api/          → routes FastAPI
│   ├── core/         → config, base de données
│   ├── models/       → tables PostgreSQL
│   └── services/     → parser Excel, générateur PDF, résumé terrain
├── frontend/         → interface web (HTML/CSS/JS)
├── scripts/          → initialisation base de données
├── assets/           → logo YBT
└── start_ybt.bat     → lancement rapide Windows
```