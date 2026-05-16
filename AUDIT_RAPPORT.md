# Audit du projet Scoring LBC/FT (RiskGuard)

**Date :** 16 mai 2026
**Statut du projet :** ~5% de complétion
**Stack :** FastAPI + PostgreSQL (backend), React + Vite + Tailwind (frontend)

---

## Résumé exécutif

27 problèmes identifiés (dont 5 critiques bloquants, 5 haute sévérité, 5 moyens, 8 de qualité).

---

## 🔴 CRITIQUE — Plante au runtime

### 1. Export services utilisent des noms de colonnes erronés

**Fichiers :** `backend/app/services/export_service.py`, `backend/tests/integration/test_exports.py`

Le modèle `Alert` utilise des colonnes en français :
| Colonne réelle | Utilisé dans le code (erroné) |
|---|---|
| `Alert.client_id` | `Alert.customer_id` |
| `Alert.type_alerte` | `alert_type` |
| `Alert.statut` | `status` |
| `Alert.date_creation` | `created_at` |
| `Alert.sar_declare` | `sar_filed` |

**Impact :** `AttributeError` au premier appel des exports PDF/SAR.

---

### 2. Conflit de migrations Alembic (multiple heads)

**Fichiers :**
- `backend/alembic/versions/8916d3c8118e_feat_initial_schema_10_tables.py` — `down_revision = None`
- `backend/alembic/versions/7efd7d148c8d_initial_schema_14_tables.py` — `down_revision = None`

Les deux migrations ont `down_revision = None`, créant deux têtes de migration. `alembic upgrade head` échoue avec *"Multiple head revisions"*.

---

### 3. Dockerfile vide

**Fichier :** `Dockerfile` (0 bytes)

`docker-compose.yml` référence ce Dockerfile pour builder le backend, mais il est vide. Impossible de conteneuriser l'application.

---

### 4. Frontend entier vide

**38 fichiers** dans `frontend/src/` (composants, pages, services, hooks, contextes, utils, thèmes) sont tous à **0 bytes**. `vite.config.js` et `tailwind.config.js` également vides.

Aucune interface utilisateur n'existe.

---

### 5. Tests créent des objets User avec des champs inexistants

**Fichiers :** `backend/tests/integration/test_exports.py`, `backend/tests/integration/test_scoring_endpoints.py`

```python
# Code actuel (erroné)
User(full_name=..., email=..., hashed_password=..., role="admin")

# Ce qui existe dans le modèle
# User(login=..., password_hash=..., role_id=<int>, is_active=...)
```

`AttributeError` au lancement des tests.

---

## 🟠 HIGH — Sévère mais contournable

### 6. Audit service fait un commit en milieu de transaction

**Fichier :** `backend/app/services/audit_service.py:36`

```python
def log_action(db, user_id, action, ...):
    log = AuditLog(...)
    db.add(log)
    db.commit()  # <-- DANGEREUX
```

Appelé depuis `scoring.py` et `customers.py` qui font aussi un `commit()` après. Si l'opération principale échoue après `log_action`, l'audit log est commité mais l'opération principale est rollbackée → état inconsistant.

---

### 7. PEP matching exact (pas de fuzzy search)

**Fichier :** `backend/app/services/scoring.py:499-507`

```python
.filter(
    PepEntry.nom.ilike(customer.nom),       # exact
    PepEntry.prenom.ilike(customer.prenom),  # exact
    PepEntry.active == True
)
```

