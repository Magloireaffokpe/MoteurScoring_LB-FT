# SCORING_LOGIC.md
# Logique du Moteur de Scoring LBC/FT — RiskGuard

> **Projet** : RiskGuard — Système de scoring AML/LBC-FT pour IMF béninoises  
> **Module** : `app/services/scoring.py`  
> **Auteur** : AFFOKPE Magloire (Dev A)  
> **Version** : 1.2 — Mai 2026  
> **Contrat** : API v1.0 — Binôme IUT Parakou 2024-2025

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture du moteur](#2-architecture-du-moteur)
3. [Paramètres dynamiques](#3-paramètres-dynamiques)
4. [Grille de notation — 6 critères](#4-grille-de-notation--6-critères)
   - [C1 — Profil professionnel](#c1--profil-professionnel-poids-20-)
   - [C2 — Zone géographique](#c2--zone-géographique-poids-20-)
   - [C3 — Historique transactionnel](#c3--historique-transactionnel-poids-25-)
   - [C4 — Ancienneté & fidélité](#c4--ancienneté--fidélité-poids-10-)
   - [C5 — Statut PEP](#c5--statut-pep-poids-15-)
   - [C6 — Cohérence KYC](#c6--cohérence-kyc-poids-10-)
5. [Calcul du score global](#5-calcul-du-score-global)
6. [Détection du smurfing — Anti faux-positifs](#6-détection-du-smurfing--anti-faux-positifs)
7. [Catégorisation du risque](#7-catégorisation-du-risque)
8. [Flux complet d'un appel API](#8-flux-complet-dun-appel-api)
9. [Corrections v1.2](#9-corrections-v12)
10. [Exemples de scores attendus](#10-exemples-de-scores-attendus)
11. [Dépendances inter-modules](#11-dépendances-inter-modules)

---

## 1. Vue d'ensemble

Le moteur de scoring LBC/FT (Lutte contre le Blanchiment de Capitaux et le
Financement du Terrorisme) calcule un **score de risque entre 0 et 100**
pour chaque client d'une Institution de Microfinance (IMF) béninoise.

Ce score est une **somme pondérée de 6 critères** (C1 à C6), chacun noté
de 0 à 100. Les poids sont configurables en base de données (table
`scoring_criteria`) sans redéploiement.

```
Score global = Σ (note_brute_Ci × poids_Ci)   pour i ∈ {1..6}
```

| Plage   | Catégorie | Action réglementaire                          |
|---------|-----------|-----------------------------------------------|
| 0 – 33  | **FAIBLE**| Vigilance standard, révision annuelle         |
| 34 – 66 | **MOYEN** | Vigilance renforcée, révision semestrielle    |
| 67 – 100| **ÉLEVÉ** | Déclaration CENTIF obligatoire, escalade      |

> **Important** : une alerte `SCORE_ELEVE` est créée automatiquement dès
> que `global_score ≥ 67`.

---

## 2. Architecture du moteur

```
ScoringEngine
│
├── calculate_score(customer_id)        ← point d'entrée unique
│   ├── _load_weights()                 ← lit scoring_criteria (DB)
│   ├── _load_thresholds()              ← lit risk_thresholds (DB)
│   ├── _score_c1(customer)             ← note brute C1 (0-100)
│   ├── _score_c2(customer)             ← note brute C2 (0-100)
│   ├── _score_c3(customer)             ← note brute C3 (0-100)
│   │   └── _detect_smurfing(txs, rev)  ← sous-analyse smurfing
│   ├── _score_c4(customer)             ← note brute C4 (0-100)
│   ├── _score_c5(customer)             ← note brute C5 (0-100)
│   ├── _score_c6(customer)             ← note brute C6 (0-100)
│   │   └── _avg_monthly_tx(customer)   ← flux mensuel moyen
│   └── _get_category(score)            ← FAIBLE | MOYEN | ÉLEVÉ
│
├── _get_zone(customer)                 ← helper : RiskZone ORM ou FK
├── _get_country(customer)              ← helper : Country ORM ou FK
└── _get_risk_country_ids()             ← helper : IDs pays border/FATF
```

---

## 3. Paramètres dynamiques

### Table `scoring_criteria` (gérée par Marcos)

Les poids sont **lus depuis la base** à chaque appel — aucune valeur n'est
hardcodée. Le moteur normalise automatiquement la somme pour qu'elle
soit toujours égale à 1.0, quelle que soit la valeur absolue des poids.

```python
# Exemple de normalisation
raw = {"C1": 20, "C2": 20, "C3": 25, "C4": 10, "C5": 15, "C6": 10}
total = 100
poids_normalises = {k: v / total for k, v in raw.items()}
# → {"C1": 0.20, "C2": 0.20, "C3": 0.25, ...}
```

> **Fix v1.2** : le filtre `is_active` a été supprimé car ce champ
> n'existe pas dans le schéma réel de `scoring_criteria`.

**Fallback** : si la table est vide, les poids par défaut sont utilisés :

| Critère | Poids par défaut |
|---------|-----------------|
| C1      | 20 %            |
| C2      | 20 %            |
| C3      | 25 %            |
| C4      | 10 %            |
| C5      | 15 %            |
| C6      | 10 %            |

### Table `risk_thresholds` (gérée par Marcos)

Les seuils de catégorisation sont également lus depuis la base.
Colonnes utilisées : `score_min`, `score_max`, `category`.

> **Attention** : la table stocke `'ELEVE'` (sans accent). Le moteur
> normalise en `'ÉLEVÉ'` (avec accent) pour respecter le contrat API.

---

## 4. Grille de notation — 6 critères

### C1 — Profil professionnel (poids 20 %)

**Source** : `customers.profession_risk` (`LOW` | `MEDIUM` | `HIGH`)

| Note brute | Profil                                                  |
|------------|---------------------------------------------------------|
| 10         | Salarié formel secteur public/privé réglementé (LOW)    |
| 35         | Commerçant informel déclaré, artisan (MEDIUM)           |
| 65         | Activité à risque élevé : changeur, transporteur (HIGH) |
| 85         | Activité non identifiable ou non renseignée             |

**Ajustements** :
- `revenus_declares == 0` et profession LOW/MEDIUM → `+10` (revenu nul suspect)
- `revenus_declares > 5 000 000` et profession LOW → `+15` (incohérence)

```python
# Exemple : changeur de devises (HIGH), revenus = 120 000 XOF
note_c1 = 65.0   # contribution = 65 × 0.20 = 13.0
```

---

### C2 — Zone géographique (poids 20 %)

**Sources** :
- `customers.zone_geo` → `risk_zones.risk_level`
- `customers.pays` → `countries.is_border`, `countries.is_fatf`, `countries.is_uemoa`

| Note brute | Zone                                                     |
|------------|----------------------------------------------------------|
| 10         | Zone urbaine stable (CAPITALE, URBAINE) — `FAIBLE`       |
| 35         | Zone semi-urbaine ou périphérique — `MOYEN`              |
| 65         | Zone frontalière (Nigéria, Togo, Burkina) — `ELEVE`      |
| 88         | Zone de conflit actif, sans infrastructure — `TRES_ELEVE`|
| 50         | Zone inconnue (aucune FK) — prudence intermédiaire       |

**Surcharges pays** (appliquées après la note de zone) :
- Pays FATF → `max(note, 70)`
- Pays frontalier → `max(note, 55)`
- Pays UEMOA → `min(note, 40)` ← plafonne à 40 si contexte réglementé

```python
# Exemple : zone FRONTIERE + pays Nigeria (frontalier, non FATF)
note_c2 = max(65.0, 55.0) = 65.0   # contribution = 65 × 0.20 = 13.0
```

---

### C3 — Historique transactionnel (poids 25 %)

**Source** : `transactions` (fenêtre des **90 derniers jours**)

**Cinq analyses cumulées** (chacune peut augmenter la note, jamais la diminuer) :

#### a) Ratio montant total / revenus déclarés

```
ratio = Σ(montants 90j) / (revenus_mensuel × 3)
```

| Ratio    | Note minimale déclenchée |
|----------|--------------------------|
| > 5×     | 80                       |
| > 3×     | 60                       |
| > 1.5×   | 40                       |

#### b) Fréquence anormale

| Transactions/jour | Note minimale |
|-------------------|---------------|
| > 5/j             | 70            |
| > 2/j             | 45            |

#### c) Retraits cash répétés

| Nb retraits (90j) | Note minimale |
|-------------------|---------------|
| > 10              | 65            |
| > 5               | 40            |

#### d) Détection du smurfing → voir [section 6](#6-détection-du-smurfing--anti-faux-positifs)

→ Si smurfing confirmé : note = max(note, **85**)

#### e) Destinations vers pays à risque

| Ratio tx vers pays border/FATF | Note minimale |
|--------------------------------|---------------|
| > 50 %                         | 75            |
| > 20 %                         | 55            |

---

### C4 — Ancienneté & fidélité (poids 10 %)

**Source** : `customers.date_creation`

| Durée relation | Note brute |
|----------------|------------|
| > 3 ans        | 10         |
| 1 à 3 ans      | 35         |
| 6 mois à 1 an  | 60         |
| < 6 mois       | 75         |
| Date inconnue  | 60         |

```python
# Exemple : client depuis 4 ans
note_c4 = 10.0   # contribution = 10 × 0.10 = 1.0
```

---

### C5 — Statut PEP (poids 15 %)

**Sources** :
- `customers.statut_pep` (boolean)
- `pep_list` (correspondance nom/prénom, insensible à la casse)

| Situation              | Note brute |
|------------------------|------------|
| Aucun lien PEP         | 0          |
| Entourage PEP          | 50 *(non implémenté dans v1.2 — pas de relation famille en base)* |
| PEP avérée (flag ou liste) | 100   |

**Logique** :
1. Si `customer.statut_pep == True` → note = **100** immédiatement
2. Sinon, recherche dans `pep_list` par `nom ILIKE` + `prenom ILIKE` + `active = True`
3. Si correspondance trouvée → note = **100** + log WARNING

```python
# Exemple : Fatima OUÉDRAOGO (PEP avérée)
note_c5 = 100.0   # contribution = 100 × 0.15 = 15.0
```

---

### C6 — Cohérence KYC (poids 10 %)

**Sources** :
- `customers_docs` (`valide`, `date_expiration`)
- `customers.kyc_completion` (0–100 %)
- `customers.revenus_declares` vs flux transactionnels

**Analyse des documents** :

| Situation documents                    | Note minimale |
|----------------------------------------|---------------|
| Aucun document                         | 85            |
| > 50 % invalides ou expirés            | 85            |
| Au moins 1 invalide ou expiré          | 55            |
| Au moins 1 expirant dans 60 jours      | 30            |
| Tous valides et non expirants          | 10            |

**Cohérence revenus/transactions** :

```
ratio = avg_monthly_tx / revenus_mensuel
```

| Ratio | Note minimale |
|-------|---------------|
| > 10× | 75            |
| > 5×  | 55            |
| > 2×  | 35            |

**Complétude KYC** :

| kyc_completion | Note minimale |
|----------------|---------------|
| < 30 %         | 80            |
| 30 à 59 %      | 40            |
| ≥ 60 %         | —             |

---

## 5. Calcul du score global

```python
# 1. Notes brutes (0-100 chacune)
notes = {"C1": 65, "C2": 65, "C3": 85, "C4": 75, "C5": 100, "C6": 85}

# 2. Poids normalisés (somme = 1.0)
poids = {"C1": 0.20, "C2": 0.20, "C3": 0.25, "C4": 0.10, "C5": 0.15, "C6": 0.10}

# 3. Contributions absolues
detail_json = {code: round(notes[code] * poids[code], 4) for code in notes}
# → {"C1": 13.0, "C2": 13.0, "C3": 21.25, "C4": 7.5, "C5": 15.0, "C6": 8.5}

# 4. Score global (arrondi, borné à [0, 100])
global_score = min(100, max(0, round(sum(detail_json.values()))))
# → round(78.25) = 78

# 5. Catégorie
risk_category = "ÉLEVÉ"   # 78 ≥ 67
```

**Propriété garantie** : `sum(detail_json.values()) ≈ global_score` (±1 arrondi)

---

## 6. Détection du smurfing — Anti faux-positifs

Le smurfing (fractionnement) consiste à fractionner un gros versement
en plusieurs petites transactions pour éviter les seuils déclaratifs FATF.

### Algorithme v1.2 — 3 conditions CUMULATIVES

```
Étape 1 : filtrer les transactions suspectes
  → montant multiple de 10 000 XOF
  → montant < 500 000 XOF (seuil déclaratif FATF)
  → au moins 3 transactions de ce type

  Si count_suspects < 3 → STOP (pas de smurfing)

Étape 2 : vérifier la concentration temporelle
  → toutes les tx suspectes doivent être dans une fenêtre ≤ 7 jours
  → span = max(dates) - min(dates)

  Si span > 7 jours → STOP (transactions étalées = comportement normal)

Étape 3 : vérifier le ratio par rapport aux revenus
  → total_suspects ≥ 3 × revenus_mensuels
  → ignorée si revenus = 0 (non renseigné)

  Si total_suspects < 3 × revenus → STOP (montants cohérents)

→ Si les 3 conditions passent : smurfing = True → C3 = max(C3, 85)
```

### Pourquoi ce changement ? — Élimination des faux positifs

**Cas problématique v1.1** : un client avec 4 dépôts de 150 000 XOF
espacés de 20 jours et des revenus de 300 000 XOF/mois déclenchait
incorrectement la détection de smurfing.

```
Analyse du cas :
  montants = [150 000, 150 000, 150 000, 150 000]
  → 150 000 % 10 000 == 0 ✓  et  150 000 < 500 000 ✓  et  count = 4 ≥ 3 ✓
  
  Étape 1 passée → FAUX POSITIF en v1.1 !

  Avec v1.2 :
  Étape 2 : dates espacées de 20j → span = 60j > 7j → STOP ✓
  → smurfing = False → C3 reste faible ✅
```

**Cas réel de smurfing** (Fatima OUÉDRAOGO) :

```
Transactions sur 5 jours consécutifs :
  [450 000, 460 000, 440 000, 450 000, 480 000, 430 000]
  
  Étape 1 : tous multiples de 10k, tous < 500k, count = 6 ≥ 3 ✓
  Étape 2 : span = 4 jours ≤ 7 jours ✓
  Étape 3 : total = 2 710 000 XOF > 3 × 120 000 = 360 000 XOF ✓
  
  → smurfing = True → C3 = 85 → contribution = 85 × 0.25 = 21.25 ✅
```

---

## 7. Catégorisation du risque

```python
def _get_category(self, score: int) -> str:
    # Normalisation DB → API (Fix v1.2)
    _NORMALIZE = {"ELEVE": "ÉLEVÉ", "ÉLEVÉ": "ÉLEVÉ", "MOYEN": "MOYEN", "FAIBLE": "FAIBLE"}
    
    for threshold in sorted(self._thresholds, key=lambda t: t["min_score"]):
        if threshold["min_score"] <= score <= threshold["max_score"]:
            return _NORMALIZE.get(threshold["category"].upper(), threshold["category"])
    
    # Fallback absolu
    if score <= 33: return "FAIBLE"
    if score <= 66: return "MOYEN"
    return "ÉLEVÉ"
```

**Normalisation** : la table `risk_thresholds` stocke `'ELEVE'` (sans accent,
convention seed_db.py de Marcos). Le contrat API v1.0 exige `'ÉLEVÉ'`
(avec accent). La normalisation est appliquée à **3 niveaux** :
1. `ScoringEngine._get_category()` — au calcul
2. `router._normalize_category()` — à la lecture depuis `Score.categorie`
3. `schemas.ScoreResponse` — validateur Pydantic `@field_validator`

---

## 8. Flux complet d'un appel API

```
Client HTTP
    │
    ▼
POST /api/scoring  { "customer_id": "uuid" }
    │
    ▼
[Auth JWT]  get_current_user()
    │
    ▼
router._run_scoring()
    ├── Customer.exists ? → 404 si non
    ├── ScoringEngine.calculate_score(uuid)
    │   ├── _load_weights()         ← DB: scoring_criteria
    │   ├── _load_thresholds()      ← DB: risk_thresholds
    │   ├── _score_c1..c6()         ← calculs LBC/FT
    │   └── _get_category()         ← normalisation ELEVE→ÉLEVÉ
    ├── Score.is_current → False    ← archivage ancien score
    ├── Score(is_current=True)      ← persistance nouveau score
    ├── Alert(SCORE_ELEVE) ?        ← si global_score ≥ 67
    ├── AuditLog(SCORING_CALCULATE) ← traçabilité réglementaire
    └── db.commit()
    │
    ▼
ScoreResponse { id, customer_id, global_score, risk_category,
                detail_json, is_current, scored_by, scored_at }
```

---

## 9. Corrections v1.2

| # | Fix | Fichier | Description |
|---|-----|---------|-------------|
| 1 | `_load_weights` sans `is_active` | `scoring.py` | Le champ `is_active` n'existe pas dans `scoring_criteria`. Tous les critères sont chargés sans filtre. |
| 2 | Normalisation `ELEVE` → `ÉLEVÉ` | `scoring.py`, `routers/scoring.py`, `schemas/score.py` | Appliquée à 3 niveaux pour garantir la conformité au contrat API. |
| 3 | Anti faux-positifs smurfing | `scoring.py` | `_detect_smurfing` reçoit désormais la liste complète des `Transaction` (avec dates) et les revenus. 3 conditions cumulatives : count ≥ 3, span ≤ 7j, total ≥ 3× revenus. |
| 4 | `datetime.utcnow()` → `datetime.now(timezone.utc)` | `scoring.py`, `routers/scoring.py` | Élimine les `DeprecationWarning` Python 3.12+. |
| 5 | Sécurité `or []` | `scoring.py` | `customer.accounts or []` et `customer.documents or []` partout pour éviter les `AttributeError` si la relation ORM n'est pas chargée. |

---

## 10. Exemples de scores attendus

### Amélie SOGLO — Profil FAIBLE

| Critère | Note brute | Poids | Contribution |
|---------|-----------|-------|-------------|
| C1 Profil (LOW, salarié) | 10 | 0.20 | 2.0 |
| C2 Zone (CAPITALE, Bénin UEMOA) | 10 | 0.20 | 2.0 |
| C3 Transactions (régulières, cohérentes) | 10 | 0.25 | 2.5 |
| C4 Ancienneté (> 4 ans) | 10 | 0.10 | 1.0 |
| C5 PEP (non) | 0 | 0.15 | 0.0 |
| C6 KYC (complet, docs valides) | 10 | 0.10 | 1.0 |
| **TOTAL** | | | **8.5 → 9** |

**Score** : 9/100 — **FAIBLE** ✅

---

### Koffi BIAOU — Profil MOYEN

| Critère | Note brute | Poids | Contribution |
|---------|-----------|-------|-------------|
| C1 Profil (HIGH, commerçant transfrontalier) | 65 | 0.20 | 13.0 |
| C2 Zone (FRONTIERE, Bénin) | 65 | 0.20 | 13.0 |
| C3 Transactions (pics × 2.5, virements vers Togo/Nigeria) | 55 | 0.25 | 13.75 |
| C4 Ancienneté (2 ans) | 35 | 0.10 | 3.5 |
| C5 PEP (non) | 0 | 0.15 | 0.0 |
| C6 KYC (partiel, doc expirant bientôt) | 30 | 0.10 | 3.0 |
| **TOTAL** | | | **46.25 → 46** |

**Score** : 46/100 — **MOYEN** ✅

---

### Fatima OUÉDRAOGO — Profil ÉLEVÉ

| Critère | Note brute | Poids | Contribution |
|---------|-----------|-------|-------------|
| C1 Profil (HIGH, changeur devises) | 65 | 0.20 | 13.0 |
| C2 Zone (FRONTIERE + pays frontalier) | 65 | 0.20 | 13.0 |
| C3 Transactions (smurfing + destinations FATF) | 85 | 0.25 | 21.25 |
| C4 Ancienneté (< 6 mois, cliente récente) | 75 | 0.10 | 7.5 |
| C5 PEP (avérée — flag + liste CENTIF) | 100 | 0.15 | 15.0 |
| C6 KYC (incomplet, doc invalide + expiré) | 85 | 0.10 | 8.5 |
| **TOTAL** | | | **78.25 → 78** |

**Score** : 78/100 — **ÉLEVÉ** ✅  
→ Alerte `SCORE_ELEVE` créée automatiquement.

---

## 11. Dépendances inter-modules

```
scoring.py
  ├── models/customers.py          (Customer)
  ├── models/transactions.py       (Transaction)
  ├── models/customer_accounts.py  (CustomerAccount)
  ├── models/customer_docs.py      (CustomerDoc)
  ├── models/pep_list.py           (PepEntry)
  ├── models/countries.py          (Country)
  ├── models/risk_zones.py         (RiskZone)
  ├── models/scoring_criteria.py   (ScoringCriteria) ← poids dynamiques
  └── models/risk_thresholds.py    (RiskThreshold)   ← seuils dynamiques

routers/scoring.py
  ├── services/scoring.py          (ScoringEngine)
  ├── services/alert_service.py    (create_score_alert_if_needed)
  ├── services/audit_service.py    (log_action)
  ├── models/scores.py             (Score)
  └── schemas/score.py             (ScoringRequest, ScoreResponse, ...)

schemas/score.py
  └── pydantic (BaseModel, field_validator)
```

---

*Document généré le 12 mai 2026 — RiskGuard v1.2*
