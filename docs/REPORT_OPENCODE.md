# Rapport d'Analyse Technique — RiskGuard : Module de Scoring LBC/FT

**Projet** : RiskGuard — Scoring LBC/FT pour IMF Béninoises  
**Auteur** : Dev A (AFFOKPE Magloire) & Dev B (BATAMOUSSI Marcos)  
**Date** : Mai 2026  
**Contexte** : Licence Professionnelle — IUT Parakou, Bénin  

---

## 1. ARCHITECTURE GÉNÉRALE

### 1.1 Structure des dossiers

```
scoring-lbc-ft/
├── backend/                        # API FastAPI + moteur de scoring
│   ├── app/
│   │   ├── main.py                 # Point d'entrée FastAPI, CORS, middlewares, routes
│   │   ├── config.py               # Settings Pydantic (.env), seuils monétaires LBC/FT
│   │   ├── limiter.py              # Rate limiter slowapi (60/min global, 5/min login)
│   │   ├── auth/                   # Authentification JWT
│   │   │   ├── security.py         # bcrypt (hash/verify), JWT (create/decode)
│   │   │   ├── dependencies.py     # get_current_user, require_admin, require_compliance_or_admin
│   │   │   └── permissions.py      # Vérifications fines basées sur JSONB permissions
│   │   ├── db/
│   │   │   ├── base.py             # Déclaration Base SQLAlchemy
│   │   │   └── session.py          # SessionLocal, get_db (dépendance FastAPI)
│   │   ├── models/                 # 14 modèles SQLAlchemy (1 par table + app_settings)
│   │   ├── routers/                # 12 routeurs FastAPI
│   │   ├── schemas/                # 6 fichiers Pydantic (auth, customer, alert, score, transaction, common)
│   │   ├── services/               # Logique métier
│   │   │   ├── scoring.py          # Moteur de scoring (932 lignes) — cœur du projet
│   │   │   ├── alert_service.py    # Création conditionnelle d'alertes (6 types)
│   │   │   ├── audit_service.py    # Journalisation des actions utilisateur
│   │   │   ├── customer_service.py # Calcul KYC completion, determine_kyc_level
│   │   │   ├── export_service.py   # PDF (ReportLab) + CSV (3 exports)
│   │   │   ├── beneficiaire_service.py  # Détection bénéficiaire groupement
│   │   │   └── pep_service.py      # Placeholder
│   │   ├── middleware/
│   │   │   ├── logging.py          # RequestLoggingMiddleware (temps, IP, status)
│   │   │   └── error_handlers.py   # Gestionnaires 422 (validation), 500 (DB/générique)
│   │   └── utils/
│   │       ├── constants.py        # Constantes LBC/FT
│   │       ├── detail_json.py      # Utilitaire construction detail_json
│   │       └── validators.py       # Validateurs métier
│   ├── alembic/                    # Migrations DB (5 versions)
│   ├── scripts/
│   │   ├── generate_fake_data.py   # Génération 500 clients de test
│   │   ├── seed_db.py              # Seed tables de référence (223 lignes)
│   │   ├── clean_fake_data.py      # Nettoyage données générées
│   │   └── create_admin.py         # Création utilisateur admin
│   ├── tests/                      # Tests unitaires + intégration
│   ├── requirements.txt            # Dépendances production
│   └── requirements-dev.txt        # Dépendances développement
├── frontend/                       # React 18 + Vite 5 + Tailwind
│   ├── src/
│   │   ├── main.jsx                # Entry point (providers, router, mock activation)
│   │   ├── App.jsx                 # Routes (lazy loading), ProtectedRoute
│   │   ├── context/                # AuthContext (JWT), AppContext (sidebar)
│   │   ├── components/             # 9 composants réutilisables
│   │   ├── pages/                  # 10 pages (lazy loaded)
│   │   ├── services/               # 9 services API (Axios)
│   │   ├── hooks/                  # 4 hooks (useFetch, useForm, usePagination, useAuth)
│   │   ├── utils/                  # formatters, helpers, constants, validators
│   │   ├── theme/                  # colors, spacing, typography
│   │   └── mocks/                  # Mock API (développement standalone)
│   ├── tests/                      # Tests unitaires + intégration
│   └── dist/                       # Build de production
├── docs/                           # 10 fichiers de documentation
├── docker-compose.yml              # 3 services (postgres, backend, frontend)
└── Dockerfile                      # Python 3.11-slim
```

### 1.2 Flux complet d'une requête de scoring

```
Frontend (React)
  │  POST /api/scoring  { customer_id }
  │  Authorization: Bearer <JWT>
  ▼
Vite Proxy (dev) → port 8000
  │
  ▼
FastAPI (main.py)
  │  1. RequestLoggingMiddleware loggue méthode/path/status/temps/IP
  │  2. CORS check (origines configurées)
  ▼
auth/dependencies.py
  │  3. get_current_user : extrait JWT (Bearer ou cookie httpOnly)
  │  4. require_compliance_or_admin : vérifie rôle (admin ou compliance_officer)
  ▼
Routers/scoring.py — create_scoring()
  │  5. Vérifie existence customer → 404 si absent
  │  6. ScoringEngine.calculate_score(customer_id)
  │       ├── _load_weights() depuis scoring_criteria
  │       ├── _load_thresholds() depuis risk_thresholds
  │       ├── _score_c1() → note brute C1
  │       ├── _score_c2() → note brute C2
  │       ├── _score_c3() → note brute C3 (90j transactions)
  │       │     └── _detect_smurfing() → booléen
  │       │     └── _detect_duplicates() → compteur
  │       ├── _score_c4() → note brute C4 (ancienneté + réactivation)
  │       ├── _score_c5() → note brute C5 (PEP flag + pep_list)
  │       ├── _score_c6() → note brute C6 (documents + cohérence revenus)
  │       └── detail_json[code] = note_brute * poids / somme_poids
  │           global_score = sum(detail_json)
  │           risk_category = get_category(global_score)
  │
  │  7. _mark_previous_scores_as_not_current() → archive ancien score
  │  8. Crée Score en DB (is_current=True)
  │  9. create_score_alert_if_needed() → SCORE_ELEVE si ≥ 67
  │ 10. create_pep_alert_if_needed() → PEP_DETECTE si C5 ≥ 50
  │ 11. create_smurfing_alert_if_needed() → SMURFING_DETECTE si détecté
  │ 12. audit_service.log_action() → écrit dans audit_logs
  │ 13. db.commit()
  ▼
  Retourne ScoreResponse { id, customer_id, global_score, risk_category,
  │                        detail_json: {C1..C6}, is_current, scored_by, scored_at }
  ▼
Frontend → ClientDetailPage → ScorePanel (gauge SVG + RadarChart + barres)
```

---

## 2. BASE DE DONNÉES

### 2.1 Les 14 tables (schéma complet)

