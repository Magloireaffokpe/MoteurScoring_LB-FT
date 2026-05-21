# Spécifications des Diagrammes UML — RiskGuard

**Version :** 1.0 — Mai 2026
**Usage :** Documentation soutenance — IUT Parakou 2025-2026
**Outil recommandé :** Draw.io (diagrams.net), Lucidchart, ou PlantUML

---

## 1. Diagramme de Contexte (Système)

**Objectif :** Montrer le système RiskGuard et ses interactions avec les acteurs et systèmes externes.

### Éléments

| Élément | Type | Description |
|---------|------|-------------|
| RiskGuard | Système | Application complète de scoring LBC/FT |
| Agent Compliance | Acteur primaire | Gère clients, alertes, transactions, exports |
| Administrateur | Acteur primaire | Gère utilisateurs, critères, seuils, PEP |
| CENTIF | Système externe | Destinataire des rapports SAR |
| Base de données | Stockage | PostgreSQL (Neon) |
| Frontend React | Sous-système | Interface utilisateur (Vercel) |
| Backend FastAPI | Sous-système | API REST (Render) |

### Flux principaux

```
[CENTIF] ←── Rapport SAR PDF ── [RiskGuard] ── API HTTPS ── [Frontend]
                                  │                                │
                                  ├── SQL ─── [PostgreSQL]        │
                                  │                                │
                          [Agent Compliance]              [Administrateur]
```

### Flux de données
- Agent ⇄ Frontend ⇄ API ⇄ DB : CRUD clients, transactions, alertes, scores
- Admin ⇄ Frontend ⇄ API ⇄ DB : Configuration, administration, audit
- RiskGuard → Export PDF/CSV : Fiche client, rapport SAR, transactions

---

## 2. Diagramme de Cas d'Utilisation (Use Case)

**Objectif :** Fonctionnalités du système vues par les acteurs.

### Acteurs

| Acteur | Description | Peut faire |
|--------|-------------|-----------|
| Agent Compliance | Utilisateur métier opérationnel | UC-01 à UC-12, UC-16 |
| Administrateur | Super-utilisateur | Tout (UC-01 à UC-16) |
| Système | Automatique | UC-10b (scoring auto), UC-10c (alerte auto) |

### Cas d'Utilisation

| ID | Nom | Acteur principal | Description |
|----|-----|-----------------|-------------|
| UC-01 | Connexion | Agent, Admin | S'authentifier avec login/password (rate limit 5/min) |
| UC-02 | Visualiser Dashboard | Agent, Admin | KPIs temps réel, polling 30s |
| UC-03 | Lister clients | Agent, Admin | Recherche, filtres, pagination |
| UC-04 | Consulter fiche client | Agent, Admin | Onglets KYC / Scoring / Alertes |
| UC-05 | Créer client | Agent, Admin | Stepper 3 étapes + scoring auto |
| UC-06 | Modifier client | Agent, Admin | Coordonnées, profession, résidence |
| UC-07 | Ajouter compte | Agent, Admin | COURANT ou EPARGNE |
| UC-08 | Ajouter document KYC | Agent, Admin | CNI, PASSEPORT, etc. |
| UC-09 | Enregistrer transaction | Agent, Admin | + auto-rescore + alerte |
| UC-10 | Calculer score | Agent, Admin, Système | C1-C6, smurfing, card testing |
| UC-10b | Scoring automatique | Système | Déclenché par création client ou transaction |
| UC-10c | Génération alerte | Système | Si score > 66 après rescore |
| UC-11 | Gérer alertes | Agent, Admin | Filtrer, ouvrir, clôturer, SAR |
| UC-12 | Déclarer SAR | Agent, Admin | Rapport PDF CENTIF |
| UC-13 | Configurer scoring | Admin | Poids C1-C6, seuils FAIBLE/MOYEN/ELEVE |
| UC-14 | Gérer liste PEP | Admin | Ajout manuel, import CSV |
| UC-15 | Consulter audit | Admin | Journal des actions |
| UC-16 | Exporter données | Agent, Admin | PDF client, CSV transactions, SAR PDF |

### Relations entre UC

