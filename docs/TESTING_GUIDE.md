# 🧪 Guide de test — Moteur de Scoring LBC/FT (RiskGuard)

> **Version** : 1.0 — Mai 2026

> Toutes les commandes se lancent depuis le dossier `backend/`

---

## Prérequis

```bash
# 1. Variables d'environnement
cp .env.example .env          # puis édite DATABASE_URL si besoin

# 2. Base de données en ligne
docker-compose up -d db       # ou ton service PostgreSQL

# 3. Migrations
alembic upgrade head

# 4. Données de référence (tables de Marcos)
python scripts/seed_db.py

# 5. Données de test (tables de Magloire)
python scripts/generate_fake_data.py
```

Résultat attendu du script :

```
════════════════════════════════════════════════════
📊  STATISTIQUES DES DONNÉES GÉNÉRÉES
════════════════════════════════════════════════════
   Clients          :    500
   Comptes          :    500
   Documents KYC    :    ~750
   Transactions     :  ~8000
   Clients PEP      :    ~10
   Entrées PEP list :    ~13
════════════════════════════════════════════════════
   Scénarios obligatoires :
     ✓ Amélie SOGLO     — id=...
     ✓ Koffi BIAOU      — id=...
     ✓ Fatima OUEDRAOGO — id=...
════════════════════════════════════════════════════
```

---

## Étape 1 — Vérification des imports

```bash
python -c "
from app.services.scoring import ScoringEngine
from app.routers.scoring import router
from app.schemas.score import ScoreResponse, ScoringRequest
print('✅ Tous les imports OK')
"
```

---

## Étape 2 — Vérification des données de référence

```bash
python -c "
from app.db.session import SessionLocal
from app.models.scoring_criteria import ScoringCriteria
from app.models.risk_thresholds import RiskThreshold
from app.models.countries import Country
from app.models.risk_zones import RiskZone

db = SessionLocal()
print('Critères     :', db.query(ScoringCriteria).count(), '(attendu 6)')
print('Seuils       :', db.query(RiskThreshold).count(),   '(attendu 3)')
print('Pays         :', db.query(Country).count(),         '(attendu 15)')
print('Zones risque :', db.query(RiskZone).count(),        '(attendu 6)')

# Vérification somme des poids = 100
total_poids = sum(float(c.weight) for c in db.query(ScoringCriteria).all())
print(f'Somme poids  : {total_poids}% (attendu 100.0)')
db.close()
"
```

---

## Étape 3 — Test du moteur (ligne de commande)

### 3a — Test rapide sur les 3 scénarios obligatoires

```bash
python -c "
from app.db.session import SessionLocal
from app.services.scoring import ScoringEngine
from app.models.customers import Customer

db = SessionLocal()
engine = ScoringEngine(db)

scenarios = [
    ('SOGLO',     'Amélie',  'FAIBLE',  '<34'),
    ('BIAOU',     'Koffi',   'MOYEN',   '34-66'),
    ('OUEDRAOGO', 'Fatima',  ÉLEVÉ',   '≥67'),
]

print()
print('═' * 60)
print('  TEST DES 3 SCÉNARIOS OBLIGATOIRES')
print('═' * 60)

for nom, prenom, cat_attendue, plage in scenarios:
    c = db.query(Customer).filter(
        Customer.nom == nom,
        Customer.prenom == prenom
    ).first()

    if not c:
        print(f'  ✗ {prenom} {nom} — INTROUVABLE !')
        continue

    result = engine.calculate_score(c.id)
    score  = result['global_score']
    cat    = result['risk_category']
    detail = result['detail_json']

    ok = '✅' if cat == cat_attendue else '❌'
    print(f'  {ok} {prenom} {nom}')
    print(f'     Score    : {score}/100  |  Catégorie : {cat}  (attendu : {cat_attendue})')
    print(f'     Détail   : C1={detail[\"C1\"]}  C2={detail[\"C2\"]}  C3={detail[\"C3\"]}')
    print(f'               C4={detail[\"C4\"]}  C5={detail[\"C5\"]}  C6={detail[\"C6\"]}')
    somme = round(sum(detail.values()))
    coherent = '✓' if abs(somme - score) <= 1 else '✗ INCOHÉRENT'
    print(f'     Σ détail : {somme} {coherent}')
    print()

db.close()
"
```