#### 2.1.1 `countries`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | Integer | PK, indexed | auto |
| code_iso | String(3) | UNIQUE, NOT NULL | — |
| name | String(100) | NOT NULL | — |
| is_uemoa | Boolean | | false |
| is_border | Boolean | | false |
| is_fatf | Boolean | | false |
| **Relations** : customers (FK `pays`), pep_list (FK `pays`), transactions (FK `origine_pays_id`, `destination_pays_id`) |

#### 2.1.2 `risk_zones`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | Integer | PK, indexed | auto |
| name | String(100) | NOT NULL | — |
| risk_level | String(20) | NOT NULL (FAIBLE/MOYEN/ELEVE/TRES_ELEVE) | — |
| source | Text | nullable | — |
| description | Text | nullable | — |
| **Relations** : customers (FK `zone_geo`) |

#### 2.1.3 `scoring_criteria`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | Integer | PK, indexed | auto |
| code | String(5) | UNIQUE, NOT NULL (C1–C6) | — |
| weight | Numeric(5,2) | NOT NULL | — |
| name | String(100) | NOT NULL | — |
| description | Text | nullable | — |
| updated_by | UUID | FK → users.id, nullable | — |
| updated_at | DateTime | | server_default=now() |

#### 2.1.4 `risk_thresholds`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | Integer | PK, indexed | auto |
| category | String(10) | UNIQUE, NOT NULL (FAIBLE/MOYEN/ELEVE) | — |
| score_min | Integer | NOT NULL | — |
| score_max | Integer | NOT NULL | — |
| action | Text | nullable | — |
| updated_at | DateTime | | server_default=now() |

#### 2.1.5 `user_roles`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | Integer | PK, indexed | auto |
| name | String(50) | UNIQUE, NOT NULL | — |
| permissions | JSONB | NOT NULL | {} |
| **Relations** : users (FK `role_id`) |

#### 2.1.6 `users`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | UUID | PK | uuid4 |
| login | String(50) | UNIQUE, NOT NULL | — |
| password_hash | String(255) | NOT NULL (bcrypt) | — |
| role_id | Integer | FK → user_roles.id, NOT NULL | — |
| is_active | Boolean | | true |
| last_login | DateTime | nullable | — |
| created_at | DateTime | | server_default=now() |
| **Relations** : role (user_roles), audit_logs, scores (calcule_par indirect), alerts (clos_par) |

#### 2.1.7 `customers`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | UUID | PK | uuid4 |
| nom | String(100) | NOT NULL | — |
| prenom | String(100) | NOT NULL | — |
| date_naissance | Date | nullable | — |
| phone | String(20) | UNIQUE, nullable | — |
| email | String(150) | UNIQUE, nullable | — |
| profession_code | String(50) | nullable | — |
| profession_name | String(150) | nullable | — |
| profession_risk | String(10) | nullable (LOW/MEDIUM/HIGH) | — |
| revenus_declares | Numeric(15,2) | nullable | — |
| city | String(100) | nullable | — |
| region | String(100) | nullable | — |
| latitude | String(20) | nullable | — |
| longitude | String(20) | nullable | — |
| zone_geo | Integer | FK → risk_zones.id, nullable, indexed | — |
| pays | Integer | FK → countries.id, nullable, indexed | — |
| statut_pep | Boolean | indexed | false |
| pep_verified_by | UUID | FK → users.id, nullable | — |
| kyc_level | String(10) | indexed | 'LOW' |
| kyc_completion | Integer | | 0 |
| status | String(20) | indexed | 'ACTIVE' |
| date_creation | DateTime | | server_default=now() |
| updated_at | DateTime | | server_default=now(), onupdate |
| **Relations** : zone_geo → risk_zones, pays → countries, documents (cascade), accounts (cascade), alerts, scores |

#### 2.1.8 `customer_accounts`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | UUID | PK | uuid4 |
| client_id | UUID | FK → customers.id (CASCADE), NOT NULL, indexed | — |
| type_compte | String(50) | nullable | — |
| solde_moyen | Numeric(15,2) | | 0 |
| date_ouverture | Date | nullable | — |
| status | String(50) | | 'ACTIF' |
| created_at | DateTime | | server_default=now() |
| **Relations** : client → customers, transactions (cascade) |

#### 2.1.9 `customer_docs`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | UUID | PK | uuid4 |
| client_id | UUID | FK → customers.id (CASCADE), NOT NULL, indexed | — |
| type_doc | String(50) | NOT NULL (CNI/passeport/permis/attestation) | — |
| numero | String(100) | nullable | — |
| date_expiration | Date | nullable | — |
| verified_by | UUID | FK → users.id, nullable, indexed | — |
| created_at | DateTime | | server_default=now() |
| **Propriété calculée** : `valide` = `date_expiration >= today OR date_expiration IS NULL` |

#### 2.1.10 `transactions`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | UUID | PK | uuid4 |
| compte_id | UUID | FK → customer_accounts.id (CASCADE), NOT NULL, indexed | — |
| montant | Numeric(15,2) | NOT NULL | — |
| devise | String(5) | | 'XOF' |
| type_op | String(50) | nullable (DEPOT/RETRAIT/VIREMENT/PAIEMENT) | — |
| date_op | DateTime | indexed | server_default=now() |
| canal | String(50) | nullable (MOBILE/GUICHET/INTERNET/ATM) | — |
| origine | Text | nullable | — |
| destination | Text | nullable | — |
| origine_pays_id | Integer | FK → countries.id, nullable, indexed | — |
| destination_pays_id | Integer | FK → countries.id, nullable, indexed | — |

#### 2.1.11 `alerts`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | UUID | PK | uuid4 |
| client_id | UUID | FK → customers.id (CASCADE), NOT NULL, indexed | — |
| clos_par | UUID | FK → users.id, nullable, indexed | — |
| type_alerte | String(50) | NOT NULL (SCORE_ELEVE/KYC_INCOMPLET/PEP_DETECTE/SEUIL_DEPASSE/BENEFICIAIRE_GROUPEMENT/SMURFING_DETECTE) | — |
| statut | String(20) | NOT NULL, indexed | 'OPEN' |
| decision | Text | nullable | — |
| sar_declare | Boolean | NOT NULL | false |
| date_creation | DateTime | | server_default=now() |
| date_cloture | DateTime | nullable | — |

#### 2.1.12 `scores`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | UUID | PK | uuid4 |
| client_id | UUID | FK → customers.id, NOT NULL, indexed | — |
| score_global | Integer | NOT NULL (0-100) | — |
| detail_json | JSONB | NOT NULL ({C1..C6}) | — |
| categorie | String(10) | NOT NULL (FAIBLE/MOYEN/ÉLEVÉ) | — |
| is_current | Boolean | | true |
| date_calcul | DateTime | | server_default=now() |
| calcule_par | String(50) | | 'AUTOMATED' |

