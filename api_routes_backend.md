# Routes API Backend — Scoring LBC/FT (RiskGuard)

**Framework :** FastAPI (Python 3.11+)  
**Base URL :** `http://localhost:8000`  
**Auth :** JWT (Bearer token) — sauf `GET /`  
**Docs auto :** `/docs` (Swagger) | `/redoc` (ReDoc)

---

## Santé

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| GET | `/` | `backend/app/main.py` | 68 | Health check |

---

## Authentification

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| POST | `/auth/login` | `routers/auth.py` | 14 | Login → JWT (8h) |
| GET | `/auth/me` | `routers/auth.py` | 51 | Infos utilisateur courant |

---

## Clients (Customers)

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| GET | `/api/clients` | `routers/customers.py` | 23 | Liste paginée/filtrée des clients |
| GET | `/api/clients/{customer_id}` | `routers/customers.py` | 67 | Détail complet d'un client |
| POST | `/api/clients` | `routers/customers.py` | 98 | Créer un nouveau client |
| PUT | `/api/clients/{customer_id}` | `routers/customers.py` | 145 | Modifier un client |

---

## Alertes

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| GET | `/api/alerts` | `routers/alerts.py` | 16 | Liste paginée/filtrée des alertes |
| GET | `/api/alerts/{alert_id}` | `routers/alerts.py` | 45 | Détail d'une alerte |
| GET | `/api/customers/{customer_id}/alerts` | `routers/alerts.py` | 61 | Alertes d'un client |
| POST | `/api/alerts` | `routers/alerts.py` | 78 | Créer une alerte manuelle |
| PUT | `/api/alerts/{alert_id}` | `routers/alerts.py` | 95 | Mettre à jour une alerte |

---

## Dashboard

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| GET | `/api/dashboard/stats` | `routers/dashboard.py` | 17 | KPIs globaux |
| GET | `/api/dashboard/alerts` | `routers/dashboard.py` | 64 | 5 dernières alertes ouvertes |
| GET | `/api/dashboard/pep` | `routers/dashboard.py` | 90 | Clients marqués PEP |

---

## Administration

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| GET | `/api/admin/scoring-criteria` | `routers/admin.py` | 26 | Liste des critères de score |
| PUT | `/api/admin/scoring-criteria/{criteria_id}` | `routers/admin.py` | 45 | Modifier poids d'un critère |
| GET | `/api/admin/risk-thresholds` | `routers/admin.py` | 85 | Seuils de risque |
| GET | `/api/admin/users` | `routers/admin.py` | 106 | Liste des utilisateurs |
| PUT | `/api/admin/users/{user_id}/toggle-active` | `routers/admin.py` | 125 | Activer/désactiver un utilisateur |
| POST | `/api/admin/users` | `routers/admin.py` | 253 | Créer un compte agent |
| POST | `/api/admin/pep-list/import` | `routers/admin.py` | 150 | Importer liste PEP (CSV) |
| GET | `/api/admin/audit-logs` | `routers/admin.py` | 210 | Journal d'audit filtré |

---

## Comptes bancaires

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| GET | `/api/customers/{customer_id}/accounts` | `routers/customer_accounts.py` | 14 | Comptes d'un client |
| GET | `/api/accounts/{account_id}` | `routers/customer_accounts.py` | 30 | Détail d'un compte |

---

## Documents KYC

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| GET | `/api/customers/{customer_id}/documents` | `routers/customer_docs.py` | 13 | Documents KYC d'un client |
| GET | `/api/documents/{doc_id}` | `routers/customer_docs.py` | 29 | Détail d'un document |

---

## Transactions

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| GET | `/api/customers/{customer_id}/transactions` | `routers/transactions.py` | 17 | Transactions d'un client (fenêtre temporelle) |
| GET | `/api/transactions/{transaction_id}` | `routers/transactions.py` | 49 | Détail d'une transaction |

---

## PEP

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| GET | `/api/pep` | `routers/pep.py` | 13 | Liste PEP (filtrable) |

---

## Scoring

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| POST | `/api/scoring` | `routers/scoring.py` | 261 | Calcul score initial LBC/FT (C1–C6) |
| POST | `/api/scoring/rescore` | `routers/scoring.py` | 307 | Re-score manuel |
| GET | `/api/scores/{score_id}` | `routers/scoring.py` | 352 | Détail d'un score |
| GET | `/api/customers/{customer_id}/scores` | `routers/scoring.py` | 387 | Historique des scores d'un client |

---

## Exports

| Méthode | Route | Fichier | Ligne | Description |
|---------|-------|---------|-------|-------------|
| GET | `/api/exports/customer/{customer_id}/pdf` | `routers/exports.py` | 75 | Export fiche client PDF |
| GET | `/api/exports/transactions/{customer_id}/csv` | `routers/exports.py` | 153 | Export transactions CSV |
| GET | `/api/exports/sar/{alert_id}/pdf` | `routers/exports.py` | 238 | Rapport SAR PDF (CENTIF Bénin) |

---

**Total : 37 routes** — 24 GET, 8 POST, 5 PUT