### 3b — Scoring complet des 500 clients (benchmark)

```bash
python -c "
import time
from app.db.session import SessionLocal
from app.services.scoring import ScoringEngine
from app.models.customers import Customer

db      = SessionLocal()
engine  = ScoringEngine(db)
clients = db.query(Customer).limit(500).all()

t0 = time.time()
stats = {'FAIBLE': 0, 'MOYEN': 0, 'ÉLEVÉ': 0, 'erreurs': 0}

for c in clients:
    try:
        r = engine.calculate_score(c.id)
        cat = r['risk_category']
        stats[cat] = stats.get(cat, 0) + 1
    except Exception as e:
        stats['erreurs'] += 1
        print(f'  ✗ {c.id} : {e}')

elapsed = time.time() - t0
total   = len(clients)

print(f'Scorés en {elapsed:.2f}s ({total/elapsed:.0f} clients/s)')
print(f'  FAIBLE : {stats[\"FAIBLE\"]:>4}  ({stats[\"FAIBLE\"]/total*100:.1f}%)')
print(f'  MOYEN  : {stats[\"MOYEN\"]:>4}  ({stats[\"MOYEN\"]/total*100:.1f}%)')
print(f'  ÉLEVÉ  : {stats.get(\"ÉLEVÉ\",0):>4}  ({stats.get(\"ÉLEVÉ\",0)/total*100:.1f}%)')
print(f'  Erreurs: {stats[\"erreurs\"]:>4}')
db.close()
"
```

---

## Étape 4 — Tests unitaires pytest

```bash
# Tous les tests unitaires (18 cas)
pytest tests/unit/test_scoring.py -v

# Un cas spécifique
pytest tests/unit/test_scoring.py::TestClientPEP::test_c5_max_si_pep_flag -v

# Avec couverture de code
pip install pytest-cov
pytest tests/unit/test_scoring.py --cov=app/services/scoring --cov-report=term-missing
```

Résultat attendu :

```
PASSED tests/unit/test_scoring.py::TestClientStandard::test_score_faible
PASSED tests/unit/test_scoring.py::TestClientPEP::test_c5_max_si_pep_flag
PASSED tests/unit/test_scoring.py::TestClientPEP::test_c5_max_si_correspondance_liste_pep
PASSED tests/unit/test_scoring.py::TestZoneFrontaliere::test_c2_eleve_zone_frontaliere
PASSED tests/unit/test_scoring.py::TestSmurfing::test_c3_eleve_smurfing
...
18 passed in X.XXs
```

---

## Étape 5 — Tests d'intégration API (endpoints)

### Démarrage du serveur

```bash
uvicorn app.main:app --reload --port 8000
```

### 5a — Authentification

```bash
# Login
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"admin1234"}' | python -m json.tool
```