Une recherche exacte sur nom ET prénom rate toutes les variantes (accents, noms composés, fautes d'orthographe). Devrait utiliser `contains()` ou `ilike(f"%{value}%")`.

---

### 8. Aucune gestion d'erreur si le scoring plante après création client

**Fichier :** `backend/app/routers/customers.py:132-139`

```python
try:
    engine = ScoringEngine(db)
    engine.calculate_score(str(customer.id), scored_by="AUTOMATED")
except Exception as e:
    print(f"[WARNING] Scoring error for {customer.id}: {e}")
```

Si le scoring échoue après le `db.commit()` de la création (ligne 128), le client est créé sans score → dashboard cassé, alertes non générées.

---

### 9. Secrets hardcodés

| Fichier | Secret |
|---|---|
| `backend/app/config.py` | `DATABASE_URL` avec credentials dev, `SECRET_KEY` hardcodée |
| `docker-compose.yml` | `POSTGRES_PASSWORD: dev_password_change_in_prod` |
| `backend/scripts/seed_db.py` | Mot de passe admin : `admin1234` |

---

### 10. Poids de scoring incohérents

- **`seed_db.py`** : poids en pourcentages (`weight=20.00`, `weight=25.00`, somme = 100)
- **`test_scoring.py`** : poids en fractions (`weight=Decimal("0.20")`, somme = 1.0)
- **`test_scoring_endpoints.py`** : poids en fractions

Bien que `_load_weights()` normalise, les scores diffèrent entre dev et tests.

---

## 🟡 MEDIUM

### 11. `compute_kyc_completion()` sans eager load

**Fichier :** `backend/app/services/customer_service.py:29-31`

```python
if customer.documents:
    valid_docs = [d for d in customer.documents if d.valide]
```

Si `customer.documents` n'est pas eager-loaded et que la session est fermée → `DetachedInstanceError`. L'appelant (`customers.py`) ne fait pas de `joinedload`.

---

### 12. Pas de rate limiting sur `/auth/login`

**Fichier :** `backend/app/routers/auth.py`

Aucune protection contre les attaques brute-force : pas de rate limiting, pas de CAPTCHA, pas de lockout.

---

### 13. JWT incomplet

**Fichier :** `backend/app/auth/security.py:20-25`

```python
payload = data.copy()
payload["exp"] = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
```

Seulement `exp` est défini. Manque : `iat`, `jti`, `nbf`. Pas de mécanisme de refresh token.

---

### 14. Précision flottante dans la détection de smurfing

**Fichier :** `backend/app/services/scoring.py:383`

```python
float(tx.montant) % _SMURFING_ROUND_STEP == 0
```

`float` modulo sur des montants financiers peut donner des faux négatifs à cause de l'arithmétique flottante. Devrait utiliser `int()` ou `Decimal`.

---

### 15. C1 scoring : profession vide + revenu nul = pas de pénalité

**Fichier :** `backend/app/services/scoring.py:211-222`

```python
if rev == 0 and risk not in ("HIGH", ""):
    note = min(100.0, note + 10.0)
```

Quand `risk = ""` et `rev = 0`, la condition est fausse → pas de pénalité. Un client sans profession déclarée ET sans revenu devrait avoir le score C1 maximum.

---

## 🔵 LOW — Qualité de code

### 16. Fichiers dupliqués / morts

- `backend/app/models/base.py` — vide (0 bytes)
- `backend/app/database.py` — vide (0 bytes, redondant avec `db/session.py`)

### 17. Mix français/anglais dans les statuts

| Modèle | Valeurs |
|---|---|
| `Customer.status` | `ACTIVE`, `INACTIVE`, `SUSPENDED` (EN) |
| `CustomerAccount.status` | `ACTIF`, `Bloqué` (FR) |
| `Transaction.type_op` | `DEPOT`, `RETRAIT`, `VIREMENT` (FR) |
| `Alert.statut` | `OPEN`, `UNDER_REVIEW`, `CLOSED` (EN) |

### 18. `datetime.utcnow()` déprécié (Python 3.12+)

**Fichier :** `backend/app/services/scoring.py`, `backend/scripts/generate_fake_data.py`

Remplacer par `datetime.now(timezone.utc)`.

### 19. Import tardif dans les tests

**Fichier :** `backend/tests/integration/test_scoring_endpoints.py:257`

```python
from app.models.transactions import Transaction as Transaction_
```

Importé après la fonction qui l'utilise (ligne 241).

### 20. `_pick_country_for_zone()` : Benin compté deux fois

**Fichier :** `backend/scripts/generate_fake_data.py:772`

```python
return random.choice([ref.bj] * 7 + list(ref.pays.values()))
```

`ref.pays.values()` contient déjà `ref.bj`. Donc Benin apparaît ~8×, autres pays 1× → ~90% Benin au lieu des ~70% attendus.

### 21. `__init__.py` vides

Tous les dossiers (`routers/`, `schemas/`, `services/`, `auth/`, `utils/`, `middleware/`) ont des `__init__.py` vides. Ajouter un nouveau router nécessite de modifier `main.py`.

### 22. Pas de `.env.example` frontend

`frontend/.env.example` est vide (0 bytes). Aucune documentation sur les vars d'env nécessaires.

### 23. `test_scenario.py` sans gestion d'erreur DB

**Fichier :** `backend/test_scenario.py`

Utilise `SessionLocal()` directement sans fallback si la base est injoignable.

### 24-27. Autres fichiers vides (tests, docs)

| Fichier | Problème |
|---|---|
| `docs/API_CONTRACT.md` | Vide |
| `docs/DATABASE.md` | Vide |
| `docs/SCORING_LOGIC.md` | Vide |
| `docs/TROUBLESHOOTING.md` | Vide |
| `backend/scripts/create_admin.py` | Vide |
| `backend/app/services/pep_service.py` | Vide |
| `backend/tests/conftest.py` | Vide |
| `backend/tests/unit/test_services.py` | Vide |
| `backend/tests/unit/test_auth.py` | Vide |
| `backend/tests/unit/test_models.py` | Vide |
| `backend/tests/integration/test_database.py` | Vide |
| `backend/tests/integration/test_endpoints.py` | Vide |
| `backend/tests/integration/test_workflow.py` | Vide |
| `PLAN_ACTION_COMPLET.md` | Vide |

---

## Statistiques

| Sévérité | Catégorie | Nombre |
|---|---|---|
| 🔴 Critique | Bugs bloquants | 5 |
| 🟠 Haute | Sécurité / Logique / Erreurs | 5 |
| 🟡 Moyenne | Logique / Manque de gestion d'erreur | 5 |
| 🔵 Basse | Qualité de code / Docs vides | 12 |

**Total : 27 problèmes identifiés**
