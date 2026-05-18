# RiskGuard — Frontend v1.2

> **Stack** : React 18 · Vite 5 · Tailwind CSS 3 · Recharts · React Router 6  
> **Auteur** : AFFOKPE Magloire (Dev A) — IUT Parakou 2025-2026

---

## Installation & démarrage

```bash
# 1. Installer les dépendances
npm install

# 2. Configurer l'environnement
cp .env.example .env
# → éditer VITE_API_URL si le backend n'est pas sur localhost:8000

# 3. Démarrer en développement
npm run dev
# → http://localhost:5173

# 4. Build de production
npm run build
```

---

## Structure respectée

```
src/
├── App.css                     ← Styles globaux Tailwind + animations
├── App.jsx                     ← Routeur principal (lazy loading)
├── main.jsx                    ← Point d'entrée React + providers
├── components/
│   ├── Badge.jsx               ← Badges colorés (FAIBLE/MOYEN/ÉLEVÉ/PEP...)
│   ├── Button.jsx              ← Bouton avec variants + loading state
│   ├── Card.jsx                ← Carte avec titre et action optionnels
│   ├── FormInput.jsx           ← Input, Select, Textarea avec validation
│   ├── Layout.jsx              ← Sidebar fixe 260px + Header + NavLinks
│   ├── Loader.jsx              ← Spinner full-page et inline
│   ├── Modal.jsx               ← Dialog avec overlay + fermeture Echap
│   ├── ScorePanel.jsx          ← Jauge SVG + radar Recharts + barres C1-C6
│   └── Table.jsx               ← Tableau + Pagination composant
├── context/
│   ├── AuthContext.jsx         ← JWT login/logout + rehydratation localStorage
│   └── AppContext.jsx          ← Sidebar open/close + recherche globale
├── hooks/
│   ├── useAuth.js              ← Wrapper useAuthContext()
│   ├── useFetch.js             ← Hook générique async avec loading/error
│   ├── useForm.js              ← Gestion formulaire avec validation
│   └── usePagination.js        ← page, skip, pageSize, paginationProps
├── pages/
│   ├── LoginPage.jsx           ← Connexion split-screen + validation
│   ├── DashboardPage.jsx       ← KPI + PieChart + alertes + rescore rapide
│   ├── ClientsListPage.jsx     ← Tableau paginé + filtres + rescore inline
│   ├── ClientDetailPage.jsx    ← Onglets KYC / Scoring / Alertes
│   ├── AddClientPage.jsx  ★    ← Stepper 3 étapes (NOUVEAU — non dans structure initiale)
│   ├── AlertsPage.jsx          ← Gestion alertes + modal + SAR
│   ├── ExportsPage.jsx         ← Interface PDF/CSV/SAR
│   ├── ScorePage.jsx           ← Visualisation d'un score particulier
│   └── AdminPage.jsx           ← Poids, Seuils, PEP (manuel+CSV), Audit
├── services/
│   ├── api.js                  ← Instance Axios + intercepteurs JWT + erreurs
│   ├── authService.js          ← POST /auth/login, GET /auth/me
│   ├── customerService.js      ← CRUD clients + référentiels (avec fallback mock)
│   ├── scoringService.js       ← POST /api/scoring, rescore, getById
│   ├── alertService.js         ← GET/PUT/POST /api/alerts
│   ├── exportService.js        ← PDF/CSV/SAR avec downloadBlob()
│   ├── dashboardService.js     ← GET /api/dashboard/*
│   └── adminService.js    ★    ← Critères, Seuils, PEP, Users, Audit (NOUVEAU)
├── theme/
│   ├── colors.js               ← Palette RiskGuard + scoreColor() + CATEGORY_COLORS
│   ├── spacing.js              ← Constantes d'espacement
│   └── typography.js           ← Familles de polices + tailles
└── utils/
    ├── constants.js            ← PROFESSIONS, pays, zones, critères (sync fake_data.py)
    ├── formatters.js           ← formatDate, formatAmount, formatName, normalizeCategory…
    ├── helpers.js              ← scoreColor, downloadBlob, debounce, truncateUUID…
    └── validators.js           ← validateStep1, validateStep2, validatePepForm…

tests/
├── setup.js                    ← Config vitest + jsdom mocks
├── unit/
│   └── components.test.jsx     ← 40+ tests : Badge, Button, Card, Table, Pagination,
│                                  Modal, FormInput, ScorePanel
└── integration/
    └── pages.test.jsx          ← Tests LoginPage, Dashboard, ClientsList,
                                   AddClientPage (stepper), AlertsPage, AdminPage
```