#### 2.1.13 `audit_logs`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | UUID | PK | uuid4 |
| user_id | UUID | FK → users.id, NOT NULL, indexed | — |
| client_id | UUID | FK → customers.id, nullable, indexed | — |
| action | String(100) | NOT NULL | — |
| timestamp | DateTime | | server_default=now() |
| ip_address | String(45) | nullable | — |

#### 2.1.14 `pep_list`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | UUID | PK | uuid4 |
| pays | Integer | FK → countries.id, nullable | — |
| nom | String(100) | NOT NULL, indexed | — |
| prenom | String(100) | NOT NULL | — |
| fonction | String(200) | nullable | — |
| date_debut | Date | nullable | — |
| date_fin | Date | nullable | — |
| source | String(100) | nullable (GIABA/CENTIF/ONU) | — |
| active | Boolean | NOT NULL | true |
| **Trigger** : avant insert/update, `active` est recalculé selon `date_fin` |

#### 2.1.15 `app_settings`
| Champ | Type | Contraintes | Défaut |
|-------|------|-------------|--------|
| id | Integer | PK, autoincrement | auto |
| key | String(100) | UNIQUE, NOT NULL, indexed | — |
| value | Float | NOT NULL | — |
| label | String(200) | nullable | — |
| description | String(500) | nullable | — |
| updated_at | DateTime | | server_default=now(), onupdate |

### 2.2 Relations et clés étrangères

```
user_roles (1) ──< users (N) ──< audit_logs
                               ──< alerts (clos_par)
customers (1) ──< customer_accounts (N) ──< transactions (N)
            ──< customer_docs (N)
            ──< alerts (N)
            ──< scores (N)
            >── risk_zones (zone_geo)
            >── countries (pays)
pep_list >── countries (pays)
```

### 2.3 Rôle métier de chaque table

| Table | Rôle |
|-------|------|
| **customers** | Cœur du système — identité, profil risque, KYC, statut PEP |
| **customer_accounts** | Comptes bancaires du client (types, soldes, ancienneté) |
| **transactions** | Flux financiers analysés par C3 (90 jours) |
| **customer_docs** | Documents d'identité (validité, expiration) pour C6 |
| **scores** | Historique des scores LBC/FT avec détail C1-C6 |
| **alerts** | Alertes générées automatiquement ou manuellement (6 types) |
| **countries** | Référentiel pays avec attributs LBC/FT (UEMOA, FATF, frontalier) |
| **risk_zones** | Zones géographiques à risque (FAIBLE → TRES_ELEVE) |
| **scoring_criteria** | Configuration des 6 critères et leurs poids |
| **risk_thresholds** | Seuils de catégorisation (FAIBLE/MOYEN/ÉLEVÉ) |
| **pep_list** | Liste des Personnes Exposées Politiquement (vigilance GAFI) |
| **users** | Utilisateurs de l'application (admin, compliance_officer) |
| **user_roles** | Rôles avec permissions JSONB (admin/compliance_officer) |
| **audit_logs** | Piste d'audit exhaustive (qui a fait quoi, quand, depuis quelle IP) |
| **app_settings** | Paramètres configurables (seuils monétaires, fenêtres de cumul) |

---

## 3. MOTEUR DE SCORING (ScoringEngine)

### 3.1 Algorithme général

La classe `ScoringEngine` dans `backend/app/services/scoring.py` (932 lignes) implémente le calcul du score LBC/FT.

**Principe** : 6 notes brutes (0-100) sont calculées indépendamment, puis multipliées par leur poids respectif pour obtenir des contributions absolues. La somme des contributions donne le score global (0-100).

### 3.2 C1 — Profil professionnel (poids 20%)

Note basée sur `profession_risk` :

| profession_risk | Note brute |
|----------------|-----------|
| LOW | 10.0 |
| MEDIUM | 35.0 |
| HIGH | 65.0 |
| None/inconnu | 85.0 |

**Ajustements** :
- Si revenus déclarés = 0 ET risque ≠ HIGH : note +10 (plafond 100)
- Si revenus > 5 000 000 XOF ET risque = LOW : note +15 (incohérence)

### 3.3 C2 — Zone géographique (poids 20%)

Note basée sur `risk_zone.risk_level` :

| risk_level | Note brute |
|-----------|-----------|
| FAIBLE | 10.0 |
| MOYEN | 35.0 |
| ELEVE | 65.0 |
| TRES_ELEVE | 88.0 |
| Inconnue | 50.0 |

**Surcharges pays** :
- `is_fatf` : note = max(note, 70)
- `is_border` : note = max(note, 55)
- `is_uemoa` : note = min(note, 40)

### 3.4 C3 — Historique transactionnel (poids 25%)

Analyse des 90 derniers jours de transactions. Note de base = 10. Chaque sous-détection peut augmenter la note (mécanisme `max()`).

**a) Ratio total 3 mois / revenus** :
- > 10× → 95 ; > 5× → 80 ; > 3× → 60 ; > 1.5× → 40
- Montant absolu > 50M → 90 ; > 20M → 75

**a') Ratio 30 jours glissants** :
- > 10× → 95 ; > 3× → 80 ; > 2× → 60 ; > 1× → 40
- Montant absolu > 30M → 90 ; > 10M → 75

**b) Fréquence anormale** : > 5 tx/jour → 70 ; > 2 → 45

**c) Retraits cash** : > 10 → 65 ; > 5 → 40

**d) Smurfing `_detect_smurfing()`** : 3 conditions cumulatives
1. Au moins 3 transactions suspectes (montant rond multiple de 10k ET < 500k, OU near-threshold 80%-100% du seuil — soit 400k-499k)
2. Ces transactions concentrées sur ≤ 7 jours
3. Total suspects ≥ 3× revenus mensuels
→ note = max(note, 85)

**d') Homogénéité** : CV < 0.10 → 60 ; CV < 0.15 → 40

**e) Destinations risquées** (FATF/frontaliers) : > 50% → 75 ; > 20% → 55

**f) Transactions dupliquées `_detect_duplicates()`** : même montant (arrondi centaine) + même destination dans 24h → ≥ 3 groupes → 60 ; ≥ 1 → 40

### 3.5 C4 — Ancienneté & fidélité (poids 10%)

| Âge du compte | Note brute |
|--------------|-----------|
| > 3 ans | 10.0 |
| 1–3 ans | 35.0 |
| 180–365 jours | 60.0 |
| < 180 jours | 75.0 |

**Réactivation brutale** : si compte > 1 an, 0 tx sur 180 jours ET ≥ 3 tx sur 30 jours → note +30

### 3.6 C5 — Statut PEP (poids 15%)

| Condition | Note |
|----------|------|
| `statut_pep = True` (flag manuel) | 100 |
| Match dans `pep_list` avec `active=True` | 100 |
| Match dans `pep_list` avec `active=False`, date_fin < 5 ans | 50 |
| Match dans `pep_list` sans date_fin (prudence) | 50 |
| Match avec date_fin > 5 ans | 0 |
| Aucun match | 0 |

