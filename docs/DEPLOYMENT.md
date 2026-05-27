# Déploiement — RiskGuard (Scoring LBC/FT)

**Stack production :** Render (backend) · Neon (PostgreSQL) · Vercel (frontend)

---

## 1. Base de données — Neon

1. Créer un compte sur [neon.tech](https://neon.tech)
2. Créer un projet → récupérer l'URI de connexion :
   ```
   postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
3. **Important** : Neon Free tier limite à 5 connexions simultanées. Les `pool_size=5` par défaut dans le code sont adaptés.
4. Exécuter les migrations et seed en local avant de déployer, ou via un script Render :

   ```bash
   # Appliquer les migrations
   DATABASE_URL="<neon-uri>" alembic upgrade head

   # Seed des références
   DATABASE_URL="<neon-uri>" python scripts/seed_db.py

   # (Optionnel) Données factices
   DATABASE_URL="<neon-uri>" python scripts/generate_fake_data.py
   ```

> **Astuce** : Utilisez `psql "$DATABASE_URL" -f scripts/seed.sql` si vous avez un dump SQL.

---

## 2. Backend — Render

### Service Web

1. **Créer** un **Web Service** → connecter le dépôt GitHub
2. **Settings** :
   - **Runtime** : Python 3.11
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `alembic upgrade head && gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120 --access-logfile - --error-logfile -`
   - **Health Check Path** : `/`

3. **Environment Variables** (obligatoires) :

| Variable | Valeur |
|----------|--------|
| `DATABASE_URL` | URI Neon |
| `SECRET_KEY` | `openssl rand -hex 32` |
| `DEBUG` | `false` |
| `CORS_ORIGINS` | `https://moteur-scoring-lb-ft.vercel.app` |
| `DATABASE_POOL_SIZE` | `5` |
| `DATABASE_MAX_OVERFLOW` | `5` |

4. **Render Cron Jobs (optionnel)** pour le rescore automatique :
   - Schedule : `0 2 * * *`
   - Command : `curl -X POST https://moteurscoring-lb-ft.onrender.com/api/scoring/rescore -H "Authorization: Bearer <admin-token>"`

### Fichier `Procfile` (déjà créé)
```
web: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120
```

> **Note** : Si vous utilisez le plan gratuit Render, réduisez `-w 2` (workers) pour consommer moins de RAM.

---

## 3. Frontend — Vercel

1. **Créer** un projet Vercel → connecter le dépôt (dossier `frontend/`)
2. **Settings** (automatiques depuis `vercel.json`) :
   - **Framework Preset** : Vite
   - **Build Command** : `npm run build`
   - **Output Directory** : `dist`
3. **Environment Variable** :
   - `VITE_API_URL` → `https://moteurscoring-lb-ft.onrender.com`
4. Le fichier `vercel.json` gère déjà le routing SPA et le cache des assets.

---

## 4. Checklist pré-déploiement

- [ ] `SECRET_KEY` générée et unique
- [ ] `DEBUG=false` (le code le refuse avec une base distante)
- [ ] `CORS_ORIGINS` pointe vers le vrai domaine Vercel
- [ ] Migrations appliquées sur Neon
- [ ] Seed exécuté sur Neon
- [ ] `DATABASE_POOL_SIZE=5` (max 5 pour Neon Free)
- [ ] Frontend build sans erreur : `npm run build`
- [ ] Test de bout en bout : login → dashboard → clients → scoring

---

## 5. Commandes utiles

```bash
# Migration
alembic revision --autogenerate -m "description"
alembic upgrade head

# Backup / Restore Neon
pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d).sql
psql "$DATABASE_URL" < backup_20260101.sql

# Logs Render (via CLI)
render logs --service riskguard-backend --tail
```

---

## Annexes

### Déploiement local (sans Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # configurer DATABASE_URL, SECRET_KEY
alembic upgrade head
python scripts/seed_db.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (autre terminal)
cd frontend
npm install
cp .env.example .env   # configurer VITE_API_URL=http://localhost:8000
npm run dev
```

### Variables d'environnement complètes

| Variable | Backend/Frontend | Obligatoire | Défaut |
|----------|-----------------|-------------|--------|
| `DATABASE_URL` | Backend | Oui | — |
| `SECRET_KEY` | Backend | Oui | — |
| `DEBUG` | Backend | Non | `false` |
| `CORS_ORIGINS` | Backend | Non | origines locales |
| `DATABASE_POOL_SIZE` | Backend | Non | `5` |
| `DATABASE_MAX_OVERFLOW` | Backend | Non | `5` |
| `VITE_API_URL` | Frontend | Oui | `http://localhost:8000` |
