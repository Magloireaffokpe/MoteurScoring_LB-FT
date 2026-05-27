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
