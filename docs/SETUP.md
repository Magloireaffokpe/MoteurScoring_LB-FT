# 🛠️ Setup Local — Guide d'installation

## Prérequis

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Docker & Docker Compose (optionnel mais recommandé)
- Git 2.30+

## Backend Setup

```bash
cd backend

# Créer virtual env
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements.txt

# Setup .env
cp .env.example .env
# Éditer .env avec tes credentials

# Migrations BD
alembic upgrade head

# Démarrer serveur
python main.py
# → http://localhost:8000
# → Swagger: http://localhost:8000/docs
```

## Frontend Setup

```bash
cd frontend

# Installer dépendances
npm install

# Setup .env (si nécessaire)
cp .env.example .env

# Dev server
npm run dev
# → http://localhost:5173
```

## Docker Compose (Recommandé)

```bash
# Root du repo
docker-compose up -d

# Vérifier
docker-compose logs -f

# Arrêter
docker-compose down
```

## Premiers tests

```bash
# Tests backend
cd backend
pytest tests/ -v

# Tests frontend
cd frontend
npm run test
```