```
UC-04 ──include──> UC-10 (voir score dans fiche)
UC-05 ──include──> UC-10 (scoring auto à la création)
UC-09 ──include──> UC-10 (auto-rescore après transaction)
UC-11 ──extend──> UC-04 (alertes visibles dans fiche)
UC-13 ──extend──> UC-10 (poids modifiables)
UC-12 ──extend──> UC-11 (SAR depuis une alerte)
UC-16 ──extend──> UC-04 (export depuis fiche)
```

---

## 3. Diagramme de Classes (Modèle de Données)

**Objectif :** Classes du domaine, attributs, méthodes, associations.

### Classes principales et attributs

| Classe | Table | Attributs clés | Méthodes |
|--------|-------|---------------|----------|
| **User** | `users` | id, login, password_hash, role_id, is_active | verify_password() |
| **UserRole** | `user_roles` | id, name, permissions | — |
| **Customer** | `customers` | id, nom, prenom, phone, email, profession*, revenus, city, region, zone_geo, pays, statut_pep, kyc_*, status | get_current_score(), get_documents(), get_accounts() |
| **CustomerAccount** | `customer_accounts` | id, client_id, type_compte, solde_moyen, status | — |
| **CustomerDoc** | `customers_docs` | id, client_id, type_doc, numero, date_expiration | valide (propriété) |
| **Transaction** | `transactions` | id, compte_id, montant, devise, type_op, canal, pays_* | — |
| **Score** | `scores` | id, client_id, score_global, detail_json, categorie, is_current | — |
| **Alert** | `alerts` | id, client_id, type_alerte, statut, sar_declare | — |
| **AuditLog** | `audit_logs` | id, user_id, client_id, action, ip_address | — |
| **PepEntry** | `pep_list` | id, nom, prenom, fonction, pays, active | — |
| **Country** | `countries` | id, code_iso, name, is_* | — |
| **RiskZone** | `risk_zones` | id, name, risk_level | — |
| **ScoringCriteria** | `scoring_criteria` | id, code, weight, name | — |
| **RiskThreshold** | `risk_thresholds` | id, category, score_min, score_max, action | — |

### Associations

| Source | Multiplicité | Cible | Multiplicité | Type |
|--------|-------------|-------|-------------|------|
| UserRole | 1 | User | 0..* | Composition |
| User | 1 | AuditLog | 0..* | Agrégation |
| Country | 1 | Customer | 0..* | Association |
| RiskZone | 1 | Customer | 0..* | Association |
| Customer | 1 | CustomerAccount | 0..* | Composition (cascade) |
| Customer | 1 | CustomerDoc | 0..* | Composition (cascade) |
| Customer | 1 | Score | 0..* | Association |
| Customer | 1 | Alert | 0..* | Association |
| CustomerAccount | 1 | Transaction | 0..* | Composition (cascade) |
| Country | 1 | Transaction (origine) | 0..* | Association |
| Country | 1 | Transaction (destination) | 0..* | Association |
| Country | 1 | PepEntry | 0..* | Association |

### Cardinalités

```
UserRole 1 ──── * User
User 1 ──── * AuditLog
Country 1 ──── * Customer
RiskZone 1 ──── * Customer
Customer 1 ──── * CustomerAccount
Customer 1 ──── * CustomerDoc
Customer 1 ──── * Score
Customer 1 ──── * Alert
CustomerAccount 1 ──── * Transaction
Country 1 ──── * Transaction (origine)
Country 1 ──── * Transaction (destination)
Country 1 ──── * PepEntry
User 1 ──── * Customer (pep_verified_by)
User 1 ──── * CustomerDoc (verified_by)
User 1 ──── * Alert (clos_par)
User 1 ──── * ScoringCriteria (updated_by)
```

---

## 4. Diagrammes de Séquence

**Objectif :** Interactions temporelles entre objets pour les flux critiques.

### Séquence 1 — Authentification

