# Rapport Complet — RiskGuard | Système de Scoring LBC/FT

**Projet :** RiskGuard — Scoring Automatisé du Risque de Blanchiment de Capitaux et Financement du Terrorisme  
**Contexte :** Institutions de Microfinance (IMF) — Bénin, zone UEMOA  
**Auteurs :** AFFOKPE Magloire (Dev A) & BATAMOUSSI Marcos (Dev B)  
**Superviseur :** M. ASSOGBA Emery — IUT Parakou, 2024-2025  
**Version :** 1.3 — Mai 2026  

---

## Table des matières

1. [Contexte et objectifs](#1-contexte-et-objectifs)
2. [Architecture technique](#2-architecture-technique)
3. [Modèle de données — 14 tables](#3-modèle-de-données--14-tables)
4. [Relations et cardinalités complètes](#4-relations-et-cardinalités-complètes)
5. [Moteur de scoring (C1–C6)](#5-moteur-de-scoring-c1c6)
6. [Détection du smurfing](#6-détection-du-smurfing)
7. [Détection du card testing](#7-détection-du-card-testing)
8. [Génération d'alertes](#8-génération-dalertes)
9. [Flux complets](#9-flux-complets)
10. [Rôles, authentification et sécurité](#10-rôles-authentification-et-sécurité)
11. [Exports et déclaration SAR](#11-exports-et-déclaration-sar)
12. [Déploiement](#12-déploiement)
13. [Tests et couverture](#13-tests-et-couverture)

---

## 1. Contexte et objectifs

### 1.1 Problématique

Les IMF béninoises sont soumises à la **loi n° 2018-16** sur la Lutte contre le Blanchiment de Capitaux et le Financement du Terrorisme (LBC/FT), ainsi qu'aux directives de la **BCEAO** et aux recommandations du **GAFI** (Groupe d'Action Financière). Elles doivent :

- Évaluer le risque LBC/FT de chaque client
- Déclarer les opérations suspectes à la **CENTIF Bénin**
- Conserver une traçabilité complète (audit trail)
- Appliquer une surveillance renforcée aux Personnes Exposées Politiquement (PEP)

### 1.2 Solution

RiskGuard est une plateforme web qui **automatise le scoring du risque** sur une échelle de **0 à 100** selon **6 critères pondérés** (C1–C6), avec :

- Catégorisation automatique : FAIBLE (0-33), MOYEN (34-66), ÉLEVÉ (67-100)
- Détection comportementale avancée : smurfing, card testing, transactions dupliquées
- Génération d'alertes fines
- Export de rapports de soupçon (SAR) au format CENTIF

---

## 2. Architecture technique

```
┌─────────────────────────────────────────────────────────────┐
│                     NAVIGATEUR (Agent/Admin)                 │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   FRONTEND — React + Vite                   │
│  Pages : Login, Dashboard, Clients, Alertes, Admin, Exports │
│  Hébergement : Vercel                                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND — FastAPI (Python 3.11)            │
│  Routers (12) → Services → ORM (SQLAlchemy 2.0)            │
│  Hébergement : Render                                       │
│  Authentification : JWT (HS256, 8h)                         │
│  Rate limiting : slowapi (60 req/min, 5/min login)          │
└─────────────────────────┬───────────────────────────────────┘
                          │ TCP 5432 (SSL)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                BASE DE DONNÉES — PostgreSQL 15               │
│  14 tables, 18 contraintes FK                               │
│  Hébergement : Neon                                         │
│  Pool : 5 connexions max                                    │
└─────────────────────────────────────────────────────────────┘
```

| Couche | Technologie | Version |
|--------|------------|---------|
| Backend | Python / FastAPI / Uvicorn | 3.11 / 0.115 / 0.34 |
| ORM | SQLAlchemy / Alembic | 2.0.36 / 1.14.1 |
| Base de données | PostgreSQL | 15+ |
| Auth | python-jose (JWT) + passlib (bcrypt) | 3.3.0 / 1.7.4 |
| Frontend | React / Vite / Tailwind CSS | 18.2 / 5.0 / 3.3 |
| Graphiques | Recharts | 2.10 |
| PDF | ReportLab | 4.0.9 |
| Tests BE | pytest + httpx TestClient | — |
| Tests FE | Vitest + Testing Library | — |
| Conteneurisation | Docker / docker-compose | — |

---

## 3. Modèle de données — 14 tables

### 3.1 Schéma relationnel complet

```
┌──────────────┐     ┌──────────────┐
│  user_roles  │1──*│    users     │──┐
└──────────────┘     └──────────────┘  │
       │                               │
       │                               │
       │                     ┌─────────┼──────────────┐
       │                     │         │              │
       │                     ▼         ▼              ▼
       │              ┌──────────┐ ┌────────┐ ┌──────────────┐
       │              │ audit_   │ │alerts  │ │ customer_    │
       │              │ logs     │ │clos_par│ │ docs         │
       │              └──────────┘ └────────┘ │ verified_by  │
       │                                      └──────────────┘
       │                                      ┌──────────────┐
       │                                      │ scoring_     │
       │                                      │ criteria     │
       │                                      │ updated_by   │
       │                                      └──────────────┘
       │
       │         ┌────────────┐
       ├─────────┤ customers  │──pep_verified_by──┘
       │         │ (centrale) │
       │         └─────┬──────┘
       │               │
       │     ┌─────────┼────────────┬──────────────┐
       │     │         │            │              │
       │     ▼         ▼            ▼              ▼
       │ ┌────────┐ ┌────────┐ ┌────────┐   ┌──────────┐
       │ │customer│ │customer│ │scores  │   │ alerts   │
       │ │accounts│ │_docs   │ │        │   │(client)  │
       │ └───┬────┘ └────────┘ └────────┘   └──────────┘
       │     │
       │     ▼
       │ ┌────────────┐
       │ │transactions│──countries (origine, destination)
       │ └────────────┘
       │
       │  ┌──────────┐
       └──│risk_zones│──customers.zone_geo
       │  └──────────┘
       │
       │  ┌───────────┐
       └──│countries  │──pep_list.pays
          └───────────┘
```

### 3.2 Descriptif des tables

| # | Table | Rôle | Lignes (test) | PK |
|---|-------|------|--------------|----|
| 1 | `countries` | 15 pays avec flags UEMOA/FATF/frontalier | 15 | Integer |
| 2 | `risk_zones` | 6 zones (CAPITALE, FRONTIÈRE, CONFLIT...) | 6 | Integer |
| 3 | `scoring_criteria` | Poids C1–C6 modifiables par admin | 6 | Integer |
| 4 | `risk_thresholds` | Seuils FAIBLE/MOYEN/ÉLEVÉ | 3 | Integer |
| 5 | `user_roles` | Rôles : admin, compliance_officer | 2 | Integer |
| 6 | `users` | Utilisateurs authentifiés | ~3 | UUID |
| 7 | **`customers`** | **Table centrale — 23 attributs** | ~503 | UUID |
| 8 | `customers_docs` | Documents KYC des clients | ~1 000 | UUID |
| 9 | `customer_accounts` | Comptes bancaires | ~503 | UUID |
| 10 | `transactions` | Transactions financières | ~12 000 | UUID |
| 11 | `scores` | Historique des scores | ~1 500 | UUID |
| 12 | `alerts` | Alertes LBC/FT | ~20 | UUID |
| 13 | `audit_logs` | Journal d'audit | Variable | UUID |
| 14 | `pep_list` | Liste des PEP | ~15 | UUID |

### 3.3 Détail des colonnes de `customers` (table centrale)

```sql
customers (
    id                  UUID PRIMARY KEY DEFAULT uuid4(),
    -- Identité
    nom                 VARCHAR(100) NOT NULL,
    prenom              VARCHAR(100) NOT NULL,
    date_naissance      DATE,
    phone               VARCHAR(20) UNIQUE,
    email               VARCHAR(150) UNIQUE,
    -- Profession
    profession_code     VARCHAR(50),        -- 'COMMER_TRANSFR', 'AGRI_MARAICH'...
    profession_name     VARCHAR(150),
    profession_risk     VARCHAR(10),        -- 'LOW', 'MEDIUM', 'HIGH'
    revenus_declares    NUMERIC(15,2),
    -- Localisation
    city                VARCHAR(100),
    region              VARCHAR(100),
    latitude            VARCHAR(20),
    longitude           VARCHAR(20),
    zone_geo            INTEGER → risk_zones.id,
    pays                INTEGER → countries.id,
    -- LBC/FT
    statut_pep          BOOLEAN DEFAULT FALSE,
    pep_verified_by     UUID → users.id,        -- ← FK vers users
    kyc_level           VARCHAR(10) DEFAULT 'LOW',
    kyc_completion      INTEGER DEFAULT 0,
    status              VARCHAR(20) DEFAULT 'ACTIVE',
    -- Audit temporel
    date_creation       DATETIME DEFAULT now(),
    updated_at          DATETIME DEFAULT now()
)
```

---

## 4. Relations et cardinalités complètes

### 4.1 Tableau des 18 contraintes FK

| # | Source | Colonne FK | Cible | Comportement DELETE |
|---|--------|-----------|-------|-------------------|
| 1 | `users` | `role_id` | `user_roles.id` | RESTRICT |
| 2 | **`customers`** | **`pep_verified_by`** | **`users.id`** | SET NULL |
| 3 | `customers` | `zone_geo` | `risk_zones.id` | RESTRICT |
| 4 | `customers` | `pays` | `countries.id` | RESTRICT |
| 5 | `customers_docs` | `client_id` | `customers.id` | **CASCADE** |
| 6 | `customers_docs` | `verified_by` | `users.id` | SET NULL |
| 7 | `customer_accounts` | `client_id` | `customers.id` | **CASCADE** |
| 8 | `transactions` | `compte_id` | `customer_accounts.id` | **CASCADE** |
| 9 | `transactions` | `origine_pays_id` | `countries.id` | RESTRICT |
| 10 | `transactions` | `destination_pays_id` | `countries.id` | RESTRICT |
| 11 | `scores` | `client_id` | `customers.id` | RESTRICT |
| 12 | `alerts` | `client_id` | `customers.id` | **CASCADE** |
| 13 | `alerts` | `clos_par` | `users.id` | SET NULL |
| 14 | `audit_logs` | `user_id` | `users.id` | RESTRICT |
| 15 | `audit_logs` | `client_id` | `customers.id` | SET NULL |
| 16 | `pep_list` | `pays` | `countries.id` | RESTRICT |
| 17 | `scoring_criteria` | `updated_by` | `users.id` | SET NULL |
| 18 | `scores` | `calcule_par` | — | VARCHAR (pas FK) |

### 4.2 Relations entre `users` et `customers`

Il existe **5 chemins** qui relient les tables `users` et `customers` :

```
Chemin 1 (FK directe) :
    users.id ──── customers.pep_verified_by
    Cardinalité : User 1 ― 0..* Customer
    Sens : "Qui a vérifié le statut PEP du client ?"

Chemin 2 (via audit_logs) :
    users.id ──── audit_logs.user_id
    audit_logs.client_id ──── customers.id
    Cardinalité : User 1..* ― 0..* Customer
    Sens : "Quel utilisateur a effectué quelle action sur quel client ?"

Chemin 3 (via customers_docs) :
    users.id ──── customers_docs.verified_by
    customers_docs.client_id ──── customers.id
    Cardinalité : User 0..* ― 0..* Customer
    Sens : "Qui a vérifié les documents KYC du client ?"

Chemin 4 (via alerts) :
    users.id ──── alerts.clos_par
    alerts.client_id ──── customers.id
    Cardinalité : User 0..* ― 0..* Customer
    Sens : "Qui a clôturé l'alerte du client ?"

Chemin 5 (via scoring_criteria — indirect) :
    users.id ──── scoring_criteria.updated_by
    (pas de lien direct vers customers)
    Sens : "Qui a modifié les poids de scoring ?"
```

### 4.3 Diagramme de classes — Associations

```
┌──────────┐  1              0..*  ┌──────────┐
│ UserRole │───────────────────────│   User   │
└──────────┘                       └────┬─────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │1                  │1                  │1
                    │                   │                   │
              0..*  │ 0..*         0..* │             0..*  │
          ┌─────────┴──┐   ┌───────────┴──┐  ┌─────────────┴──┐
          │ AuditLog   │   │ CustomerDoc  │  │    Alert       │
          ├────────────┤   ├──────────────┤  ├───────────────┤
          │* user_id   │   │* verified_by │  │* clos_par     │
          │* client_id │   │* client_id   │  │* client_id    │
          └────────────┘   └──────────────┘  └───────────────┘
               0..* │          0..* │              0..* │
                    │               │                   │
                    └───────────────┼───────────────────┘
                                    │1
                             ┌──────┴──────┐
                   0..* ─────│  Customer   │──── 0..1 ────┐
                    ┌───────│ (centrale)  │──── 1 ────┐   │
                    │       └─────────────┘           │   │
                    │1                                │   │
              0..*  │                          0..*   │   │
          ┌─────────┴──┐                    ┌─────────┴┐  │
          │ Customer   │                    │  Score    │  │
          │ Account    │                    │* client_id│  │
          ├────────────┤                    │* is_cur-  │  │
          │* client_id │                    │  rent     │  │
          └─────┬──────┘                    └───────────┘  │
                │1                                         │
          0..*  │                                          │
          ┌─────┴──────┐              0..* ┌───────────┐   │
          │Transaction │──────────────────│  Country   │   │
          │* compte_id │    (origine/     ├───────────┤   │
          │* origine_  │    dest.)        │is_fatf,   │   │
          │  pays_id   │                  │is_border, │   │
          │* destina-  │                  │is_uemoa   │   │
          │  tion_pays │                  └─────┬─────┘   │
          └────────────┘                        │        1│
                                          0..*  │         │
                                          ┌─────┴─────┐   │
                                          │ PepEntry  │   │
                                          └───────────┘   │
                                                          │
                                           ┌───────────┐  │
                                           │ RiskZone  │──┘
                                           │risk_level │
                                           └───────────┘
```

---

## 5. Moteur de scoring (C1–C6)

Le fichier `backend/app/services/scoring.py` (870 lignes) implémente le cœur métier.

### 5.1 Principe général

```
Score global = (C1 × poids_C1) + (C2 × poids_C2) + ... + (C6 × poids_C6)

Poids par défaut : C1=20%, C2=20%, C3=25%, C4=10%, C5=15%, C6=10%
Total = 100% → Score 0-100 arrondi
```

Les poids sont stockés en base dans `scoring_criteria` et **modifiables** via l'interface admin.

### 5.2 Critère C1 — Profil professionnel (20%)

```
profession_risk = 'LOW'    → note 10/100
                = 'MEDIUM'  → note 35/100
                = 'HIGH'    → note 65/100
                = non renseigné → note 85/100
```

Majorations :
- Revenus non déclarés + profession non à risque → +10
- Revenus > 5M FCFA + profession LOW → +15

### 5.3 Critère C2 — Zone géographique (20%)

```
risk_level = 'FAIBLE'      → note 10/100 (ex: CAPITALE)
           = 'MOYEN'       → note 35/100 (ex: URBAINE)
           = 'ELEVE'       → note 65/100 (ex: FRONTIERE)
           = 'TRES_ELEVE'  → note 88/100 (ex: CONFLIT)
```

Surcharges pays :
- Pays FATF (liste noire) → note min 70
- Pays frontalier du Bénin → note min 55
- Pays UEMOA → note max 40

### 5.4 Critère C3 — Transactions (25%) — le plus important

Analyse des 90 derniers jours avec **7 détecteurs** :

| # | Détection | Seuil | Pénalité C3 |
|---|-----------|-------|------------|
| a | Volume total / (revenu × 3) > 5 | ratio > 5 | note ≥ 80 |
| a | Volume total / (revenu × 3) > 3 | ratio > 3 | note ≥ 60 |
| a | Volume total / (revenu × 3) > 1.5 | ratio > 1.5 | note ≥ 40 |
| b | Transactions par jour > 5 | tx/jour > 5 | note ≥ 70 |
| b | Transactions par jour > 2 | tx/jour > 2 | note ≥ 45 |
| c | Retraits cash > 10 en 90j | > 10 retraits | note ≥ 65 |
| c | Retraits cash > 5 en 90j | > 5 retraits | note ≥ 40 |
| **d** | **Smurfing** | **voir §6** | **note ≥ 85** |
| e | > 50% transactions vers pays risque | ratio > 50% | note ≥ 75 |
| e | > 20% transactions vers pays risque | ratio > 20% | note ≥ 55 |
| **f** | **Card testing** | **voir §7** | **note ≥ 45 ou 75** |
| **g** | **Transactions dupliquées** | **≥ 3 groupes** | **note ≥ 60** |
| **g** | **Transactions dupliquées** | **≥ 1 groupe** | **note ≥ 40** |

### 5.5 Critère C4 — Ancienneté (10%)

```
Relation > 3 ans  → note 10/100
Relation 1-3 ans  → note 35/100
Relation 6-12 mois → note 60/100
Relation < 6 mois  → note 75/100
```

### 5.6 Critère C5 — Statut PEP (15%) — Conforme GAFI R.12

```
PEP active (statut_pep=True OU pep_list.active=True)  → 100/100
Ancienne PEP (pep_list.active=False, < 5 ans)         →  50/100
Aucune correspondance                                  →   0/100
```

La recherche s'effectue par nom/prénom dans `pep_list`. L'ordre est trié par `active DESC` pour privilégier les PEP actives en cas de doublon.

### 5.7 Critère C6 — Cohérence KYC (10%)

Points vérifiés :
- **Documents** : ratio d'invalides (> 50% → 85/100, > 0 → 55/100)
- **Expiration** : documents expirant dans 60 jours → 30/100
- **Cohérence revenus** : moyenne transactions / revenu mensuel > 10 → 75/100
- **Complétude KYC** : < 30% → 80/100, < 60% → 40/100

---

## 6. Détection du smurfing

Méthode : `_detect_smurfing()` dans `scoring.py:485-569`.

### 6.1 Principe

Le smurfing (fractionnement) consiste à diviser une somme importante en plusieurs petites transactions pour **contourner le seuil déclaratif FATF de 500 000 FCFA**.

### 6.2 Transactions suspectes (OR)

Deux familles de transactions sont marquées comme suspectes :

| Type | Condition | Exemples |
|------|-----------|----------|
| **Montant rond classique** | Multiple de 10 000 ET < 500 000 | 10k, 50k, 100k, 250k, 490k |
| **Near-threshold** | Entre 400 000 (80%) et 500 000 (100%) | 495 000, 498 000, 499 900 |

### 6.3 Conditions cumulatives (AND)

Les 3 conditions suivantes doivent être **toutes vraies** :

```
1. Au moins 3 transactions suspectes        (_SMURFING_MIN_COUNT = 3)
2. Ces transactions concentrées sur ≤ 7 jours (_SMURFING_WINDOW_DAYS = 7)
3. Total suspect ≥ 3 × revenus mensuels      (_SMURFING_REVENUE_MULT = 3.0)
```

### 6.4 Exemples concrets

#### Cas 1 : Petit commerçant (revenu 100 000 FCFA/mois)

Transactions sur 5 jours :
- 90 000 FCFA → montant rond (multiple de 10 000) ✓ suspect
- 95 000 FCFA → montant rond ✓ suspect
- 95 000 FCFA → montant rond ✓ suspect
- 80 000 FCFA → montant rond ✓ suspect

**Analyse :**
- 4 transactions suspectes ≥ 3 ✓
- Span 5 jours ≤ 7 ✓
- Total = 360 000 ≥ 3 × 100 000 = 300 000 ✓

→ **Smurfing détecté** — note C3 = 85, alerte SMURFING créée

#### Cas 2 : Agent immobilier (revenu 2 000 000 FCFA/mois)

Transactions sur 3 jours :
- 490 000 FCFA → near-threshold ✓ suspect
- 495 000 FCFA → near-threshold ✓ suspect
- 480 000 FCFA → near-threshold ✓ suspect
- 498 000 FCFA → near-threshold ✓ suspect

**Analyse :**
- 4 transactions suspectes ≥ 3 ✓
- Span 3 jours ≤ 7 ✓
- Total = 1 963 000 ≥ 3 × 2 000 000 = 6 000 000 ✗

→ **Smurfing NON détecté** (condition 3 non remplie — revenus trop élevés par rapport aux montants)

#### Cas 3 : Fonctionnaire (revenu 350 000 FCFA/mois)

Transactions sur 2 jours :
- 100 000 FCFA → rond ✓ suspect
- 450 000 FCFA → near-threshold ✓ suspect
- 300 000 FCFA → rond ✓ suspect

**Analyse :**
- 3 transactions suspectes ≥ 3 ✓
- Span 2 jours ≤ 7 ✓
- Total = 850 000 ≥ 3 × 350 000 = 1 050 000 ✗

→ **Smurfing NON détecté** (juste en dessous du seuil)

---

## 7. Détection du card testing

Méthode intégrée dans `_score_c3()` — lignes 438-465.

### 7.1 Principe

Le card testing est une technique de fraude où un attaquant teste une carte volée en effectuant de **très petits paiements** pour vérifier sa validité avant de l'utiliser pour des montants plus importants.

### 7.2 Détection

```python
CARD_TESTING_MAX_AMOUNT = 1_000    # XOF : seuil micro-transaction
CARD_TESTING_ALERT_COUNT = 5       # nb min pour alerte forte
CARD_TESTING_WARN_COUNT = 2        # nb min pour alerte modérée
```

Une transaction est marquée comme micro-transaction carte si :
```python
canal contient "CARTE" ET 0 < montant ≤ 1_000 XOF
```

### 7.3 Seuils de déclenchement

| Micro-tx carte | Impact |
|----------------|--------|
| ≥ 5 | Alerte **CARD_TESTING** + note C3 ≥ 75 |
| ≥ 2 | Note C3 ≥ 45 (pas d'alerte formelle) |
| < 2 | Aucun impact |

---

## 8. Génération d'alertes

Fichier : `backend/app/services/alert_service.py` (322 lignes).

### 8.1 Types d'alertes

| Type | Déclencheur | Condition |
|------|------------|-----------|
| `SCORE_ELEVE` | Score global | ≥ 67 |
| `PEP_ACTIF` | PEP en fonction | C5 = 100 |
| `PEP_ANCIEN` | Ancienne PEP | C5 = 50 |
| **`SMURFING`** | **Fractionnement** | **smurfing_detected = true** |
| `CARD_TESTING` | Micro-tx carte | ≥ 5 micro-tx |
| `KYC_INCOMPLET` | Dossier incomplet | complétude < 40% |

### 8.2 Anti-doublon

```python
def has_open_alert(db, customer_id, alert_type):
    # Vérifie si une alerte OPEN du même type existe déjà
    # Si oui, on ne crée pas de doublon
```

Le rescore automatique utilise `skip_if_open=True` pour éviter les doublons.

### 8.3 Indépendance des alertes

**Point critique :** l'alerte `SMURFING` est créée **indépendamment** du score global. Un client peut avoir un score de 30 (FAIBLE) et recevoir une alerte SMURFING si le fractionnement est détecté.

```python
# transactions.py:121-122
if result["smurfing_detected"]:
    create_smurfing_alert_if_needed(db, customer_id, skip_if_open=True)
```

---

## 9. Flux complets

### 9.1 Création d'un client

```
Agent → Frontend : Remplit le formulaire (stepper 3 étapes)
    → Backend POST /api/clients
        → Validation des champs (phone/email uniques)
        → Insertion dans customers
        → Calcul automatique du score (ScoringEngine)
            → Sauvegarde du score
            → Création des alertes si nécessaire (PEP, KYC)
        → Log dans audit_logs
    → Frontend : Redirection vers la fiche client
```

### 9.2 Enregistrement d'une transaction + auto-rescore

```
Agent → Frontend : Saisit la transaction
    → Backend POST /customers/{id}/transactions
        → Insertion dans transactions
        → Auto-rescore (ScoringEngine.calculate_score)
            → Archive l'ancien score (is_current=false)
            → Sauvegarde le nouveau score
            → Crée les alertes si nécessaire :
                • SCORE_ELEVE si score ≥ 67
                • SMURFING si smurfing détecté
                • CARD_TESTING si ≥ 5 micro-tx carte
                • PEP_ACTIF/PEP_ANCIEN si PEP détectée
                • KYC_INCOMPLET si complétude < 40%
        → Log dans audit_logs (action SCORING_RESCORE)
    → Frontend : Affiche le nouveau score + alertes
```

### 9.3 Cycle de vie d'une alerte

```
Génération auto (scoring) → Statut OPEN
    ↓
Agent examine l'alerte → Statut UNDER_REVIEW
    ↓
Deux possibilités :
    ├── Décision : classement sans suite → Statut CLOSED, sar=false
    └── Décision : suspicion confirmée → Télécharge SAR PDF
                                        → Statut CLOSED, sar=true
```

---

## 10. Rôles, authentification et sécurité

### 10.1 Rôles

| Rôle | Droits |
|------|--------|
| **admin** | Configuration des poids C1-C6, seuils, gestion des utilisateurs, import CSV PEP, consultation des logs d'audit, toutes les opérations métier |
| **compliance_officer** | Gestion des clients, transactions, scoring, alertes, exports — pas d'accès à la configuration système |

Les permissions sont stockées dans `user_roles.permissions` (JSONB) et vérifiées par `app/auth/permissions.py`.

### 10.2 Authentification

- **Mécanisme** : JWT (JSON Web Token)
- **Algorithme** : HS256
- **Expiration** : 480 minutes (8 heures)
- **Hash mot de passe** : bcrypt (via passlib)
- **Rate limiting login** : 5 tentatives/min/IP

### 10.3 Middleware

- Logging HTTP (toutes les requêtes)
- Gestion globale des erreurs (ValidationError, SQLAlchemyError, exceptions génériques)
- Rate limiting global (60 requêtes/min)

---

## 11. Exports et déclaration SAR

### 11.1 Types d'exports

| Export | Format | Contenu |
|--------|--------|---------|
| Fiche client | PDF | Profil complet, score, historique, documents |
| Transactions | CSV | Liste des transactions avec filtres |
| Rapport de soupçon (SAR) | PDF | Format CENTIF Bénin |

### 11.2 Rapport SAR

Le SAR (Suspicious Activity Report) est un PDF généré via ReportLab, contenant :
- Identité du client
- Description des faits suspects
- Type d'alerte (SCORE_ELEVE, SMURFING, CARD_TESTING, PEP)
- Score et catégorie de risque
- Décision de l'agent

---

## 12. Déploiement

### 12.1 Infrastructure

| Service | Rôle | URL |
|---------|------|-----|
| **Render** | Backend FastAPI | Python 3.11, gunicorn + uvicorn |
| **Neon** | Base PostgreSQL 15 | SSL require, pool 5 connexions |
| **Vercel** | Frontend React SPA | Static build, rewrites SPA |
| **Docker** | Développement local | docker-compose |

### 12.2 Variables d'environnement

```
# Backend (.env)
DATABASE_URL=postgresql://user:pass@host:5432/riskguard?sslmode=require
SECRET_KEY=<openssl rand -hex 32>
DEBUG=false
CORS_ORIGINS=http://localhost:5173,https://riskguard.vercel.app
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5

# Frontend (.env)
VITE_API_URL=https://riskguard-api.onrender.com
VITE_USE_MOCKS=false
```

### 12.3 Base de données (Alembic)

4 migrations gèrent le schéma :
1. `v1_init` — Création des 14 tables avec contraintes FK
2. `v2_alerts_audit_pep` — Ajout des types d'alertes, index
3. `v3_server_defaults` — Valeurs par défaut des colonnes
4. `v4_column_removal` — Nettoyage des colonnes obsolètes

---

## 13. Tests et couverture

### 13.1 Backend (pytest)

| Catégorie | Fichiers | Description |
|-----------|----------|-------------|
| Unitaires | `tests/scoring/` | Tests du moteur de scoring (C1-C6, smurfing, card testing) |
| Unitaires | `tests/auth/` | Authentification, JWT, permissions |
| Unitaires | `tests/models/` | Validation des modèles ORM |
| Integration | `tests/endpoints/` | Tests des routes API |
| Integration | `tests/exports/` | Génération PDF/CSV |
| Integration | `tests/database/` | CRUD, migrations Alembic |
| Workflow | `tests/workflow/` | Scénarios complets |

Les tests utilisent une base SQLite in-memory avec seed des données de référence.

### 13.2 Frontend (Vitest + Testing Library)

- Tests des composants React
- Tests des hooks personnalisés
- Tests des services API

---

## Annexe A — Fichiers clés du projet

```
backend/
├── app/
│   ├── main.py                    # Point d'entrée FastAPI
│   ├── config.py                  # Configuration (Pydantic Settings)
│   ├── models/                    # 14 modèles ORM SQLAlchemy
│   │   ├── customers.py           # Table centrale (client)
│   │   ├── users.py               # Utilisateurs
│   │   ├── transactions.py        # Transactions financières
│   │   ├── alerts.py              # Alertes LBC/FT
│   │   ├── scores.py              # Historique des scores
│   │   ├── audit_logs.py          # Journal d'audit
│   │   ├── pep_list.py            # Liste des PEP
│   │   ├── countries.py           # Pays
│   │   ├── risk_zones.py          # Zones géographiques
│   │   ├── customer_accounts.py   # Comptes clients
│   │   ├── customer_docs.py       # Documents KYC
│   │   ├── user_roles.py          # Rôles utilisateur
│   │   ├── scoring_criteria.py    # Poids C1-C6
│   │   └── risk_thresholds.py     # Seuils de risque
│   ├── routers/                   # 12 points d'API
│   │   ├── auth.py                # Authentification
│   │   ├── customers.py           # CRUD clients
│   │   ├── transactions.py        # Transactions + auto-rescore
│   │   ├── scoring.py             # Scoring manuel + batch
│   │   ├── alerts.py              # Gestion des alertes
│   │   ├── dashboard.py           # KPIs tableau de bord
│   │   ├── admin.py               # Administration
│   │   ├── exports.py             # PDF/CSV/SAR
│   │   └── ...
│   ├── services/
│   │   ├── scoring.py             # Moteur de scoring (870 lignes)
│   │   └── alert_service.py       # Création d'alertes
│   ├── auth/                      # JWT, permissions
│   └── middleware/                # Logging, erreurs
├── scripts/
│   ├── seed_db.py                 # Données de référence
│   └── generate_fake_data.py      # 500 clients de test
├── alembic/                       # Migrations DB
└── tests/                         # Tests automatisés

frontend/
├── src/
│   ├── pages/                     # 9 pages React
│   ├── components/                # 10 composants réutilisables
│   ├── services/                  # 8 services API (Axios)
│   ├── context/                   # AuthContext, AppContext
│   ├── hooks/                     # useAuth, useFetch, etc.
│   └── theme/                     # Design tokens
├── package.json
└── vite.config.js
```

---

## Annexe B — Recommandations d'amélioration

### B.1 Court terme

1. **Alerte SMURFING pour les gros revenus** — Ajuster `_SMURFING_REVENUE_MULT` (3.0 → 1.5) ou le rendre dynamique selon le profil
2. **Index manquant** — Ajouter CASCADE DELETE sur `scores.client_id`
3. **Notification temps réel** — WebSocket ou polling dashboard pour alertes critiques
4. **Validation téléphone** — Format +229 XX XX XX XX (Bénin)

### B.2 Moyen terme

1. **Détection de réseau** — Analyse des liens entre clients (même téléphone, même adresse IP)
2. **Proches de PEP** — Table `pep_relationships` pour couvrir GAFI R.12 (famille et associés)
3. **Machine Learning** — Modèle supervisé pour affiner les poids C1-C6
4. **API bancaire** — Intégration avec les systèmes core banking des IMF

### B.3 Long terme

1. **Géo-scoring temps réel** — Analyse GPS des transactions
2. **Cross-IMF** — Partage anonymisé d'indicateurs entre institutions
3. **Déclaration CENTIF automatisée** — API directe vers la CENTIF Bénin

---

*Document généré le 22 mai 2026 — RiskGuard v1.3 — IUT Parakou, département GEA*