La recherche utilise la normalisation NFKD (suppression accents) et ILIKE.

### 3.7 C6 — Cohérence KYC (poids 10%)

**Documents** :
- Aucun document → 85
- > 50% invalides → 85 ; au moins un invalide → 55 ; expiration imminente → 30

**Cohérence revenus/flux** : transaction mensuelle moyenne / revenus > 10× → 75 ; > 5× → 55 ; > 2× → 35

**Complétion KYC** : < 30% → 80 ; < 60% → 40

### 3.8 Formule finale

```python
detail_json[code] = round(note_brute * poids_normalisé, 4)
global_score = min(100, max(0, round(sum(detail_json.values()))))
risk_category = _get_category(global_score)
```

Poids par défaut : C1=20%, C2=20%, C3=25%, C4=10%, C5=15%, C6=10%
Seuils : FAIBLE 0-33, MOYEN 34-66, ÉLEVÉ 67-100

### 3.9 Construction du `detail_json`

Le `detail_json` retourné contient les contributions absolues (pas les notes brutes) :

```json
{
  "C1": 2.0,    // note_brute=10 * 0.20
  "C2": 2.0,    // note_brute=10 * 0.20
  "C3": 2.5,    // note_brute=10 * 0.25
  "C4": 1.0,    // note_brute=10 * 0.10
  "C5": 0.0,    // note_brute=0  * 0.15
  "C6": 1.0     // note_brute=10 * 0.10
}
```

Le résultat étendu (v1.3) inclut aussi :
- `c5_score` : la note brute C5 (0/50/100) pour le service d'alertes
- `smurfing_detected` : booléen pour l'alerte SMURFING_DETECTE

### 3.10 Exemples de résultats (scénarios)

**Amélie SOGLO** (risque FAIBLE) : score attendu < 34
- Profession : Fonctionnaire (LOW) → C1 = 10 × 0.20 = 2.0
- Zone : CAPITALE (FAIBLE) → C2 = 10 × 0.20 = 2.0
- Transactions régulières, revenus cohérents → C3 = 10 × 0.25 = 2.5
- Compte > 3 ans → C4 = 10 × 0.10 = 1.0
- Non PEP → C5 = 0 × 0.15 = 0.0
- KYC 95% complet, docs valides → C6 = 10 × 0.10 = 1.0
- **Total : 2.0 + 2.0 + 2.5 + 1.0 + 0.0 + 1.0 = 8.5 → FAIBLE**

**Koffi BIAOU** (risque MOYEN) : score attendu 34-66
- Profession : Commerçant transfrontalier (HIGH) → C1 = 65 × 0.20 = 13.0
- Zone : FRONTIERE (ELEVE) → C2 = 65 × 0.20 = 13.0
- Transactions avec anomaly_factor=2.5 → C3 majoré
- Compte ~2 ans → C4 = 35 × 0.10 = 3.5
- Non PEP → C5 = 0
- KYC partiel, passeport expirant → C6 majoré
- **Total estimé ~45 → MOYEN**

**Fatima OUEDRAOGO** (risque ÉLEVÉ) : score ≥ 67
- Profession : Changeur (HIGH) → C1 = 65 × 0.20 = 13.0
- Zone : FRONTIERE (ELEVE) → C2 = 65 × 0.20 = 13.0
- Smurfing 6× virements 400k-490k vers Nigeria → C3 ≥ 85 × 0.25 = 21.25
- Compte récent → C4 = 75 × 0.10 = 7.5
- PEP active → C5 = 100 × 0.15 = 15.0
- KYC minimal, docs expirés → C6 ≥ 80 × 0.10 = 8.0
- **Total : 13.0 + 13.0 + 21.25 + 7.5 + 15.0 + 8.0 = 77.75 → ÉLEVÉ**

---

## 4. API FASTAPI

### 4.1 Tous les endpoints

#### Authentification
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| POST | `/auth/login` | `{login, password}` | `{access_token, token_type, user_id, role}` | Public (rate-limité 5/min) |
| GET | `/auth/me` | — | `{id, login, role, is_active}` | Authentifié |

#### Clients
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| GET | `/api/clients` | `?search, status, kyc_level, statut_pep, zone_geo, skip, limit` | `{items: CustomerSummary[], total}` | Authentifié |
| GET | `/api/clients/{id}` | — | CustomerDetail | Authentifié |
| POST | `/api/clients` | CustomerCreate | CustomerSummary (201) | Compliance/Admin |
| PUT | `/api/clients/{id}` | CustomerUpdate | CustomerSummary | Compliance/Admin |

#### Comptes clients
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| GET | `/api/customers/{id}/accounts` | — | `{items: AccountSchema[], total}` | Authentifié |
| GET | `/api/accounts/{id}` | — | AccountSchema | Authentifié |
| POST | `/api/customers/{id}/accounts` | AccountCreate | AccountSchema (201) | Compliance/Admin |

#### Documents
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| GET | `/api/customers/{id}/documents` | — | `{items: DocumentSchema[], total}` | Authentifié |
| GET | `/api/documents/{id}` | — | DocumentSchema | Authentifié |
| POST | `/api/customers/{id}/documents` | DocumentCreate | DocumentSchema (201) | Compliance/Admin |

#### Transactions
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| GET | `/api/customers/{id}/transactions` | `?days, type_op, skip, limit` | TransactionResponse | Authentifié |
| GET | `/api/transactions/{id}` | — | TransactionResponse | Authentifié |
| POST | `/api/customers/{id}/transactions` | TransactionCreate | TransactionCreateResponse (inclut nouveau score) | Compliance/Admin |

#### Alertes
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| GET | `/api/alerts` | `?statut, type_alerte, sar_declare, skip, limit` | `{items: AlertResponse[], total}` | Authentifié |
| GET | `/api/alerts/{id}` | — | AlertResponse | Authentifié |
| GET | `/api/customers/{id}/alerts` | — | AlertResponse[] | Authentifié |
| POST | `/api/alerts` | AlertCreate | AlertResponse (201) | Compliance/Admin |
| PUT | `/api/alerts/{id}` | AlertUpdate | AlertResponse | Compliance/Admin |

#### Scoring
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| POST | `/api/scoring` | `{customer_id}` | ScoreResponse | Compliance/Admin |
| POST | `/api/scoring/rescore` | `{customer_id}` | ScoreResponse | Compliance/Admin |
| POST | `/api/scoring/rescore-all` | — | `{rescored, critical}` | Compliance/Admin |
| GET | `/api/scores/{id}` | — | ScoreResponse | Authentifié |
| GET | `/api/customers/{id}/scores` | `?skip, limit` | ScoreListResponse | Authentifié |

#### Dashboard
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| GET | `/api/dashboard/stats` | — | KPIs (total_clients, risk dist., KYC dist., alertes, transactions) | Authentifié |
| GET | `/api/dashboard/alerts` | — | 5 dernières alertes ouvertes | Authentifié |
| GET | `/api/dashboard/pep` | — | PEP actifs | Authentifié |