```
Acteur: Agent Compliance
Frontend: React App
Backend: FastAPI
DB: PostgreSQL

Agent->Frontend: Saisit login + password
Frontend->Backend: POST /auth/login {login, password}
Backend->DB: SELECT * FROM users WHERE login = ?
DB-->Backend: user row with password_hash
Backend->Backend: verify password (bcrypt)
Backend->Backend: generate JWT (8h expiry)
Backend->DB: UPDATE users SET last_login = now()
Backend-->Frontend: 200 {access_token, user_id, role}
Frontend->Frontend: set cookie httpOnly
Frontend->Backend: GET /auth/me (cookie)
Backend-->Frontend: 200 {id, login, role, is_active}
Frontend->Frontend: redirect to /dashboard
Frontend-->Agent: Dashboard visible
```

### Séquence 2 — Création de transaction + auto-rescore

```
Acteur: Agent Compliance
Frontend: React App
Backend: FastAPI
ScoringEngine: Service
AlertService: Service
DB: PostgreSQL

Agent->Frontend: Remplir formulaire transaction
Frontend->Backend: POST /customers/{id}/transactions
Backend->DB: INSERT INTO transactions (...)
DB-->Backend: transaction created
Backend->ScoringEngine: score(customer_id)
ScoringEngine->DB: SELECT transactions FROM customer
ScoringEngine->DB: SELECT accounts, docs, customer
ScoringEngine->ScoringEngine: compute C1..C6 scores
ScoringEngine->ScoringEngine: detect smurfing
ScoringEngine->ScoringEngine: detect card testing
ScoringEngine->ScoringEngine: detect duplicates
ScoringEngine->ScoringEngine: weighted sum = global_score
ScoringEngine-->Backend: {score_global, categorie, detail, smurfing, card_testing}
Backend->DB: UPDATE scores SET is_current=false WHERE client_id=X
Backend->DB: INSERT INTO scores (...is_current=true)
Backend->AlertService: check thresholds
AlertService->AlertService: if score_global > 66 → create alert
AlertService->DB: INSERT INTO alerts (...)
AlertService-->Backend: alert created (or not)
Backend-->Frontend: 201 {transaction, new_score_global, new_score_category}
Frontend-->Agent: Transaction créée + nouveau score affiché
```

### Séquence 3 — Rescore batch (tous les clients)

```
Acteur: Administrateur
Frontend: React App
Backend: FastAPI
ScoringEngine: Service
AlertService: Service
DB: PostgreSQL

Admin->Frontend: Clique "Recalculer tous les scores"
Frontend->Backend: POST /scoring/rescore-all
Backend->DB: SELECT id FROM customers
DB-->Backend: [id1, id2, ..., id503]

loop 503 times
    Backend->ScoringEngine: score(customer_id)
    ScoringEngine->DB: fetch transactions, accounts, docs
    ScoringEngine->ScoringEngine: compute C1..C6
    ScoringEngine-->Backend: score result
    Backend->DB: mark old score is_current=false
    Backend->DB: INSERT new score
    Backend->AlertService: check thresholds
    AlertService-->Backend: alert created (or not)
end

Backend-->Frontend: 200 {rescored: 503, critical: 12}
Frontend-->Admin: Notification "503 scores recalculés"
```

### Séquence 4 — Cycle de vie d'une alerte

```
Acteur: Agent Compliance
Frontend: React App
Backend: FastAPI
DB: PostgreSQL

Note over Backend: Alerte créée automatiquement par le scoring (score > 66)
Backend->DB: INSERT INTO alerts (type, statut='OPEN', sar=false)

Agent->Frontend: Ouvre la liste des alertes
Frontend->Backend: GET /api/alerts?statut=OPEN
Backend->DB: SELECT * FROM alerts WHERE statut='OPEN'
DB-->Backend: [alert1, alert2, ...]
Backend-->Frontend: 200 {items: [...], total: 18}
Frontend-->Agent: Liste des alertes ouvertes

Agent->Frontend: Clique sur une alerte
Frontend->Backend: GET /api/alerts/{id}
Backend-->Frontend: 200 {id, type, client, date, ...}
Frontend-->Agent: Détail de l'alerte

Agent->Frontend: Décide de clôturer + déclarer SAR
Frontend->Backend: PUT /api/alerts/{id} {statut: 'CLOSED', decision: '...', sar_declare: true}
Backend->DB: UPDATE alerts SET statut='CLOSED', sar_declare=true
DB-->Backend: alert updated
Backend-->Frontend: 200 AlertResponse
Frontend-->Agent: Alerte clôturée, SAR marqué

Agent->Frontend: Télécharge le rapport SAR
Frontend->Backend: GET /api/exports/sar/{alert_id}/pdf
Backend->Backend: generate PDF (ReportLab)
Backend-->Frontend: StreamingResponse (PDF)
Frontend-->Agent: Fichier PDF téléchargé
```

