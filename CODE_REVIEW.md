# Code Review Report: Scoring LBC-FT

## Projet
Système de scoring AML/CFT (Anti-Money Laundering / Counter Financing of Terrorism) pour les institutions de microfinance au Bénin.

**Stack**: FastAPI + PostgreSQL (backend), React + Vite + Tailwind (frontend)

**Statut**: Early development - ~5% de completion

---

## 🔴 CRITIQUE

### 1. Tout le code applicatif est vide (stubs)

**Impact**: Le projet ne peut pas fonctionner.

#### Backend - Routers (tous à 0 octets)
| Fichier | Status |
|---------|--------|
| `backend/app/routers/scoring.py` | 0 bytes |
| `backend/app/routers/customers.py` | 0 bytes |
| `backend/app/routers/alerts.py` | 0 bytes |
| `backend/app/routers/transactions.py` | 0 bytes |
| `backend/app/routers/dashboard.py` | 0 bytes |
| `backend/app/routers/admin.py` | 0 bytes |
| `backend/app/routers/customer_accounts.py` | 0 bytes |
| `backend/app/routers/customer_docs.py` | 0 bytes |
| `backend/app/routers/exports.py` | 0 bytes |
| `backend/app/routers/pep.py` | 0 bytes |

#### Backend - Services (tous à 0 octets)
| Fichier | Status |
|---------|--------|
| `backend/app/services/scoring.py` | 0 bytes |
| `backend/app/services/customer_service.py` | 0 bytes |
| `backend/app/services/alert_service.py` | 0 bytes |
| `backend/app/services/export_service.py` | 0 bytes |
| `backend/app/services/pep_service.py` | 0 bytes |

#### Backend - Schemas (vides)
- `backend/app/schemas/score.py`
- `backend/app/schemas/transaction.py`

#### Backend - Utils (vides)
- `backend/app/utils/validators.py`
- `backend/app/utils/constants.py`
- `backend/app/utils/detail_json.py`

#### Backend - Middleware (vides)
- `backend/app/middleware/error_handlers.py`
- `backend/app/middleware/logging.py`

#### Frontend - Tous les fichiers source (0 octets)
- App.jsx, main.jsx
- Tous les services (auth, customer, scoring, alert, dashboard, export, api)
- Tous les hooks (useAuth, useFetch, usePagination, useForm)
- Tous les composants (Layout, Button, Card, Table, FormInput, Badge, Loader, Modal)
- Toutes les pages (LoginPage, DashboardPage, ClientsListPage, ClientDetailPage, ScorePage, AlertsPage, ExportsPage, AdminPage)
- Tous les contexts (AuthContext, AppContext)
- Tous les fichiers theme (colors, typography, spacing)
- Tous les utilitaires (helpers, formatters, validators, constants)
- App.css, vite.config.js, tailwind.config.js

#### Tests (tous à 0 octets)
- `tests/unit/test_scoring.py`
- `tests/unit/test_services.py`
- `tests/unit/test_auth.py`
- `tests/unit/test_models.py`
- `tests/conftest.py`
- `tests/integration/test_endpoints.py`
- `tests/integration/test_database.py`
- `tests/integration/test_workflow.py`

---

### 2. Secrets hardcodés

**Fichier**: `backend/app/config.py`
```python
DATABASE_URL: str = "postgresql://marcos:dev_password_change_in_prod@localhost:5433/scoring_db"
SECRET_KEY: str = "dev_secret_key_change_in_production"
```

**Fichier**: `docker-compose.yml`
```yaml
POSTGRES_PASSWORD: dev_password_change_in_prod
SECRET_KEY: dev_secret_key_change_in_production
```

**Fichier**: `backend/scripts/seed_db.py`
```python
admin = User(
    login="admin",
    password_hash=pwd_context.hash("admin1234"),
    ...
)
```

---

## 🟠 HAUT

### 3. Schéma Score manquant
**Fichier**: `backend/app/schemas/score.py` - 0 bytes

Le modèle `Score` existe mais aucun schéma Pydantic pour la validation API request/response.

### 4. Schéma Transaction manquant
**Fichier**: `backend/app/schemas/transaction.py` - 0 bytes

### 5. Middleware d'erreur incomplet
**Fichier**: `backend/app/middleware/error_handlers.py` - 0 bytes