#### Administration
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| GET | `/api/admin/scoring-criteria` | — | Liste critères C1-C6 | Admin |
| PUT | `/api/admin/scoring-criteria/{id}` | `{weight}` | Critère mis à jour | Admin |
| GET | `/api/admin/risk-thresholds` | — | Seuils | Admin |
| PUT | `/api/admin/risk-thresholds/{id}` | — | Seuil mis à jour | Admin |
| GET | `/api/admin/settings` | — | Paramètres app | Admin |
| PUT | `/api/admin/settings/{key}` | `{value}` | Setting mis à jour | Admin |
| GET | `/api/admin/users` | — | Liste utilisateurs | Admin |
| POST | `/api/admin/users` | UserCreate | Utilisateur créé | Admin |
| PUT | `/api/admin/users/{id}/toggle-active` | — | Actif/inactif | Admin |
| PUT | `/api/admin/users/{id}/reset-password` | — | Mot de passe réinitialisé | Admin |
| POST | `/api/admin/pep-list/import` | CSV | Import PEP | Admin |
| POST | `/api/admin/pep-list` | PepCreate | Entrée PEP créée | Admin |
| GET | `/api/admin/audit-logs` | `?action, user_id, skip, limit` | AuditLogs paginés | Admin |

#### Référentiels
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| GET | `/api/countries` | — | Liste pays | Authentifié |
| POST | `/api/countries` | CountryCreate | Pays créé | Admin |
| PUT | `/api/countries/{id}` | CountryUpdate | Pays mis à jour | Admin |
| GET | `/api/risk-zones` | — | Liste zones risque | Authentifié |

#### PEP
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| GET | `/api/pep` | `?search, active` | Liste PEP paginée | Authentifié |

#### Exports
| Méthode | Route | Paramètres | Réponse | Rôle |
|---------|-------|-----------|---------|------|
| GET | `/api/exports/customer/{id}/pdf` | — | PDF (StreamingResponse) | Compliance/Admin |
| GET | `/api/exports/transactions/{id}/csv` | — | CSV UTF-8 BOM | Compliance/Admin |
| GET | `/api/exports/sar/{alert_id}/pdf` | — | PDF SAR CENTIF | Compliance/Admin |

#### Health
| Méthode | Route | Réponse |
|---------|-------|---------|
| GET | `/` | `{status: "ok", app: "RiskGuard API", version: "1.0.0"}` |

### 4.2 Authentification JWT

Implémentée dans `auth/security.py` et `auth/dependencies.py` :

1. **Hash des mots de passe** : bcrypt via `passlib.CryptContext(schemes=["bcrypt"])`
2. **Création du JWT** : `jose.jwt.encode()` avec payload `{sub: user_id, role: role_name, exp: expiry}` — algorithme HS256, expiration configurable (480 min par défaut)
3. **Vérification** : le token est extrait soit de l'en-tête `Authorization: Bearer <token>`, soit du cookie HTTP-only `access_token`
4. **Reconstruction utilisateur** : requête `User` par ID depuis le token + vérification `is_active=True`
5. **Rôles** : deux dépendances — `require_admin` (403 si pas admin) et `require_compliance_or_admin` (403 si ni admin ni compliance_officer)

### 4.3 Gestion des erreurs HTTP

Middleware `error_handlers.py` :

| Exception | Status | Format réponse |
|-----------|--------|---------------|
| `RequestValidationError` (Pydantic) | 422 | `{error: "Validation failed", detail: [{field, message, type}]}` |
| `SQLAlchemyError` | 500 | `{error: "Database error", detail: "..."}` (générique, pas de détails internes) |
| `Exception` (non catchée) | 500 | `{error: "Internal server error", detail: "..."}` |
| `RateLimitExceeded` (slowapi) | 429 | Géré par slowapi |

Les `HTTPException` standard FastAPI sont laissées telles quelles (401, 403, 404, etc.).

### 4.4 Middleware de journalisation

`RequestLoggingMiddleware` dans `middleware/logging.py` :
- Log chaque requête : `"GET /api/clients — 200 — 45.2ms — 127.0.0.1"`
- Exclut les routes `/`, `/docs`, `/redoc`, `/openapi.json`
- Ajoute les en-têtes de réponse `X-Process-Time` et `X-RiskGuard-Version`
- Log en `ERROR` si une exception est levée pendant le traitement

Le `audit_service.py` complète cette journalisation technique par une **piste d'audit métier** (table `audit_logs`) avec les actions standardisées (LOGIN, VIEW_CUSTOMER, SCORING_CALCULATE, EXPORT_PDF, etc.).

---

## 5. SCRIPT FAKER (génération de données)

### 5.1 Génération des 500 clients

Le script `scripts/generate_fake_data.py` (1326 lignes) génère **exactement 500 clients** :

- **3 scénarios obligatoires** : Amélie SOGLO, Koffi BIAOU, Fatima OUEDRAOGO — créés en premier avec des attributs codés en dur
- **497 clients aléatoires** générés par la fonction `generate_random_clients()`

**Processus de génération** :
1. **Profession** : choisie parmi 19 métiers béninois (FONCT_PUBL, COMMER_TRANSFR, CHANGEUR, AGRICULTEUR, COUTURIER, etc.) chacun avec un niveau de risque (LOW/MEDIUM/HIGH) et une plage de revenus
2. **Zone géographique** : choisie selon le niveau de risque (LOW→FAIBLE, HIGH→ELEVE/TRES_ELEVE)
3. **Pays** : choisi selon la zone (70% Bénin, 30% autre pays UEMOA/frontalier)
4. **Revenus** : générés aléatoirement dans la plage de la profession, arrondis au millier
5. **KYC** : completion% et niveau déterminés selon le risque professionnel (LOW→70-100%, HIGH→10-70%)
6. **PEP** : ~2% des clients (10/497) marqués PEP aléatoirement
7. **Documents** : 1-2 documents par client, validité selon le niveau KYC
8. **Transactions** : 3-8 transactions/mois sur 1-6 mois

### 5.2 Cohérence entre tables

Les UUID sont générés côté client (v1.1) pour permettre la construction complète du graphe d'objets sans `db.flush()` intermédiaire :

```python
customer = Customer(id=uuid.uuid4(), ...)  # UUID disponible immédiatement
account = CustomerAccount(id=uuid.uuid4(), client_id=customer.id, ...)
doc = CustomerDoc(id=uuid.uuid4(), client_id=customer.id, ...)
transaction = Transaction(id=uuid.uuid4(), compte_id=account.id, ...)
```

Les transactions sont accumulées par batch de 100 et insérées via `db.add_all(tx_batch)`. Les relations FK avec CASCADE garantissent l'intégrité au niveau base.

### 5.3 Scénarios spéciaux