---

## 5. Diagramme d'Activité

**Objectif :** Workflow du scoring automatique (enchaînement des actions).

### Activité : Calcul du score LBC/FT

```
[Début] ──> Récupérer données client
    │
    ▼
[Récupérer transactions client]
    │
    ▼
[Récupérer comptes et documents]
    │
    ▼
[Parallélisme]
    ├──> Calculer C1 (Profil client)
    │       ├── profession_risk → score
    │       ├── statut_pep → score
    │       └── cohérence revenus → score
    │
    ├──> Calculer C2 (Transactionnel)
    │       ├── montant max / min
    │       ├── volume hebdomadaire
    │       ├── détection smurfing
    │       ├── détection card testing
    │       └── détection doublons
    │
    ├──> Calculer C3 (Géographique)
    │       ├── zone_geo → risque
    │       ├── virements internationaux
    │       └── pays FATF / frontaliers
    │
    ├──> Calculer C4 (Produit/Service)
    │       ├── type_compte
    │       └── ancienneté relation
    │
    ├──> Calculer C5 (Canal)
    │       ├── canaux utilisés
    │       └── proportion internet/mobile
    │
    └──> Calculer C6 (KYC)
            ├── documents valides ?
            └── kyc_completion %
    │
    ▼
[Fusion : Score pondéré = Σ(Ci × poids_i)]
    │
    ▼
[Décision : catégorie]
    ├── score < 34 ──> FAIBLE
    ├── 34 ≤ score ≤ 66 ──> MOYEN
    └── score > 66 ──> ELEVE
    │
    ▼
[Sauvegarder score (is_current=true)]
    │
    ▼
[Vérifier seuil alerte]
    ├── score > 66 ──> Créer alerte OPEN
    └── score ≤ 66 ──> Rien
    │
    ▼
[Fin]
```

---

## 6. Diagramme de Déploiement

**Objectif :** Architecture physique de la solution déployée.

### Nœuds et artefacts

