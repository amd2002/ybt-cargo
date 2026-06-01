# YBT Cargo Manager

Application web de génération automatique de factures cargo.

## Stack
- **Backend** : FastAPI + Python
- **Queue** : Celery + Redis
- **DB** : PostgreSQL
- **Stockage** : Cloudflare R2
- **Hébergement** : Railway

---

## Déploiement sur Railway (étape par étape)

### 1. Préparer GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/TON_USERNAME/ybt-cargo.git
git push -u origin main
```

### 2. Créer le projet Railway

1. Aller sur [railway.app](https://railway.app) → **New Project**
2. Choisir **Deploy from GitHub repo** → sélectionner `ybt-cargo`
3. Railway détecte le Dockerfile automatiquement

### 3. Ajouter les services Railway

Dans le projet Railway, cliquer **+ New** et ajouter :
- **PostgreSQL** (plugin Railway)
- **Redis** (plugin Railway)

Railway génère automatiquement les variables `DATABASE_URL` et `REDIS_URL`.

### 4. Configurer les variables d'environnement

Dans Railway → Variables, ajouter :

```
SECRET_KEY=une-cle-secrete-aleatoire-longue
R2_ACCOUNT_ID=votre-account-id-cloudflare
R2_ACCESS_KEY_ID=votre-access-key
R2_SECRET_ACCESS_KEY=votre-secret-key
R2_BUCKET_NAME=ybt-cargo-pdfs
R2_PUBLIC_URL=https://votre-bucket.r2.dev
```

### 5. Configurer Cloudflare R2

1. Aller sur [dash.cloudflare.com](https://dash.cloudflare.com) → R2
2. Créer un bucket `ybt-cargo-pdfs`
3. Dans **Settings** → activer **Public access**
4. Créer un **API Token** avec permissions R2 Read + Write
5. Copier Account ID, Access Key, Secret Key

### 6. Ajouter le worker Celery

Dans Railway → **+ New Service** → **Dockerfile** → même repo
- Dans les settings du service worker, changer la commande :
  ```
  celery -A app.workers.tasks.celery_app worker --loglevel=info --concurrency=2
  ```

### 7. Initialiser la base de données

Dans Railway → votre service web → **Shell** :
```bash
python scripts/init_db.py
```

### 8. Ajouter le logo YBT

Mettre le fichier `ybt_logo.jpg` dans le dossier `assets/` et redéployer.

---

## Utilisation

1. Ouvrir l'URL Railway du projet
2. Login : `admin` / `ybt2024!` (changer après premier login)
3. Renseigner le n° conteneur, date, ETA
4. Uploader le fichier Excel
5. Corriger les clients si nécessaire
6. Cliquer **Générer les PDFs**
7. Télécharger le ZIP

---

## Modifier les tarifs

- Dans l'interface : cliquer **⚙ Tarifs** en haut à droite
- Les nouveaux tarifs s'appliquent immédiatement aux prochains uploads

---

## Ajouter un utilisateur

Dans le shell Railway :
```python
from scripts.init_db import *
db = SessionLocal()
user = User(username="ibrahim", hashed_pw=pwd_ctx.hash("motdepasse"), is_admin=False)
db.add(user); db.commit()
```