**Smurfing** (dans `_generate_smurfing_transactions()`) :
- Crée 6 virements de 400 000-490 000 XOF (juste sous le seuil FATF de 500 000 XOF)
- Via INTERNET/MOBILE vers pays FATF ou frontalier
- 15% des clients HIGH-risk reçoivent 3-5 transactions smurfing

**PEP** :
- ~2% des clients marqués avec `statut_pep=True`
- Fonctions PEP typiques : Député, Conseiller présidentiel, Directeur Trésor, Préfet, Ambassadeur, Général
- Sources : GIABA, CENTIF, ONU

**Zones frontières** :
- Les clients HIGH-risk sont plus susceptibles d'être assignés à des zones ELEVE/TRES_ELEVE (FRONTIERE, CONFLIT)
- Les pays FATF/frontaliers (Nigeria, Libye, etc.) sont utilisés comme destinations de transactions risquées

### 5.4 Profils annotés (ground truth)

**3 profils explicites** documentés dans `docs/SCENARIOS.md` :

| Client | Risque attendu | Score attendu |
|--------|---------------|--------------|
| Amélie SOGLO | FAIBLE | < 34 |
| Koffi BIAOU | MOYEN | 34-66 |
| Fatima OUEDRAOGO | ÉLEVÉ | ≥ 67 |

**18 tests unitaires** dans `tests/unit/test_scoring.py` avec des profils synthétiques et des assertions de score (test_score_faible, test_c5_max_si_pep_flag, test_c3_eleve_smurfing, test_c6_eleve_doc_invalide, etc.).

---

## 6. FRONTEND REACT

### 6.1 Pages développées (10)

| Page | Rôle |
|------|------|
| **LoginPage** | Authentification avec validation, eye toggle, branding |
| **DashboardPage** | KPIs, graphiques risque/KYC, alertes récentes, PEP |
| **ClientsListPage** | Tableau paginé, filtres (KYC, statut, PEP), recherche |
| **ClientDetailPage** | 4 onglets (KYC, Scoring, Transactions, Alertes), exports PDF/CSV |
| **AddClientPage** | Assistant 3 étapes (identité → adresse → documents) |
| **EditClientPage** | Modification client avec pré-remplissage |
| **AlertsPage** | Alertes filtrables, mise à jour statut, création, SAR PDF |
| **ExportsPage** | Recherche auto-complétion, 3 types d'export |
| **ScorePage** | Visualisation standalone du score |
| **AdminPage** | 7 onglets admin (critères, seuils, paramètres, pays, PEP, utilisateurs, audit logs) |

### 6.2 Dashboard

Affiche :
- **Cartes KPI** : total clients, nombre PEP, alertes ouvertes, répartition risque
- **PieChart** (Recharts) : répartition des clients par catégorie de risque (FAIBLE/MOYEN/ÉLEVÉ)
- **BarChart** (Recharts) : distribution des niveaux KYC
- **Tableau** : 5 dernières alertes ouvertes
- **Liste** : clients PEP actifs
- **Client le plus risqué** : score maximum

### 6.3 Fiche client (ClientDetailPage)

4 onglets :
1. **KYC** : identité, profession, zone, pays, statut PEP, complétion KYC, documents
2. **Scoring & Historique** : jauge SVG circulaire (score/100), RadarChart 6 critères, barres C1-C6, tableau d'historique des scores
3. **Transactions** : tableau paginé, filtres par type/période
4. **Alertes** : alertes du client, modal de création, mise à jour, export SAR PDF

Les exports PDF/CSV sont accessibles depuis cette page.

### 6.4 Filtrage / Pagination / Export

- **Filtres** : par statut, KYC level, PEP, type d'alerte, période (hooks `useForm`)
- **Pagination** : hook `usePagination` (25 items/page, prev/next/numéros)
- **Export** : 3 endpoints — PDF client (3 pages, Chart ReportLab), CSV transactions (UTF-8 BOM, séparateur `;`), PDF SAR CENTIF

### 6.5 Authentification JWT côté frontend

- `AuthContext.jsx` : stocke le token dans `localStorage` (clé `riskguard_token`)
- `login()` : appelle `POST /auth/login`, stocke le token, configure l'en-tête Axios `Authorization: Bearer`
- `logout()` : efface le token et redirige vers `/login`
- `restoreFromStorage()` : au montage de l'application, appelle `GET /auth/me` pour valider le token
- `ProtectedRoute` : vérifie la présence du token et le rôle (admin pour les routes admin)
- Intercepteur Axios : 401 → redirection vers `/login`

---

## 7. FONCTIONNALITÉS COMPLÈTES