| Nœud | Technologie | Hébergement | Artefacts |
|------|-----------|-------------|-----------|
| Client | Navigateur Web | Poste agent/admin | Frontend React (JS bundle) |
| Frontend Server | Vite + Node 18+ | Vercel | static SPA, vercel.json |
| Backend Server | Python 3.11 + FastAPI | Render | app/**, requirements.txt, Procfile |
| Base de données | PostgreSQL 15 | Neon | 14 tables, 18 FK |

### Protocoles

```
[Client Navigateur]
    │
    ├── HTTPS ──> [Vercel] ── Frontend React (CDN)
    │                       └── Static assets (cache 1 an)
    │
    ├── HTTPS ──> [Render] ── Backend FastAPI (gunicorn + uvicorn)
    │                       │
    │                       └── TCP 5432 ──> [Neon] ── PostgreSQL
    │                                              ├── connexion pool: 5
    │                                              ├── SSL require
    │                                              └── Extensions: pgcrypto
    │
    └── HTTPS ──> [Vercel] ── rewrites → /index.html (SPA fallback)
```

### Configuration des nœuds

**Render (Web Service)**
- Plan : Free / Starter
- RAM : 512 MB (Free) — 2GB (Starter)
- Workers gunicorn : 2 (Free) / 4 (Starter)
- Start : `alembic upgrade head && gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker`
- Env vars : DATABASE_URL, SECRET_KEY, DEBUG=false, CORS_ORIGINS, DATABASE_POOL_SIZE=5

**Neon (PostgreSQL)**
- Plan : Free (5 connections max)
- Storage : 500 MB
- Branches : 1 main + 1 dev
- SSL : require

**Vercel (Frontend)**
- Plan : Hobby (Free)
- Build : `npm run build`
- Output : `dist/`
- SPA : vercel.json rewrites
- Env : VITE_API_URL

---

## 7. Diagramme de Paquetages (Composants)

**Objectif :** Organisation modulaire du code backend.

### Backend (FastAPI)

```
backend/
├── app/
│   ├── main.py                    # Point d'entrée, CORS, middleware
│   ├── config.py                  # Settings (DATABASE_URL, SECRET_KEY...)
│   ├── limiter.py                 # Rate limiting (slowapi)
│   │
│   ├── db/
│   │   ├── session.py             # Engine + SessionLocal
│   │   └── base.py                # DeclarativeBase
│   │
│   ├── models/                    # 14 classes ORM
│   │   ├── customers.py
│   │   ├── transactions.py
│   │   ├── scores.py
│   │   ├── alerts.py
│   │   ├── pep_list.py
│   │   ├── countries.py
│   │   ├── risk_zones.py
│   │   ├── customer_accounts.py
│   │   ├── customer_docs.py
│   │   ├── users.py
│   │   ├── user_roles.py
│   │   ├── audit_logs.py
│   │   ├── scoring_criteria.py
│   │   └── risk_thresholds.py
│   │
│   ├── schemas/                   # Pydantic models
│   │   ├── customer.py
│   │   ├── transaction.py
│   │   ├── score.py
│   │   ├── alert.py
│   │   ├── auth.py
│   │   ├── pep.py
│   │   ├── country.py
│   │   └── ...
│   │
│   ├── routers/                   # 12 controllers
│   │   ├── auth.py
│   │   ├── customers.py
│   │   ├── transactions.py
│   │   ├── alerts.py
│   │   ├── scoring.py
│   │   ├── dashboard.py
│   │   ├── admin.py
│   │   ├── customer_accounts.py
│   │   ├── customer_docs.py
│   │   ├── pep.py
│   │   ├── referentials.py
│   │   └── exports.py
│   │
│   ├── services/                  # Métier
│   │   ├── scoring.py             # Moteur (870 lignes)
│   │   ├── auth_service.py        # JWT, password
│   │   └── alert_service.py       # Création alertes auto
│   │
│   └── middleware/
│       ├── logging.py             # Logging middleware
│       └── error_handlers.py      # Exception handlers
│
├── scripts/
│   ├── seed_db.py                 # Données de référence
│   └── generate_fake_data.py      # 500 clients test (1190 lignes)
│
├── alembic/                       # Migrations
├── tests/                         # Tests
├── requirements.txt
└── Procfile                       # Render start
```

### Frontend (React)

```
frontend/
├── src/
│   ├── main.jsx                   # Entry point
│   ├── App.jsx                    # Routes (lazy loading)
│   ├── App.css                    # Tailwind + animations
│   │
│   ├── components/                # UI réutilisable
│   │   ├── Badge.jsx
│   │   ├── Button.jsx
│   │   ├── Card.jsx
│   │   ├── FormInput.jsx (Input, Select, Textarea)
│   │   ├── Layout.jsx (Sidebar + Header)
│   │   ├── Loader.jsx
│   │   ├── Modal.jsx
│   │   ├── ScorePanel.jsx (Jauge + Radar + Barres)
│   │   └── Table.jsx (Pagination)
│   │
│   ├── context/
│   │   ├── AuthContext.jsx
│   │   └── AppContext.jsx
│   │
│   ├── hooks/
│   │   ├── useAuth.js
│   │   ├── useFetch.js
│   │   ├── useForm.js
│   │   └── usePagination.js
│   │
│   ├── pages/                     # 9 pages
│   │   ├── LoginPage.jsx
│   │   ├── DashboardPage.jsx
│   │   ├── ClientsListPage.jsx
│   │   ├── ClientDetailPage.jsx
│   │   ├── AddClientPage.jsx (Stepper)
│   │   ├── AlertsPage.jsx
│   │   ├── ScorePage.jsx
│   │   ├── ExportsPage.jsx
│   │   └── AdminPage.jsx (4 onglets)
│   │
│   ├── services/                  # 7 API services
│   │   ├── api.js (Axios instance)
│   │   ├── authService.js
│   │   ├── customerService.js
│   │   ├── scoringService.js
│   │   ├── alertService.js
│   │   ├── dashboardService.js
│   │   ├── adminService.js
│   │   └── exportService.js
│   │
│   ├── theme/                     # Design tokens
│   │   ├── colors.js
│   │   ├── spacing.js
│   │   └── typography.js
│   │
│   └── utils/
│       ├── constants.js
│       ├── formatters.js
│       ├── helpers.js
│       └── validators.js
│
├── vite.config.js
├── vercel.json
└── package.json
```

---

## 8. Diagramme d'État (Alertes et Scores)

**Objectif :** Cycle de vie des objets avec états et transitions.

### États d'une Alerte

```
┌──────────┐     création auto     ┌──────────┐
│ Nouveau  │ ──────────────────→   │  OPEN    │
│ (score   │                       │          │
│  > 66)   │                       │          │
└──────────┘                       └────┬─────┘
                                        │
                          ┌─────────────┴─────────────┐
                          │                           │
                    ┌─────▼──────┐              ┌─────▼──────┐
                    │   CLOSED   │              │  CLOSED    │
                    │  (normal)  │              │  (SAR)     │
                    │ sar=false  │              │ sar=true   │
                    └────────────┘              └────────────┘
```

### États d'un Score

```
┌──────────┐                          ┌──────────────────┐
│  NOUVEAU │── scoring initial ──→    │  is_current=true │
│  Client  │                          │  (score + cat.)  │
└──────────┘                          └────────┬─────────┘
                                               │
                        ┌──────────────────────┴──────────────────────┐
                        │                         │                   │
                  ┌─────▼──────┐            ┌─────▼──────┐      ┌─────▼──────┐
                  │  rescore   │            │  rescore   │      │  rescore   │
                  │  manuel    │            │  auto (tx) │      │  batch     │
                  └─────┬──────┘            └─────┬──────┘      └─────┬──────┘
                        │                         │                   │
                        └─────────────────────────┴───────────────────┘
                                            │
                                            ▼
                                  ┌──────────────────┐
                                  │ is_current=false │
                                  │   (archivé)      │
                                  └──────────────────┘
                                            │
                                  ┌─────────▼─────────┐
                                  │ is_current=true   │
                                  │  (nouveau score)  │
                                  └───────────────────┘
```

---

## 9. Couleurs et styles recommandés

| Élément | Couleur | Code Hex |
|---------|---------|----------|
| Arrière-plan système | Gris clair | #F5F5F5 |
| Agent Compliance | Bleu | #2563EB |
| Administrateur | Violet | #7C3AED |
| Système (auto) | Vert | #059669 |
| FAIBLE (score) | Vert | #22C55E |
| MOYEN (score) | Jaune/Orange | #F59E0B |
| ELEVE (score) | Rouge | #EF4444 |
| Entité (classe) | Orange doux | #FED7AA |
| Association | Gris | #6B7280 |
| Ligne de vie (sequence) | Gris pointillé | #9CA3AF |
| Activation (sequence) | Bleu clair | #BFDBFE |

---

## 10. Liste de vérification pour la soutenance

- [ ] Diagramme de Contexte (système + acteurs + flux)
- [ ] Diagramme de Cas d'Utilisation (16 UC, 3 acteurs)
- [ ] Diagramme de Classes (14 classes + associations + multiplicités)
- [ ] Diagramme de Séquence — Authentification
- [ ] Diagramme de Séquence — Création de transaction + auto-rescore
- [ ] Diagramme de Séquence — Rescore batch
- [ ] Diagramme de Séquence — Cycle de vie alerte
- [ ] Diagramme d'Activité — Calcul du score
- [ ] Diagramme de Déploiement — Render + Neon + Vercel
- [ ] Diagramme de Paquetages — Backend + Frontend
- [ ] Diagramme d'État — Alerte (OPEN → CLOSED/SAR)
- [ ] Diagramme d'État — Score (current → archivé)