Réponse attendue :

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_id": "...",
  "role": "admin"
}
```

### 5b — Scoring via API (script complet)

```bash
# Récupérer le token et scorer Amélie SOGLO
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"admin1234"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Récupérer l'UUID d'Amélie
AMELIE_ID=$(python -c "
from app.db.session import SessionLocal
from app.models.customers import Customer
db = SessionLocal()
c = db.query(Customer).filter(Customer.nom=='SOGLO', Customer.prenom=='Amélie').first()
print(str(c.id))
db.close()
")

echo "UUID Amélie : $AMELIE_ID"

# Appel API de scoring
curl -s -X POST http://localhost:8000/api/scoring \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"customer_id\": \"$AMELIE_ID\"}" \
  | python -m json.tool
```

Réponse attendue (Amélie SOGLO — FAIBLE) :

```json
{
  "id": "...",
  "customer_id": "...",
  "global_score": 18,
  "risk_category": "FAIBLE",
  "detail_json": {
    "C1": 2.0,
    "C2": 2.0,
    "C3": 2.5,
    "C4": 1.0,
    "C5": 0.0,
    "C6": 1.0
  },
  "is_current": true,
  "scored_by": "AUTOMATED",
  "scored_at": "2026-05-11T..."
}
```

### 5c — Vérification de l'alerte automatique (Fatima)

```bash
FATIMA_ID=$(python -c "
from app.db.session import SessionLocal
from app.models.customers import Customer
db = SessionLocal()
c = db.query(Customer).filter(Customer.nom=='OUEDRAOGO', Customer.prenom=='Fatima').first()
print(str(c.id))
db.close()
")

# Scorer Fatima
curl -s -X POST http://localhost:8000/api/scoring \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"customer_id\": \"$FATIMA_ID\"}" \
  | python -m json.tool

# Vérifier l'alerte créée
curl -s "http://localhost:8000/api/alerts?status=OPEN" \
  -H "Authorization: Bearer $TOKEN" \
  | python -m json.tool
```

### 5d — Tests d'intégration automatisés

```bash
pytest tests/integration/test_scoring_endpoints.py -v
```

---

## Étape 6 — Tests via pgAdmin / psql

```sql
-- Vérifier les scores créés
SELECT c.prenom, c.nom, s.score_global, s.categorie, s.is_current
FROM scores s
JOIN customers c ON c.id = s.client_id
ORDER BY s.date_calcul DESC
LIMIT 20;

-- Alertes SCORE_ELEVE ouvertes
SELECT c.prenom, c.nom, a.alert_type, a.risk_level, a.status, a.created_at
FROM alerts a
JOIN customers c ON c.id = a.customer_id
WHERE a.alert_type = 'SCORE_ELEVE' AND a.status = 'OPEN';

-- Répartition des catégories
SELECT categorie, COUNT(*) as nb, ROUND(COUNT(*)*100.0/SUM(COUNT(*)) OVER(), 1) as pct
FROM scores
WHERE is_current = TRUE
GROUP BY categorie;

-- Vérifier le smurfing de Fatima
SELECT t.montant, t.type_op, c2.name as pays_destination, t.date_op
FROM transactions t
JOIN customer_accounts ca ON ca.id = t.compte_id
JOIN customers c ON c.id = ca.client_id
LEFT JOIN countries c2 ON c2.id = t.destination_pays_id
WHERE c.nom = 'OUEDRAOGO' AND c.prenom = 'Fatima'
ORDER BY t.date_op DESC;
```

---

## Checklist de validation finale

```
□ seed_db.py        → tables de référence peuplées (6 critères, 3 seuils, 15 pays, 6 zones)
□ generate_fake_data.py → 500 clients + 3 scénarios créés, idempotent
□ Import scoring.py → aucune erreur
□ Scénario Amélie   → score FAIBLE  (0-33)
□ Scénario Koffi    → score MOYEN   (34-66)
□ Scénario Fatima   → score ÉLEVÉ   (≥67) + alerte SCORE_ELEVE créée
□ Σ contributions   → égale au global_score (±1)
□ is_current        → un seul TRUE par client
□ pytest unit       → 33/33 tests passent (alert service + model)
□ pytest intégration→ 15 scénarios complets OK (dont bénéficiaire groupé)
□ Audit logs        → ligne créée après chaque scoring
```

---

## Dépannage rapide

| Symptôme                               | Cause                                | Solution                                              |
| -------------------------------------- | ------------------------------------ | ----------------------------------------------------- |
| `RuntimeError: Table 'countries' vide` | seed_db.py non exécuté               | `python scripts/seed_db.py`                           |
| `AttributeError: score_min`            | Modèle RiskThreshold différent       | Vérifier le champ dans le modèle de ton binôme        |
| `C5 = 0.0` pour Fatima                 | `statut_pep` non chargé depuis la DB | Vérifier `db.refresh(customer)`                       |
| Score = 0 pour tous                    | Poids non normalisés (sum ≠ 100)     | Vérifier `_load_weights()` → division par 100         |
| `UniqueConstraint phone`               | Script relancé sans nettoyage        | Le script est idempotent → nettoie avant de regénérer |
| `TypeError: Object of type UUID is not JSON serializable` | `tx_ids` contient des UUID Python | SQLite ne sérialise pas les UUIDs → fixé dans `alert_service.py` par `str(u)` |
| Tests pytest `FAILED`                  | DB de test inaccessible              | Vérifier `DATABASE_URL` dans `.env`                   |
