# 📊 Module de Scoring LBC/FT

Système de scoring automatisé pour la lutte contre le blanchiment de capitaux et le financement du terrorisme dans les Institutions de Microfinance (IMF) béninoises.

**Stack technologique :**
- Backend : Python 3.11 + FastAPI + PostgreSQL
- Frontend : React 18 + Vite + Tailwind CSS
- Base de données : 14 tables PostgreSQL + Alembic migrations
- Déploiement : Render (backend) + Neon (DB) + Vercel (frontend)

**Binôme :** AFFOKPE Magloire (Dev A) & BATAMOUSSI Marcos (Dev B)  
**Encadrant :** Mr ASSOGBA Emery  
**Durée :** 12 semaines (Licenc Pro IUT Parakou 2024-2025)

## 📚 Documentation

- [Setup Local](./docs/SETUP.md) — Comment configurer l'environnement
- [API Contract](./docs/API_CONTRACT.md) — Spécifications API REST
- [Déploiement](./docs/DEPLOYMENT.md) — Docker & production
- [Documentation complète](./docs/RAPPORT_COMPLET.md) — Rapport détaillé du projet

## ⚡ Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## 📝 License

Projet académique — Université de Parakou, 2025

<!-- nouveau-pc:debut -->
## Installer sur un nouveau PC

**Prérequis :** Git et Docker avec Compose. Sans Docker : Python 3.12, Node.js 20 ou plus et PostgreSQL.

```bash
git clone git@github.com:Magloireaffokpe/MoteurScoring_LB-FT.git scoring-lbc-ft
cd scoring-lbc-ft
git switch develop           # branche de travail
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build    # API : http://localhost:8000 · interface : http://localhost:5173

# Dans un autre terminal, à la première installation :
docker compose exec backend alembic upgrade head
```

**Sans Docker :**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows : venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Dans un autre terminal
cd frontend && npm install && npm run dev
```

**À recopier à la main (hors Git) :** `backend/.env` (réglages `SEUIL_*`, `FENETRE_CUMUL_JOURS`, `BENEFICIAIRE_MIN_*` en plus de ceux de l'exemple) et `frontend/.env`.
<!-- nouveau-pc:fin -->