---

## Fichiers ajoutés par rapport à la structure initiale

| Fichier                         | Raison                                                                  |
| ------------------------------- | ----------------------------------------------------------------------- |
| `src/pages/AddClientPage.jsx`   | Formulaire stepper 3 étapes demandé                                     |
| `src/services/adminService.js`  | Requis par AdminPage (poids, seuils, PEP, audit)                        |
| `src/components/ScorePanel.jsx` | Composant réutilisable (détaché de ScorePage)                           |
| `tests/setup.js`                | Configuration vitest (mocks jsdom, ResizeObserver, URL.createObjectURL) |

---

## Synchronisation avec le backend (Marcos)

### Champs Customer (customers.py)

```
prenom, nom, date_naissance, phone, email
profession_code, profession_name, profession_risk, revenus_declares
city, region, zone_geo (FK risk_zones.id), pays (FK countries.id)
statut_pep, kyc_completion, kyc_level, status
```

### Champs PepEntry (pep_list.py)

```
nom, prenom, fonction, pays (FK countries.id)
date_debut, date_fin, source, active
```

### Champs Score (scores.py)

```
client_id, score_global, detail_json {C1..C6}
categorie ('FAIBLE'|'MOYEN'|'ELEVE'), is_current, calcule_par
```

### Professions (synchronisées avec generate_fake_data.py)

19 codes profession avec leur niveau de risque (LOW/MEDIUM/HIGH) dans `utils/constants.js`.

---

## Tests

```bash
npm test                  # Run une fois (CI)
npm run test:watch        # Mode watch (développement)
npm run test:coverage     # Rapport de couverture HTML
```

**Tests unitaires** (`tests/unit/components.test.jsx`) — 40+ assertions :

- Badge (6 variants), Button (8 cas), Card, Loader, FormInput, Modal, Table, Pagination, ScorePanel

**Tests d'intégration** (`tests/integration/pages.test.jsx`) :

- LoginPage : validation, erreur 401, appel authService
- DashboardPage : KPI, alertes, rescore
- ClientsListPage : chargement, filtres, PEP badge
- AddClientPage : stepper, validation étape 1, passage étape 2
- AlertsPage : filtres, modal gestion, alertes chargées
- AdminPage : 4 onglets, validation PEP manuel, critères

---

## Dépendance supplémentaire

**`react-hot-toast ^2.4.1`** — remplace `react-toastify` (plus léger, zéro CSS externe requis, natif avec Tailwind). Déjà dans `package.json`.

---

## Checklist soutenance

```
□ Backend démarré : uvicorn app.main:app --reload --port 8000
□ Seed : python scripts/seed_db.py
□ Données : python scripts/generate_fake_data.py
□ Frontend : npm run dev → http://localhost:5173
□ Login : admin / admin1234
□ Dashboard : KPI chargés, graphique répartition visible
□ Clients : liste paginée, filtres, badge PEP Fatima OUÉDRAOGO
□ Nouveau client : stepper 3 étapes, scoring automatique après création
□ Fiche client : onglets KYC / Scoring (jauge + radar) / Alertes
□ Rescore : bouton fiche client → score mis à jour
□ Exporter PDF fiche client
□ Exporter CSV transactions
□ Alertes : filtres, modal, export SAR
□ Admin (poids C3 = 30%) → recalculer un score → vérifier impact
□ Admin PEP manuel → ajouter une entrée
□ Audit logs : actions apparaissent
□ npm test → tous les tests passent
```
