# Rapport Complet — RiskGuard | Système de Scoring LBC/FT

**Projet :** RiskGuard — Scoring Automatisé du Risque de Blanchiment de Capitaux et Financement du Terrorisme  
**Contexte :** Institutions de Microfinance (IMF) — Bénin, zone UEMOA  
**Auteurs :** AFFOKPE Magloire (Dev A) & BATAMOUSSI Marcos (Dev B)  
**Superviseur :** M. ASSOGBA Emery — IUT Parakou, 2024-2025  
**Version :** 1.3 — Mai 2026  

---

## Table des matières

1. [Contexte et objectifs](#1-contexte-et-objectifs)
   - [1.3 Cycle de vie du client](#13-cycle-de-vie-du-client-sur-la-plateforme)
2. [Architecture technique](#2-architecture-technique)
3. [Modèle de données — 14 tables](#3-modèle-de-données--14-tables)
4. [Relations et cardinalités complètes](#4-relations-et-cardinalités-complètes)
5. [Moteur de scoring (C1–C6)](#5-moteur-de-scoring-c1c6)
6. [Détection du smurfing](#6-détection-du-smurfing)
7. [Transactions dupliquées / replay](#7-transactions-dupliquées--replay)
8. [Génération d'alertes](#8-génération-dalertes)
9. [Flux complets](#9-flux-complets)
10. [Rôles, authentification et sécurité](#10-rôles-authentification-et-sécurité)
11. [Exports et déclaration SAR](#11-exports-et-déclaration-sar)
12. [Déploiement](#12-déploiement)
13. [Tests et couverture](#13-tests-et-couverture)
- [Annexe C — Observations techniques](#annexe-c--observations-techniques)

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
- Détection comportementale avancée : smurfing, transactions dupliquées
- Génération d'alertes fines
- Export de rapports de soupçon (SAR) au format CENTIF

### 1.3 Cycle de vie du client sur la plateforme

**Création du client :** L'agent saisit les informations personnelles (nom, prénom, profession, revenus, adresse, zone géographique). Le système **calcule automatiquement le score de risque** dès la création.

**Ajout des documents KYC :** CNI, passeport, permis, etc. Le système vérifie la validité (date d'expiration) et met à jour le taux de complétude KYC.

**Ouverture de comptes :** Comptes COURANT ou EPARGNE liés au client.

**Enregistrement des transactions :** Dépôts, retraits, virements, paiements avec montant, date, canal et pays source/destination. **Chaque transaction déclenche un rescore automatique.**

**Génération d'alertes :** Si le score dépasse un seuil ou si des comportements suspects sont détectés (PEP, smurfing), une alerte est créée pour investigation.

**Déclaration SAR :** L'agent peut exporter un rapport de soupçon au format CENTIF Bénin.

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

### 2.1 Application React (10 pages)

| Page | Rôle |
|------|------|
| **LoginPage** | Authentification avec validation, eye toggle, branding |
| **DashboardPage** | KPIs, graphiques (risque/KYC), 5 dernières alertes, PEP |
| **ClientsListPage** | Tableau paginé, filtres (KYC, statut, PEP), recherche |
| **ClientDetailPage** | 4 onglets (KYC, Scoring, Transactions, Alertes), exports PDF/CSV |
| **AddClientPage** | Assistant 3 étapes (identité → adresse → documents) |
| **EditClientPage** | Modification client avec pré-remplissage |
| **AlertsPage** | Alertes filtrables, mise à jour statut, création, SAR PDF |
| **ExportsPage** | Recherche auto-complétion, exports PDF/CSV |
| **ScorePage** | Visualisation standalone du score |
| **AdminPage** | 7 onglets admin (critères, seuils, paramètres, pays, PEP, utilisateurs, audit logs) |

**Dashboard** — Cartes KPI (total clients, PEP, alertes ouvertes, répartition risque), PieChart répartition risque, BarChart distribution KYC, tableau 5 dernières alertes, liste PEP actifs.

**Fiche client** — 4 onglets : KYC (identité, profession, zone, pays, PEP, complétion), Scoring (jauge SVG, RadarChart C1-C6, historique), Transactions (tableau paginé), Alertes (création, mise à jour, export SAR).

Composants réutilisables : Button, Card, Badge, Modal, Table, ScorePanel, Loader, FormInput, Layout. Librairies : Recharts, Axios (9 services API).

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
| 11 | `scores` | `client_id` | `customers.id` | **CASCADE** (migration abc123456789) |
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

Le fichier `backend/app/services/scoring.py` (932 lignes) implémente le cœur métier.

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

→ **Smurfing détecté** — note C3 = 85, alerte SMURFING_DETECTE créée

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

## 7. Transactions dupliquées / replay

Méthode `_detect_duplicates()` dans `_score_c3()`.

Détecte les groupes de transactions avec le même montant arrondi (tolérance
100 XOF pour les frais) vers la même destination, dans une fenêtre de 24 h.

| Nb groupes suspects (24 h) | Note C3 minimale |
|---------------------------|------------------|
| ≥ 3                       | 60               |
| ≥ 1                       | 40               |

---

## 8. Génération d'alertes

Fichier : `backend/app/services/alert_service.py` (297 lignes).

RiskGuard génère **6 types d'alertes** distincts, chacun correspondant à un signal de risque LBC/FT spécifique.
Les alertes sont créées automatiquement par le moteur de scoring ou par les services de détection,
et peuvent aussi être créées manuellement par un agent compliance.

### 8.1 Carte d'identité des 6 alertes

| # | Type | Code | Déclencheur | Règle métier | Router déclencheur |
|---|------|------|------------|-------------|-------------------|
| 1 | **Score élevé** | `SCORE_ELEVE` | Score global ≥ 67 (seuil ÉLEVÉ) | Un score de risque LBC/FT ≥ 67/100 déclenche une vigilance maximale avec obligation de déclaration SAR à la CENTIF | `routers/scoring.py:275`, `routers/transactions.py:133` |
| 2 | **PEP détectée** | `PEP_DETECTE` | Note C5 ≥ 50 (PEP active=100, ancienne PEP=50) | Conforme à la recommandation GAFI R.12. Une PEP active ou ancienne (< 5 ans post-mandat) nécessite une vigilance renforcée sur l'origine des fonds | `routers/scoring.py:181`, `routers/customers.py:151` |
| 3 | **Smurfing/fractionnement** | `SMURFING_DETECTE` | `smurfing_detected = True` (détection dans `scoring.py:455`) | Fractionnement de sommes importantes en transactions < 500 000 XOF pour contourner le seuil déclaratif FATF. L'alerte est indépendante du score global | `routers/scoring.py:189`, `routers/transactions.py:135` |
| 4 | **KYC incomplet** | `KYC_INCOMPLET` | Taux de complétion KYC < 40% | Un dossier KYC insuffisant (LOW selon `determine_kyc_level`) empêche l'évaluation correcte du risque. L'agent doit relancer le client pour compléter son dossier | `routers/customers.py:147`, `routers/transactions.py:139` |
| 5 | **Seuil dépassé** | `SEUIL_DEPASSE` | Cumul 30j > seuil configurable (`SEUIL_MONETAIRE` ou `SEUIL_ESPECES`) | Détection des dépassements de seuils monétaires dans la fenêtre de cumul configurable (défaut 30 jours). Deux sous-types : toutes opérations et espèces (GUICHET/ATM) | `routers/transactions.py:165,189` |
| 6 | **Bénéficiaire groupement** | `BENEFICIAIRE_GROUPEMENT` | Bénéficiaire commun à ≥ 2 clients ou ≥ 5 transactions ou montant ≥ 5M FCFA | Détection des transferts groupés vers un même bénéficiaire — indicateur de montage financier suspect ou de rabatteur | `services/beneficiaire_service.py:113` |

### 8.2 Règles de déclenchement détaillées

#### 8.2.1 `SCORE_ELEVE` — Score de risque élevé
- **Déclencheur :** `global_score ≥ 67`
- **Créée par :** `create_score_alert_if_needed()` dans `alert_service.py:149`
- **Appelée depuis :**
  - Scoring initial : `POST /scoring`
  - Rescore manuel : `POST /scoring/rescore`
  - Auto-rescore transaction : `POST /customers/{id}/transactions`
  - Rescore global : `POST /scoring/rescore-all`
- **Décision typique :** La déclaration SAR à la CENTIF est obligatoire pour tout score ÉLEVÉ
- **Indépendance :** Cette alerte est créée **quelle que soit** l'origine du score (scoring initial, rescore manuel, auto-rescore transactionnel)

#### 8.2.2 `PEP_DETECTE` — Personne Exposée Politiquement
- **Déclencheur :** `C5 ≥ 50`, où :
  - `C5 = 100` → PEP active (`statut_pep=True` ou nom présent dans `pep_list` avec `active=True`)
  - `C5 = 50` → Ancienne PEP (dans `pep_list` avec `active=False`, `date_fin` < 5 ans)
  - `C5 = 0` → Aucune correspondance PEP
- **Conformité GAFI R.12 :** La vigilance renforcée s'applique 5 ans après la fin du mandat
- **Créée par :** `create_pep_alert_if_needed()` dans `alert_service.py:186`
- **Appelée depuis :**
  - Scoring et rescore : `routers/scoring.py:181`
  - Création client (si `statut_pep=True`) : `routers/customers.py:151`
  - Auto-rescore transaction : `routers/transactions.py:134`
- **Décision typique :** Vérification renforcée de l'origine des fonds, justification de la relation commerciale

#### 8.2.3 `SMURFING_DETECTE` — Fractionnement de transactions
- **Déclencheur :** `smurfing_detected = True` retourné par `ScoringEngine._detect_smurfing()`
- **Conditions cumulatives :**
  1. Au moins 3 transactions suspectes (montant rond < 500k XOF ou near-threshold 80%-100%)
  2. Transactions concentrées sur ≤ 7 jours
  3. Total des suspects ≥ 3× revenus mensuels déclarés
- **Indépendance du score global :** Point critique — un client peut avoir un score FAIBLE (ex: 30) mais recevoir une alerte SMURFING_DETECTE si le fractionnement est détecté. L'investigation est obligatoire indépendamment du score.
- **Créée par :** `create_smurfing_alert_if_needed()` dans `alert_service.py:229`
- **Appelée depuis :** scoring engine, auto-rescore transaction
- **Décision typique :** Analyse des flux, demande de justificatifs sur l'origine des fonds fragmentés

#### 8.2.4 `KYC_INCOMPLET` — Dossier d'identification incomplet
- **Déclencheur :** `kyc_completion < 40%` (niveau `LOW` selon `determine_kyc_level`)
- **Calcul du taux de complétion :** `compute_kyc_completion()` dans `customer_service.py:4`
  - 9 champs obligatoires : date_naissance, phone, email, profession_code, revenus_declares, city, region, zone_geo, pays
  - Chaque champ rempli = +11.1 points
  - Bonus +10 si documents valides présents
- **Recalcul :** À chaque création ou modification client, et à chaque ajout de document
- **Créée par :** `create_kyc_alert_if_needed()` dans `alert_service.py:262`
- **Appelée depuis :**
  - Création client : `routers/customers.py:147`
  - Modification client : `routers/customers.py:224`
  - Auto-rescore transaction : `routers/transactions.py:139`
- **Décision typique :** Relance du client pour fournir les pièces manquantes (CNI, justificatif de domicile, etc.)

#### 8.2.5 `SEUIL_DEPASSE` — Dépassement de seuil monétaire
- **Déclencheur :** Cumul des transactions sur `FENETRE_CUMUL_JOURS` (défaut 30 jours) ≥ seuil configurable
- **Deux sous-types :**
  - **Toutes opérations** : `SEUIL_MONETAIRE` (défaut 10 000 000 XOF)
  - **Espèces uniquement** : `SEUIL_ESPECES` (défaut 3 000 000 XOF) — dépôts via GUICHET ou ATM
- **Paramètres configurables :** via l'interface admin (`PUT /settings`) ou la table `app_settings`
- **Créée par :** `create_if_not_open()` directement dans `routers/transactions.py:165,189`
- **Appelée depuis :** `POST /customers/{id}/transactions` après chaque création de transaction
- **Décision typique :** Justification des flux dépassant les seuils, vérification de la cohérence avec l'activité déclarée
- **Note technique :** L'alerte n'est pas créée par alert_service.py mais directement dans le routeur transactions, car elle dépend des cumuls calculés après insertion

#### 8.2.6 `BENEFICIAIRE_GROUPEMENT` — Bénéficiaire commun suspect
- **Déclencheur :** Virement ou paiement vers un bénéficiaire déjà destinataire de fonds provenant de plusieurs clients distincts
- **Seuils (configurables) :**
  - `BENEFICIAIRE_MIN_CLIENTS` ≥ 2 clients distincts vers le même bénéficiaire
  - Ou `BENEFICIAIRE_MIN_TRANSACTIONS` ≥ 5 transactions vers ce bénéficiaire
  - Ou `BENEFICIAIRE_MIN_MONTANT` ≥ 5 000 000 XOF cumulés vers ce bénéficiaire
- **Fenêtre d'analyse :** `FENETRE_CUMUL_JOURS` (défaut 30 jours)
- **Créée par :** `check_and_alert()` dans `services/beneficiaire_service.py:55`, appelé depuis `routers/transactions.py:194`
- **Limitation documentée :** La normalisation du nom du bénéficiaire (minuscule, strip) ne couvre pas les homonymes ni les variantes orthographiques. En production réelle, un algorithme de similarité textuelle (Levenshtein, Soundex) serait nécessaire.
- **Décision typique :** Identifier si le bénéficiaire est un rabatteur, un collecteur de fonds ou une structure écran

### 8.3 Flux de création — Vue d'ensemble

```
Transaction client
    │
    ├── ScoringEngine.calculate_score()
    │       │
    │       ├── SCORE_ELEVE       (si global_score ≥ 67)
    │       ├── PEP_DETECTE       (si C5 ≥ 50)
    │       └── SMURFING_DETECTE  (si smurfing détecté)
    │
    ├── create_kyc_alert_if_needed()
    │       └── KYC_INCOMPLET     (si kyc_completion < 40%)
    │
    ├── Seuils monétaires
    │       └── SEUIL_DEPASSE     (cumul 30j ≥ seuil)
    │
    └── check_and_alert()
            └── BENEFICIAIRE_GROUPEMENT (bénéficiaire commun)
```

### 8.4 Indépendance des alertes

**Point critique :** L'alerte `SMURFING_DETECTE` est créée **indépendamment** du score global. 
Un client peut avoir un score de 30 (FAIBLE) et recevoir une alerte SMURFING_DETECTE 
si le fractionnement est détecté.

De même, `SEUIL_DEPASSE` et `BENEFICIAIRE_GROUPEMENT` sont déclenchés par des règles 
transactionnelles indépendantes du moteur de scoring.

### 8.5 Anti-doublon

```python
def has_open_alert(db, customer_id, alert_type):
    """Vérifie si une alerte OPEN du même type existe déjà pour ce client."""
    return db.query(Alert).filter(
        Alert.client_id == customer_id,
        Alert.type_alerte == alert_type,
        Alert.statut == STATUS_OPEN,
    ).first() is not None
```

Toutes les fonctions de création d'alertes (`create_if_not_open`, `create_score_alert_if_needed`,
`create_pep_alert_if_needed`, etc.) vérifient systématiquement qu'aucune alerte OPEN du même type
n'existe déjà avant d'en créer une nouvelle. Cette vérification évite le spam d'alertes redondantes
qui rendrait le système inutilisable.

Lorsqu'un rescore automatique est déclenché par une transaction, les alertes existantes déjà OPEN 
ne sont pas dupliquées. Seules les alertes CLOSED peuvent être ré-ouvertes via un nouveau 
déclenchement.

### 8.6 Cycle de vie d'une alerte

```
                    ┌──────────┐
                    │   OPEN   │  ← Création automatique (scoring, seuil, etc.)
                    └────┬─────┘
                         │ Agent commence l'investigation
                    ┌────▼──────┐
                    │ UNDER_    │
                    │ REVIEW    │  ← Agent examine les faits
                    └────┬──────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────▼───┐ ┌───▼────┐ ┌───▼────┐
         │ CLOSED │ │ CLOSED │ │ CLOSED  │
         │ SAR=   │ │ SAR=   │ │ SAR=    │
         │ false  │ │ true   │ │ false   │
         └────────┘ └────────┘ └────────┘
         Classement  SAR transmis  Fausse alerte
         sans suite  à la CENTIF   (score réévalué)
```

Lors de la clôture (`statut = CLOSED`), le système enregistre automatiquement :
- L'agent ayant clôturé (`clos_par`)
- La date de clôture (`date_cloture`)
- La décision (`decision`) — champ texte libre
- Le flag `sar_declare` — true si un rapport de soupçon a été transmis à la CENTIF

---

## 9. Flux complets

### 9.0 Parcours résumé

```
Création client → Score initial
    ↓
Ajout documents KYC → Mise à jour complétude
    ↓
Enregistrement transactions → Rescore automatique
    ↓
Analyse C1-C6 → Score global → Catégorisation
    ↓
Création d'alertes si nécessaire
    ↓
Investigation → Export SAR → Déclaration CENTIF
    ↓
Journal d'audit (chaque action tracée)
```

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
                • SMURFING_DETECTE si smurfing détecté
                • PEP_DETECTE si PEP détectée (active ou ancienne)
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
- Type d'alerte (SCORE_ELEVE, SMURFING_DETECTE, PEP_DETECTE)
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
CORS_ORIGINS=http://localhost:5173,https://moteur-scoring-lb-ft.vercel.app
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5

# Frontend (.env)
VITE_API_URL=https://moteurscoring-lb-ft.onrender.com
VITE_USE_MOCKS=false
```

### 12.3 Base de données (Alembic)

5 migrations gèrent le schéma :
1. `v1_init` — Création des 14 tables avec contraintes FK
2. `v2_alerts_audit_pep` — Ajout des types d'alertes, index
3. `v3_server_defaults` — Valeurs par défaut des colonnes
4. `v4_column_removal` — Nettoyage des colonnes obsolètes
5. `v5_cascade_scores` — CASCADE DELETE sur `scores.client_id` pour cohérence avec les autres FK

---

## 13. Tests et couverture

### 13.1 Backend (pytest)

| Catégorie | Fichiers | Description |
|-----------|----------|-------------|
| Unitaires | `tests/scoring/` | Tests du moteur de scoring (C1-C6, smurfing) |
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
│   │   ├── scoring.py             # Moteur de scoring (932 lignes)
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
│   ├── pages/                     # 10 pages React
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

1. **Alerte SMURFING_DETECTE pour les gros revenus** — Ajuster `_SMURFING_REVENUE_MULT` (3.0 → 1.5) ou le rendre dynamique selon le profil
2. ~~**Index manquant** — Ajouter CASCADE DELETE sur `scores.client_id`~~ ✅ **Corrigé** (migration `abc123456789`)
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

## Annexe C — Observations techniques

- Le scoring est basé sur les tables `scoring_criteria` et `risk_thresholds`. Les poids par défaut (fallback) sont codés en dur dans `scoring.py`.
- `Score.categorie` est stocké en base avec la valeur `ELEVE` (sans accent) mais normalisé côté API en `ÉLEVÉ` via un mapping explicite dans `_get_category()`.
- `Transaction.date_op` est stocké sans fuseau horaire (naive datetime) et comparé en UTC naive pour compatibilité PostgreSQL.
- `pep_list` gère le champ `active` automatiquement via trigger SQL en fonction des dates (`date_fin`).
- `app_settings` permet de paramétrer des seuils monétaires (SMURFING_AMOUNT_THRESHOLD, SMURFING_NEAR_THRESHOLD_RATIO, etc.) utilisables par le backend sans recompilation.

---

*Document généré le 22 mai 2026 — RiskGuard v1.3 — IUT Parakou, département GEA*