Pas de gestion globale des erreurs:
- Réponses incohérentes
- Risque de fuite d'information via stack traces
- Pas de format standardisé

### 6. Middleware de logging incomplet
**Fichier**: `backend/app/middleware/logging.py` - 0 bytes

### 7. Pas de validation d'input
**Fichier**: `backend/app/utils/validators.py` - 0 bytes

### 8. Audit log sans rollback
**Fichier**: `backend/app/services/audit_service.py`
```python
def log_action(db, user_id, action, client_id=None, ip="0.0.0.0"):
    log = AuditLog(...)
    db.add(log)
    db.commit()  # Si commit échoue, pas de gestion d'erreur
```

### 9. Pas de pool de connexion configuré
**Fichier**: `backend/app/db/session.py`
```python
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)
```

Pool par défaut de 5 peut être insuffisant.

### 10. Pas de refresh token
Seuls les access tokens existent. Pas de mécanisme pour sessions longue durée.

---

## 🟡 MOYEN

### 11. DEBUG=True par défaut
**Fichier**: `backend/app/config.py`
```python
DEBUG: bool = True
```

### 12. Incohérence de langue dans les status
**Fichier**: `backend/app/models/customers.py`
```python
status = Column(String(20), default="ACTIVE", ...)  # 'ACTIVE', 'INACTIVE', 'SUSPENDED'
```

**Fichier**: `backend/app/models/customer_accounts.py`
```python
status = Column(String(50), default="ACTIF", ...)   # 'ACTIF', 'Bloqué'
```

Clients: anglais, Comtes: français.

### 13. Location stockée en String
**Fichier**: `backend/app/models/customers.py`
```python
latitude = Column(String(20), nullable=True)
longitude = Column(String(20), nullable=True)
```
Devrait être `Numeric` pour calculs géographiques.

### 14. VITE_API_URL pointe sur localhost
**Fichier**: `docker-compose.yml`
```yaml
VITE_API_URL: http://localhost:8000
```
Dans le réseau Docker, devrait être `http://backend:8000`.

### 15. Pas de rate limiting sur /auth/login
Risque d'attaque brute-force.

### 16. Pas de pagination
`PaginatedResponse` existe mais pas d'implémentation.

### 17. Champs nullable qui ne devraient pas l'être
- `Customer.profession_code`
- `Transaction.type_op`
- `Transaction.canal`

### 18. Colonne `active` PEP non indexée
**Fichier**: `backend/app/models/pep_list.py`

---

## 🟢 BAS

### 19. Documentation vide
- `docs/TROUBLESHOOTING.md`
- `docs/SCORING_LOGIC.md`
- `docs/API_CONTRACT.md`
- `.github/workflows/ci.yml`
- `Dockerfile`

### 20. Tests vides
Tous les tests backend et frontend sont à 0 octets.

### 21. Pas de .env.example frontend

### 22. Imports SQLAlchemy incohérents
```python
# Variante 1
from sqlalchemy.orm import relationship
# Variante 2
import sqlalchemy as sa
```

### 23. Pas de newline en fin de fichier
**Fichier**: `backend/app/routers/auth.py`

---

## Checklist des fonctionnalités manquantes

### Backend
- [ ] Endpoints Customer CRUD
- [ ] Gestion des alerts
- [ ] Listing/filtrage transactions
- [ ] Statistiques dashboard
- [ ] Logique de calcul scoring
- [ ] Matching/screening PEP
- [ ] Export (PDF/Excel)
- [ ] Gestion utilisateurs admin
- [ ] Gestion documents client
- [ ] Gestion comptes client

### Frontend
- [ ] Toutes les pages
- [ ] Tous les composants
- [ ] Couche service API
- [ ] Auth context/hooks
- [ ] Gestion formulaires
- [ ] Hooks data fetching
- [ ] Styles (CSS, Tailwind)

### Tests
- [ ] Tests unitaires backend
- [ ] Tests intégration backend
- [ ] Tests composants frontend
- [ ] Tests intégration frontend

---

## Résumé

| Severity | Count |
|----------|-------|
| CRITIQUE | 3 |
| HAUT | 8 |
| MOYEN | 10 |
| BAS | 7 |

**Total: ~28 problèmes identifiés**

Le projet est à ~5% de completion. Seuls fonctionnent : auth, models de base, audit, et seed data.