| Fonctionnalité | Description | Utilisateurs | Statut |
|---------------|------------|-------------|--------|
| Authentification JWT | Login/mot de passe avec bcrypt, token JWT 8h, httpOnly cookie | Tous | Terminée |
| Gestion des clients | CRUD complet avec filtres, recherche, pagination | Agent/Admin | Terminée |
| Scoring LBC/FT | Calcul automatique 6 critères pondérés (C1-C6) | Agent/Admin | Terminée |
| Rescoring manuel | Recalcul du score sans doublon d'alertes | Agent/Admin | Terminée |
| Rescoring global | Recalcul de tous les clients (batch 20) | Agent/Admin | Terminée |
| Alertes automatiques | 6 types : SCORE_ELEVE, PEP_DETECTE, SMURFING, KYC, SEUIL, BENEFICIAIRE | Agent/Admin | Terminée |
| Détection smurfing | Fractionnement near-threshold + concentration temporelle | Automatique | Terminée |
| Détection PEP | Flag manuel + liste PEP avec vigilance 5 ans post-mandat | Automatique | Terminée |
| Gestion des alertes | CRUD, mise à jour statut, déclaration SAR | Agent/Admin | Terminée |
| Dashboard | KPIs, graphiques (risque, KYC), alertes récentes, PEP | Tous | Terminée |
| Export PDF fiche client | 3 pages : KYC, score, historiques, alertes, conformité CENTIF | Agent/Admin | Terminée |
| Export CSV transactions | UTF-8 BOM, séparateur `;`, colonnes françaises | Agent/Admin | Terminée |
| Export PDF SAR | Déclaration de soupçon conforme CENTIF Bénin | Agent/Admin | Terminée |
| Administration critères | Modification des poids C1-C6 (validation somme=100%) | Admin | Terminée |
| Administration seuils | Configuration des plages FAIBLE/MOYEN/ÉLEVÉ | Admin | Terminée |
| Administration paramètres | Seuils monétaires, fenêtres de cumul | Admin | Terminée |
| Gestion utilisateurs | Création, activation/désactivation, reset password | Admin | Terminée |
| Import PEP CSV | Importation fichier CSV dans pep_list | Admin | Terminée |
| Journalisation audit | Piste d'audit complète (actions, IP, timestamps) | Admin | Terminée |
| Rate limiting | 5 req/min sur /auth/login (anti-bruteforce) | Automatique | Terminée |
| Mocks frontend | Simulation complète API pour développement standalone | Développeur | Terminée |
| Gestion des transactions | CRUD avec déclenchement automatique rescore + alertes | Agent/Admin | Terminée |
| Assistant ajout client | Formulaire 3 étapes avec validation | Agent/Admin | Terminée |
| Génération données test | 500 clients (497 aléatoires + 3 scénarios) | Développeur | Terminée |
| Migrations DB | Alembic (5 versions de migration) | Développeur | Terminée |
| Docker | 3 services : postgres, backend, frontend | Déploiement | Terminée |
| Tests unitaires scoring | 18 cas de test avec ground truth | Développeur | Partielle (1 test d'intégration échoue) |

---

## 8. SÉCURITÉ

### 8.1 Mécanismes implémentés

| Mécanisme | Implémentation | Détail |
|-----------|---------------|--------|
| **Hachage mots de passe** | bcrypt via passlib | 12 rounds, `CryptContext(schemes=["bcrypt"])` |
| **JWT** | python-jose (HS256) | Payload : `{sub, role, exp}`, durée 8h |
| **CORS** | FastAPI CORSMiddleware | Origines listées explicitement (localhost:5173, etc.) |
| **Rate Limiting** | slowapi | 60 req/min global, 5 req/min sur `/auth/login` |
| **Validation entrées** | Pydantic v2 | Schemas stricts, `@model_validator` fail-fast |
| **Protection DB** | SQLAlchemy | Requêtes paramétrées, pas de SQL brut |
| **Cookie httpOnly** | JWT en cookie + Bearer | Double mode d'authentification |
| **Validation .env** | Config Pydantic | Rejet SECRET_KEY faible, DEBUG + DB distante interdit |

### 8.2 Vérification des rôles

Trois niveaux de protection par dépendance FastAPI :
- `get_current_user` : 401 si token invalide/absent ou utilisateur inactif
- `require_admin` : 403 si rôle ≠ "admin"
- `require_compliance_or_admin` : 403 si rôle ni "admin" ni "compliance_officer"

### 8.3 Journalisation (audit_logs)

Le `audit_service.py` journalise les actions suivantes dans la table `audit_logs` :

| Action | Déclencheur |
|--------|------------|
| LOGIN | Connexion réussie |
| LIST_CLIENTS | Consultation liste clients |
| VIEW_CUSTOMER | Consultation détail client |
| CREATE_CUSTOMER | Création client |
| UPDATE_CUSTOMER | Modification client |
| LIST_ALERTS | Consultation alertes |
| VIEW_ALERT | Détail alerte |
| CREATE_ALERT | Création manuelle alerte |
| UPDATE_ALERT | Mise à jour alerte |
| SCORING_CALCULATE | Calcul initial score |
| SCORING_RESCORE | Rescore manuel |
| SCORING_RESCORE_ALL | Rescore global |
| EXPORT_PDF | Export PDF |
| EXPORT_CSV | Export CSV |
| IMPORT_PEP_LIST | Import liste PEP |
| UPDATE_SCORING_CRITERIA | Modification poids C1-C6 |

Chaque entrée enregistre : `user_id`, `action`, `client_id` (optionnel), `ip_address`, `timestamp`.

---

## 9. DOCKER

### 9.1 docker-compose.yml

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    container_name: scoring_db
    ports: ["5433:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck: pg_isready -U marcos
    environment: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB

  backend:
    build: ./backend (Dockerfile: python:3.11-slim)
    container_name: scoring_backend
    ports: ["8000:8000"]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    depends_on: postgres (condition: service_healthy)
    volumes: [./backend:/app]
    environment: DATABASE_URL, SECRET_KEY, DEBUG

  frontend:
    image: node:18-alpine
    container_name: scoring_frontend
    ports: ["5173:5173"]
    command: npm run dev
    volumes: [./frontend:/app]
    environment: VITE_API_URL

volumes:
  postgres_data:

networks:
  scoring_network: (driver: bridge)
```

### 9.2 Lancement

```bash
# Une commande
docker-compose up --build

# Avec variables d'environnement
POSTGRES_PASSWORD=mon_mdp SECRET_KEY=$(openssl rand -hex 32) docker-compose up --build
```

### 9.3 Variables d'environnement (.env)

```
DATABASE_URL=postgresql://marcos:password@localhost:5433/scoring_db
SECRET_KEY=<openssl rand -hex 32>
DEBUG=false
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
POSTGRES_USER=marcos
POSTGRES_PASSWORD=password
POSTGRES_DB=scoring_db
VITE_API_URL=http://localhost:8000
```

---

## 10. TESTS ET RÉSULTATS

### 10.1 Tests écrits

**Backend — Tests unitaires** (`backend/tests/unit/`) :
| Fichier | Tests | Couverture |
|---------|-------|-----------|
| `test_scoring.py` | 18 tests | Tous les critères C1-C6, smurfing, PEP, erreurs |
| `test_auth.py` | — | Authentification JWT |
| `test_models.py` | — | Modèles SQLAlchemy |
| `test_services.py` | — | Services métier |

**Backend — Tests d'intégration** (`backend/tests/integration/`) :
| Fichier | Tests | Couverture |
|---------|-------|-----------|
| `test_endpoints.py` | 1+ tests | Endpoints API |
| `test_scoring_endpoints.py` | — | Endpoints scoring |
| `test_database.py` | — | Base de données |
| `test_exports.py` | — | Export PDF/CSV |
| `test_scenarios_complets.py` | — | Scénarios complets |
| `test_workflow.py` | — | Workflow complet |

**Frontend** (`frontend/tests/`) :
| Fichier | Tests |
|---------|-------|
| `unit/components.test.jsx` | Tests composants |
| `integration/pages.test.jsx` | Tests pages |

### 10.2 Résultats obtenus

Le fichier `test_result.log` montre **1 test d'intégration en échec** :
- `test_create_transaction_success` échoue avec `TypeError: 'numero_compte' is an invalid keyword argument for CustomerAccount`
- Cause : le modèle `CustomerAccount` n'a pas de champ `numero_compte` — il utilise `type_compte`, `solde_moyen`, etc. (divergence entre le test et le schéma réel)

### 10.3 Difficultés techniques et solutions

| Difficulté | Solution |
|-----------|---------|
| **Fix 1** : `is_active` inexistant sur `scoring_criteria` | Suppression du filtre dans `_load_weights()` |
| **Fix 2** : Normalisation 'ELEVE' → 'ÉLEVÉ' | Mapping explicite dans `_get_category()` |
| **Fix 3** : Faux positifs smurfing | Ajout concentration temporelle (7 jours) + ratio revenus (3×) |
| **Fix 4** : `datetime.utcnow()` déprécié | Remplacement par `datetime.now(timezone.utc)` |
| **Fix 5** : Sécurité null sur relations | `or []` sur `customer.accounts` et `customer.documents` |
| **Fix 6** : Timezone naive vs aware PostgreSQL | Fonction `_naive_utc_now()` et `_strip_tz()` pour compatibilité |
| **Fix 7** : Ancienne PEP non détectée | Suppression du filtre `active=True` — détection de toutes les PEP, puis logique post-mandat 5 ans |
| **Fix 9** : Smurfing near-threshold | Ajout montants entre 80% et 100% du seuil FATF (400k-499k) |
| **Fix 10** : Transactions dupliquées | Nouvelle méthode `_detect_duplicates()` avec fenêtre 24h, arrondi centaine |
| **Fix 11** : Champs étendus dans résultat scoring | Ajout `c5_score` et `smurfing_detected` dans le dict retourné |
| **Perf v1.1** : 10 000 appels `db.flush()` individuels | UUID générés côté client, `db.add_all()` par batch de 100 |
| **Int-1, Int-2, Int-3** : Alertes fines PEP/Smurfing | Intégration des champs étendus dans les routes scoring |

### 10.4 Ce qui n'a pas pu être implémenté

- **Gestion des proches de PEP** : la table `pep_relationships` n'existe pas dans le schéma actuel (prévue roadmap V2)
- **Tests d'intégration complets** : le test `test_create_transaction_success` échoue à cause d'un décalage entre les noms de champs du test et du modèle réel
- **Déploiement production réel** : CI/CD (`.github/workflows/ci.yml`) est vide
- **Authentification multi-facteurs** : seule l'authentification par mot de passe est implémentée
- **Scoring en temps réel** : le scoring est déclenché manuellement ou à la création de transaction, pas en continu

---

## 11. TECHNOLOGIES — Détail d'usage réel

### React 18
Framework frontend. Utilisé avec **lazy loading** (`React.lazy()` + `Suspense`) pour les 10 pages, créant des chunks séparés. Context API pour l'état global (`AuthContext`, `AppContext`). Composants réutilisables (9 composants : Button, Card, Badge, Modal, Table, ScorePanel, Loader, FormInput, Layout) avec props typées. Pas de TypeScript — tout est en JSX.

### FastAPI
Framework backend Python. Utilisé pour exposer 30+ endpoints REST avec documentation automatique Swagger/ReDoc. Dépendances d'injection (`Depends()`) pour l'authentification, les sessions DB et les vérifications de rôles. `APIRouter` pour organiser les routes en 12 modules. Pydantic v2 pour la validation des entrées/sorties. Middleware ASNI pour CORS, logging, rate limiting et gestion d'erreurs.

### PostgreSQL 15
Base de données relationnelle. 14 tables + app_settings. Utilisation extensive des types UUID (clés primaires), JSONB (`detail_json` scores, `permissions` rôles), et contraintes FK avec CASCADE. Indexation sur les colonnes de recherche fréquentes. Schéma de seed avec 15 pays, 6 zones, 6 critères, 3 seuils, 2 rôles.

### SQLAlchemy 2.0
ORM Python. Mode `session` avec `SessionLocal` et injection via `get_db`. Modèles déclaratifs avec relations ORM (`relationship()`) et chargement lazy. Requêtes paramétrées pour la sécurité. Utilisation de `db.flush()` pour obtenir les IDs avant commit, `db.begin_nested()` (savepoints) pour le rescore global par lots. Jointures implicites via relations.

### Alembic
Migration de schéma. 5 versions de migration dans `alembic/versions/` :
1. `8916d3c8118e` — Schéma initial 10 tables
2. `7efd7d148c8d` — Schéma 14 tables
3. `dbe731e3913a` — Ajout alerts, audit_logs, pep_list
4. `f2a63074a8b7` — Server defaults
5. `395261316418` — Suppression colonne `valide` (remplacée par propriété calculée)
6. `77b8481de8a2` — Fix cascade + server defaults

### JWT (JSON Web Token)
Authentification sans état. Créé avec `python-jose` (algorithme HS256), payload `{sub: user_id, role, exp}`. 8h d'expiration. Transmis par en-tête `Authorization: Bearer` ou cookie httpOnly `access_token`. Vérifié dans `dependencies.py` à chaque requête protégée.

### Faker (Python)
Génération de données réalistes. Utilisé avec `Faker('fr_FR')` pour les noms, adresses, téléphones — seedé (`random.seed(42)`, `Faker.seed(42)`) pour la reproductibilité. Listes anthroponymiques béninoises (100 prénoms, 90 noms, 42 villes, 12 départements) pour remplacer les données génériques de Faker.

### pandas & NumPy
Utilisés exclusivement dans le **moteur de scoring** (`scoring.py`) :
- `numpy.array()` pour les montants de transactions (opérations vectorisées)
- `numpy.mean()`, `numpy.std()` pour le calcul du coefficient de variation (détection homogénéité C3)
- Pas de pandas dans ce projet (seulement NumPy)

### ReportLab
Génération PDF côté serveur. Utilisé dans `export_service.py` (1283 lignes) pour :
- **PDF fiche client** (3 pages) : en-tête institutionnel, tableau KYC, score global, barres C1-C6, historique scores, alertes, conformité CENTIF
- **PDF SAR** : déclaration de soupçon avec en-tête CENTIF, infos déclarant, personne concernée, détail alerte, transactions suspectes, signature
- Tables stylisées avec couleurs RiskGuard (bleu marine #1B2A6B, vert #1A7A3C)
- Diagramme en barres horizontal via `reportlab.graphics` (pas de dépendance Recharts côté backend)

### Docker
Conteneurisation complète. **docker-compose.yml** avec 3 services :
- `postgres:15-alpine` : base de données avec healthcheck
- `backend` : construit depuis `Dockerfile` (Python 3.11-slim + requirements.txt), reload en dev
- `frontend` : node:18-alpine, serveur Vite dev
Réseau bridge partagé `scoring_network`. Volume persistant `postgres_data`.

### Recharts
Graphiques côté frontend. Utilisé dans :
- `DashboardPage.jsx` : `PieChart` (répartition risque), `BarChart` (distribution KYC)
- `ScorePanel.jsx` : `RadarChart` (6 critères C1-C6), `BarChart` (contributions)
- `ResponsiveContainer` pour l'adaptation à la taille du conteneur
- Composants mockés dans les tests (jsdom ne supporte pas le SVG)

### Tailwind CSS
Framework CSS utilitaire. Configuration avec polices personnalisées (DM Sans, Sora, JetBrains Mono), ombres (`shadow-card`, `shadow-panel`, `shadow-dialog`). Utilisé sans classes CSS custom (sauf `App.css` minimal). PostCSS avec `tailwindcss` + `autoprefixer`. Responsive sidebar (toggle mobile via AppContext).

---

*Rapport généré automatiquement par analyse du code source — basé uniquement sur le code existant du dépôt `scoring-lbc-ft`. Aucune information externe n'a été ajoutée.*
