# SCORING_LOGIC.md
# Logique du Moteur de Scoring LBC/FT — RiskGuard

> **Projet** : RiskGuard — Système de scoring AML/LBC-FT pour IMF béninoises  
> **Module** : `app/services/scoring.py`  
> **Auteur** : AFFOKPE Magloire (Dev A)  
> **Version** : 1.3 — Mai 2026  
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
7. [Détections comportementales complémentaires](#7-détections-comportementales-complémentaires)
   - [Card testing](#71-card-testing)
   - [Transactions dupliquées / replay](#72-transactions-dupliquées--replay)
8. [Catégorisation du risque](#8-catégorisation-du-risque)
9. [Système d'alertes](#9-système-dalertes)
10. [Flux complet d'un appel API](#10-flux-complet-dun-appel-api)
11. [Corrections v1.2 et v1.3](#11-corrections-v12-et-v13)
12. [Exemples de scores attendus](#12-exemples-de-scores-attendus)
13. [Dépendances inter-modules](#13-dépendances-inter-modules)

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

| Plage    | Catégorie  | Action réglementaire                          |
|----------|------------|-----------------------------------------------|
| 0 – 33   | **FAIBLE** | Vigilance standard, révision annuelle         |
| 34 – 66  | **MOYEN**  | Vigilance renforcée, révision semestrielle    |
| 67 – 100 | **ÉLEVÉ**  | Déclaration CENTIF obligatoire, escalade      |

> **Important** : une alerte `SCORE_ELEVE` est créée automatiquement dès
> que `global_score ≥ 67`. Des alertes fines supplémentaires (PEP, smurfing,
> card testing) sont créées indépendamment selon les signaux détectés —
> voir [section 9](#9-système-dalertes).

---

## 2. Architecture du moteur

```
ScoringEngine
│
├── calculate_score(customer_id)          ← point d'entrée unique
│   ├── _load_weights()                   ← lit scoring_criteria (DB)
│   ├── _load_thresholds()                ← lit risk_thresholds (DB)
│   ├── _score_c1(customer)               ← note brute C1 (0-100)
│   ├── _score_c2(customer)               ← note brute C2 (0-100)
│   ├── _score_c3(customer)               ← note brute C3 (0-100)
│   │   ├── _detect_smurfing(txs, rev)    ← fractionnement (3 conditions)
│   │   ├── _detect_duplicates(txs)       ← tx dupliquées / replay [v1.3]
│   │   └── [card testing inline]         ← micro-tx carte [v1.3]
│   ├── _score_c4(customer)               ← note brute C4 (0-100)
│   ├── _score_c5(customer)               ← note brute C5 (0/50/100) [v1.3]
│   ├── _score_c6(customer)               ← note brute C6 (0-100)
│   │   └── _avg_monthly_tx(customer)     ← flux mensuel moyen
│   └── _get_category(score)              ← FAIBLE | MOYEN | ÉLEVÉ
│
│   Champs retournés (v1.3 — non-breaking) :
│     global_score, risk_category, detail_json   ← existants
│     c5_score, smurfing_detected, card_testing_count ← nouveaux
│
├── _get_zone(customer)                   ← helper : RiskZone ORM ou FK
├── _get_country(customer)                ← helper : Country ORM ou FK
└── _get_risk_country_ids()               ← helper : IDs pays border/FATF
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
note_c2 = max(65.0, 55.0)  # = 65.0 → contribution = 65 × 0.20 = 13.0
```

---

### C3 — Historique transactionnel (poids 25 %)

**Source** : `transactions` (fenêtre des **90 derniers jours**)

**Sept analyses cumulées** (v1.3 — chacune peut augmenter la note, jamais la diminuer) :

#### a) Ratio montant total / revenus déclarés

```
ratio = Σ(montants 90j) / (revenus_mensuel × 3)
```

| Ratio  | Note minimale déclenchée |
|--------|--------------------------|
| > 5×   | 80                       |
| > 3×   | 60                       |
| > 1.5× | 40                       |

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

→ Si smurfing confirmé : `note = max(note, 85)`  
→ Positionne `self._smurfing_detected = True` (exposé dans le résultat)

#### e) Destinations vers pays à risque

| Ratio tx vers pays border/FATF | Note minimale |
|--------------------------------|---------------|
| > 50 %                         | 75            |
| > 20 %                         | 55            |

#### f) Card testing — micro-transactions carte [v1.3]

Détection comportementale : petits montants répétés sur carte pour valider
une carte volée avant une fraude de grande ampleur.
La **validité technique** de la carte est gérée par le service dédié existant.

| Nb micro-tx carte ≤ 1 000 XOF (90j) | Note minimale |
|--------------------------------------|---------------|
| ≥ 5                                  | 75            |
| ≥ 2                                  | 45            |

→ Positionne `self._card_testing_count` (exposé dans le résultat)

#### g) Transactions dupliquées / replay [v1.3]

Détecte les groupes de transactions avec le même montant arrondi (tolérance
100 XOF pour les frais) vers la même destination, dans une fenêtre de 24 h.

| Nb groupes suspects (24 h) | Note minimale |
|---------------------------|---------------|
| ≥ 3                       | 60            |
| ≥ 1                       | 40            |

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

**Grille révisée v1.3 — alignée GAFI recommandation 12** :

| Situation                        | Note brute | Alerte créée   |
|----------------------------------|------------|----------------|
| Aucun lien PEP                   | 0          | —              |
| Ancienne PEP (`active=False`)    | **50**     | `PEP_ANCIEN`   |
| PEP active (`active=True` ou flag) | **100**  | `PEP_ACTIF`    |

> **Changement v1.3** : en v1.2, la requête filtrait sur `active=True` — une
> PEP ayant quitté ses fonctions était invisible et recevait une note de 0.
> La GAFI (R.12 §14) exige une vigilance renforcée pendant **5 ans minimum**
> après la fin du mandat. La requête ne filtre plus sur `active`, et une
> ancienne PEP reçoit désormais la note 50.

> **Note** : la gestion des proches de PEP (entourage familial) est hors scope
> v1.3 — la table `pep_relationships` n'est pas présente dans le schéma actuel
> (roadmap V2).

**Logique** :

```python
# 1. Flag dur positionné manuellement par le compliance officer
if customer.statut_pep:
    return 100.0

# 2. Recherche pep_list SANS filtre active — [v1.3]
#    order_by active.desc() : PEP active prioritaire si doublon de nom
match = db.query(PepEntry)\
    .filter(PepEntry.nom.ilike(customer.nom),
            PepEntry.prenom.ilike(customer.prenom))\
    .order_by(PepEntry.active.desc())\
    .first()

if match:
    return 100.0 if match.active else 50.0   # [v1.3] ancienne PEP = 50
return 0.0
```

```python
# Exemple : Fatima OUÉDRAOGO (PEP avérée, active)
note_c5 = 100.0   # contribution = 100 × 0.15 = 15.0

# Exemple : Koffi BIAOU (ancien ministre, date_fin = 2023)
note_c5 = 50.0    # contribution = 50 × 0.15 = 7.5 — vigilance résiduelle
```

---

### C6 — Cohérence KYC (poids 10 %)

**Sources** :
- `customers_docs` (`valide`, `date_expiration`)
- `customers.kyc_completion` (0–100 %, recalculé par `compute_kyc_completion()`
  à chaque ajout/modification de document)
- `customers.revenus_declares` vs flux transactionnels moyens

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

### Champs étendus retournés par `calculate_score` (v1.3)

`calculate_score()` retourne désormais un dict avec 6 clés. Les 3 premières
sont inchangées (non-breaking). Les 3 nouvelles permettent au router de créer
les alertes fines sans ré-interroger la base.

| Clé                  | Type    | Description                                    |
|----------------------|---------|------------------------------------------------|
| `global_score`       | `int`   | Score 0-100 (existant)                         |
| `risk_category`      | `str`   | FAIBLE / MOYEN / ÉLEVÉ (existant)              |
| `detail_json`        | `dict`  | Contributions C1–C6 (existant)                 |
| `c5_score`           | `float` | Note brute C5 : 0, 50 ou 100 (nouveau)         |
| `smurfing_detected`  | `bool`  | True si smurfing confirmé en C3 (nouveau)      |
| `card_testing_count` | `int`   | Nb micro-tx carte détectées en C3 (nouveau)    |

---

## 6. Détection du smurfing — Anti faux-positifs

Le smurfing (fractionnement) consiste à fractionner un gros versement
en plusieurs petites transactions pour éviter les seuils déclaratifs FATF.

### Algorithme v1.3 — 3 conditions CUMULATIVES

```
Étape 1 : filtrer les transactions suspectes (deux familles — logique OR)

  Famille A — Montant rond classique :
    → montant multiple de 10 000 XOF
    → montant < 500 000 XOF (seuil déclaratif FATF)

  Famille B — Near-threshold [v1.3] :
    → montant entre 400 000 et 499 999 XOF (80 %–100 % du seuil FATF)
    → couvre les montants 495 000, 498 000 XOF… forme la plus courante
       au Bénin (clients de Malanville, Parakou, Cotonou porto)

  → au moins 3 transactions (famille A ou B) → sinon STOP

Étape 2 : vérifier la concentration temporelle
  → toutes les tx suspectes dans une fenêtre ≤ 7 jours
  → span = max(dates) - min(dates)
  → Si span > 7 jours → STOP (transactions étalées = comportement normal)

Étape 3 : vérifier le ratio par rapport aux revenus
  → total_suspects ≥ 3 × revenus_mensuels
  → ignorée si revenus = 0 (non renseigné)
  → Si total_suspects < 3 × revenus → STOP (montants cohérents)

→ Si les 3 conditions passent : smurfing = True → C3 = max(C3, 85)
```

### Pourquoi le near-threshold ? [v1.3]

En v1.2, seuls les multiples de 10 000 XOF étaient ciblés. Or la fraude
la plus fréquente dans la zone UEMOA utilise des montants comme 495 000 XOF,
498 000 XOF — juste sous le seuil déclaratif de 500 000 XOF — qui ne sont
pas toujours des multiples ronds.

```
Exemple near-threshold (v1.3 détecte, v1.2 manquait) :
  transactions sur 4 jours : [495 000, 498 000, 492 000, 496 000]

  Étape 1 : 495 000 % 10 000 ≠ 0 → famille A échoue
            480 000 × 1.0 ≤ montant < 500 000 → famille B ✓
            count = 4 ≥ 3 ✓

  Étape 2 : span = 3 jours ≤ 7 jours ✓
  Étape 3 : total = 1 981 000 XOF > 3 × 120 000 = 360 000 XOF ✓
  → smurfing = True ✅
```

### Cas référence — Élimination des faux positifs (v1.2)

**Cas problématique v1.1** : 4 dépôts de 150 000 XOF espacés de 20 jours.

```
Avec v1.2 / v1.3 :
  Étape 1 : 150 000 % 10 000 == 0 ✓  et  < 500 000 ✓  et  count = 4 ≥ 3 ✓
  Étape 2 : dates espacées de 20j → span = 60j > 7j → STOP ✓
  → smurfing = False ✅
```

**Cas réel de smurfing** (Fatima OUÉDRAOGO) :

```
Transactions sur 5 jours : [450 000, 460 000, 440 000, 450 000, 480 000, 430 000]

  Étape 1 : tous multiples de 10k ✓, tous < 500k ✓, count = 6 ≥ 3 ✓
  Étape 2 : span = 4 jours ≤ 7 jours ✓
  Étape 3 : total = 2 710 000 XOF > 3 × 120 000 = 360 000 XOF ✓
  → smurfing = True → C3 = 85 → contribution = 85 × 0.25 = 21.25 ✅
```

---

## 7. Détections comportementales complémentaires

### 7.1 Card testing

**Principe** : un fraudeur en possession d'une carte volée effectue plusieurs
micro-transactions pour vérifier que la carte est active avant de réaliser
une fraude de grande ampleur.

> **Périmètre** : détection **comportementale uniquement** — la validité
> technique de la carte (numéro Luhn, date d'expiration) est gérée par le
> service dédié existant dans le backend.

**Signal détecté dans C3** :

```python
card_micro_tx = [
    tx for tx in transactions
    if "CARTE" in tx.type_op.upper()
    and 0 < float(tx.montant) <= 1_000   # XOF
]
```

| Nb micro-tx carte ≤ 1 000 XOF (90j) | Note C3 minimale | Alerte créée    |
|--------------------------------------|------------------|-----------------|
| ≥ 5                                  | 75               | `CARD_TESTING`  |
| ≥ 2                                  | 45               | — (score pénalisé) |

---

### 7.2 Transactions dupliquées / replay

**Principe** : une même transaction est soumise plusieurs fois, soit par
erreur (double-clic côté client) soit intentionnellement (replay d'un
identifiant de transaction intercepté).

**Algorithme** :

```python
# Clé de regroupement : (montant arrondi à la centaine, destination, compte source)
# Tolérance de 100 XOF pour absorber les variations de frais
key = (round(float(tx.montant), -2), tx.destination_pays_id, tx.compte_id)

# Fenêtre de détection : 24 heures
if (dates_sorted[i] - dates_sorted[i-1]).total_seconds() < 86_400:
    → groupe suspect
```

| Nb groupes suspects (24 h) | Note C3 minimale |
|---------------------------|------------------|
| ≥ 3                       | 60               |
| ≥ 1                       | 40               |

---

## 8. Catégorisation du risque

```python
def _get_category(self, score: int) -> str:
    _NORMALIZE = {
        "ELEVE": "ÉLEVÉ", "ÉLEVÉ": "ÉLEVÉ",
        "MOYEN": "MOYEN", "FAIBLE": "FAIBLE"
    }
    for threshold in sorted(self._thresholds, key=lambda t: t["min_score"]):
        if threshold["min_score"] <= score <= threshold["max_score"]:
            return _NORMALIZE.get(threshold["category"].upper(), threshold["category"])

    # Fallback absolu
    if score <= 33: return "FAIBLE"
    if score <= 66: return "MOYEN"
    return "ÉLEVÉ"
```

**Normalisation appliquée à 3 niveaux** (double et triple sécurité) :

| Niveau | Fichier | Mécanisme |
|--------|---------|-----------|
| 1      | `scoring.py` | `_get_category()` — au calcul |
| 2      | `routers/scoring.py` | `_normalize_category()` — à la lecture depuis `Score.categorie` |
| 3      | `schemas/score.py` | Validateur Pydantic `@field_validator` |

---

## 9. Système d'alertes

Les alertes sont créées par `alert_service.py` après chaque calcul de score.
Chaque type est **distinct et filtrable indépendamment** dans le dashboard
compliance — les alertes fines ne sont pas noyées dans `SCORE_ELEVE`.

### Types d'alertes

| Type           | Déclencheur                                    | Priorité    |
|----------------|------------------------------------------------|-------------|
| `SCORE_ELEVE`  | `global_score ≥ 67`                            | Standard    |
| `PEP_ACTIF`    | `c5_score == 100` (PEP en fonction)            | **Critique**|
| `PEP_ANCIEN`   | `c5_score == 50` (ancienne PEP — GAFI 5 ans)   | Haute       |
| `SMURFING`     | `smurfing_detected == True`                    | Haute       |
| `CARD_TESTING` | `card_testing_count ≥ 5`                       | Haute       |
| `KYC_INCOMPLET`| `kyc_completion < 40 %`                        | Modérée     |

> **Note** : `PEP_DETECTE` est conservé dans le code comme alias de
> rétrocompatibilité — ne pas l'utiliser pour les nouveaux développements.

### Politique anti-doublon

| Contexte                    | `skip_if_open` | Comportement                        |
|-----------------------------|----------------|-------------------------------------|
| Scoring initial (`POST /scoring`) | `False` | Toutes les alertes sont créées      |
| Rescore unitaire (`POST /scoring/rescore`) | `True` | Pas de doublon si alerte déjà OPEN |
| Rescore global (`POST /scoring/rescore-all`) | `True` | Idem — batch protégé    |

### Flux de création des alertes dans le router

```python
# Étape 5 — alerte générique
create_score_alert_if_needed(db, customer_id, result["global_score"], skip_if_open)

# Étape 6 — alertes fines (fonction helper _create_fine_alerts)
create_pep_alert_if_needed(db, customer_id, result["c5_score"], skip_if_open)
if result["smurfing_detected"]:
    create_smurfing_alert_if_needed(db, customer_id, skip_if_open)
create_card_testing_alert_if_needed(db, customer_id, result["card_testing_count"], skip_if_open)
```

---

## 10. Flux complet d'un appel API

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
    ├── 1. Customer.exists ? → 404 si non
    ├── 2. ScoringEngine.calculate_score(uuid)
    │       ├── _load_weights()           ← DB: scoring_criteria
    │       ├── _load_thresholds()        ← DB: risk_thresholds
    │       ├── _score_c1..c6()           ← calculs LBC/FT
    │       │   └── C3 : smurfing, near-threshold, card testing, dupes [v1.3]
    │       │   └── C5 : ancienne PEP → 50, active → 100 [v1.3]
    │       └── _get_category()           ← normalisation ELEVE→ÉLEVÉ
    ├── 3. Score.is_current → False       ← archivage ancien score
    ├── 4. Score(is_current=True)         ← persistance nouveau score
    ├── 5. Alert(SCORE_ELEVE) ?           ← si global_score ≥ 67
    ├── 6. Alertes fines [v1.3] :
    │       ├── Alert(PEP_ACTIF|PEP_ANCIEN)  ← selon c5_score
    │       ├── Alert(SMURFING) ?            ← si smurfing_detected
    │       └── Alert(CARD_TESTING) ?        ← si card_testing_count ≥ 5
    ├── 7. AuditLog(SCORING_CALCULATE)    ← traçabilité réglementaire
    └── 8. db.commit()
    │
    ▼
ScoreResponse { id, customer_id, global_score, risk_category,
                detail_json, is_current, scored_by, scored_at }
```

---

## 11. Corrections v1.2 et v1.3

### v1.2 (inchangé)

| # | Fix | Fichier | Description |
|---|-----|---------|-------------|
| 1 | `_load_weights` sans `is_active` | `scoring.py` | Le champ `is_active` n'existe pas dans `scoring_criteria`. |
| 2 | Normalisation `ELEVE` → `ÉLEVÉ` | `scoring.py`, `routers/scoring.py`, `schemas/score.py` | Appliquée à 3 niveaux. |
| 3 | Anti faux-positifs smurfing | `scoring.py` | 3 conditions cumulatives : count ≥ 3, span ≤ 7j, total ≥ 3× revenus. |
| 4 | `datetime.utcnow()` déprécié | `scoring.py`, `routers/scoring.py` | Remplacé par `datetime.now(timezone.utc)`. |
| 5 | Sécurité `or []` | `scoring.py` | `customer.accounts or []` et `customer.documents or []` partout. |
| 6 | Timezone naive/aware | `scoring.py` | `Transaction.date_op` est `Column(DateTime)` sans tz en base PostgreSQL — cutoff strippé avant requête SQL. |

### v1.3 (nouveautés)

| # | Fix | Fichier | Description |
|---|-----|---------|-------------|
| 7 | `_score_c5` — ancienne PEP | `scoring.py` | Requête sans filtre `active`. Ancienne PEP (`active=False`) → note 50 au lieu de 0. Aligné GAFI R.12 §14. |
| 8 | Card testing comportemental | `scoring.py` | Détection micro-tx carte répétées (≤ 1 000 XOF) dans C3. Périmètre comportemental uniquement — validité technique gérée ailleurs. |
| 9 | Near-threshold smurfing | `scoring.py` | Montants 80–100 % du seuil FATF (400k–499k XOF) ajoutés aux suspects en plus des montants ronds. |
| 10 | Transactions dupliquées | `scoring.py` | Nouvelle méthode `_detect_duplicates()` — même montant arrondi + même destination dans 24 h. |
| 11 | Champs étendus `calculate_score` | `scoring.py` | `c5_score`, `smurfing_detected`, `card_testing_count` ajoutés au dict résultat (non-breaking). |
| A | Nouveaux types d'alertes | `alert_service.py` | `PEP_ACTIF`, `PEP_ANCIEN`, `CARD_TESTING` ajoutés. `PEP_DETECTE` conservé en alias. |
| B | `create_pep_alert_if_needed` | `alert_service.py` | Différencie PEP active (100→`PEP_ACTIF`) et ancienne PEP (50→`PEP_ANCIEN`). |
| C | `create_card_testing_alert_if_needed` | `alert_service.py` | Alerte dédiée card testing (seuil : ≥ 5 micro-tx). |
| D | `create_smurfing_alert_if_needed` | `alert_service.py` | Alerte SMURFING dédiée, séparée de SCORE_ELEVE. |
| Int-1 | Intégration router `_run_scoring` | `routers/scoring.py` | Appel de `_create_fine_alerts()` après `create_score_alert_if_needed`. |
| Int-2 | Intégration `rescore_all_customers` | `routers/scoring.py` | Même intégration pour le rescoring global du portefeuille. |

---

## 12. Exemples de scores attendus

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

### Koffi BIAOU — Profil MOYEN (ancien élu local)

| Critère | Note brute | Poids | Contribution |
|---------|-----------|-------|-------------|
| C1 Profil (HIGH, commerçant transfrontalier) | 65 | 0.20 | 13.0 |
| C2 Zone (FRONTIERE, Bénin) | 65 | 0.20 | 13.0 |
| C3 Transactions (pics × 2.5, virements vers Togo/Nigeria) | 55 | 0.25 | 13.75 |
| C4 Ancienneté (2 ans) | 35 | 0.10 | 3.5 |
| C5 PEP (**ancienne PEP**, date_fin 2023) | **50** | 0.15 | **7.5** |
| C6 KYC (partiel, doc expirant bientôt) | 30 | 0.10 | 3.0 |
| **TOTAL** | | | **53.75 → 54** |

**Score** : 54/100 — **MOYEN** ✅  
→ Alerte `PEP_ANCIEN` créée — surveillance renforcée GAFI 5 ans.

> **v1.2** : C5 = 0 (ancienne PEP non détectée) → score = 46/100  
> **v1.3** : C5 = 50 → score = 54/100 — conforme GAFI R.12

---

### Fatima OUÉDRAOGO — Profil ÉLEVÉ

| Critère | Note brute | Poids | Contribution |
|---------|-----------|-------|-------------|
| C1 Profil (HIGH, changeur devises) | 65 | 0.20 | 13.0 |
| C2 Zone (FRONTIERE + pays frontalier) | 65 | 0.20 | 13.0 |
| C3 Transactions (smurfing + card testing + destinations FATF) | 85 | 0.25 | 21.25 |
| C4 Ancienneté (< 6 mois, cliente récente) | 75 | 0.10 | 7.5 |
| C5 PEP (avérée — flag + liste CENTIF, active) | 100 | 0.15 | 15.0 |
| C6 KYC (incomplet, doc invalide + expiré) | 85 | 0.10 | 8.5 |
| **TOTAL** | | | **78.25 → 78** |

**Score** : 78/100 — **ÉLEVÉ** ✅  
→ Alertes créées : `SCORE_ELEVE`, `PEP_ACTIF`, `SMURFING`

---

## 13. Dépendances inter-modules

```
scoring.py (v1.3)
  ├── models/customers.py          (Customer)
  ├── models/transactions.py       (Transaction)
  ├── models/customer_accounts.py  (CustomerAccount)
  ├── models/customer_docs.py      (CustomerDoc)
  ├── models/pep_list.py           (PepEntry — requête sans filtre active [v1.3])
  ├── models/countries.py          (Country)
  ├── models/risk_zones.py         (RiskZone)
  ├── models/scoring_criteria.py   (ScoringCriteria) ← poids dynamiques
  └── models/risk_thresholds.py    (RiskThreshold)   ← seuils dynamiques

routers/scoring.py (v1.3)
  ├── services/scoring.py          (ScoringEngine)
  ├── services/alert_service.py
  │     ├── create_score_alert_if_needed      (existant)
  │     ├── create_pep_alert_if_needed        (nouveau [v1.3])
  │     ├── create_smurfing_alert_if_needed   (nouveau [v1.3])
  │     └── create_card_testing_alert_if_needed (nouveau [v1.3])
  ├── services/audit_service.py    (log_action)
  ├── models/scores.py             (Score)
  └── schemas/score.py             (ScoringRequest, ScoreResponse, ...)

schemas/score.py
  └── pydantic (BaseModel, field_validator)

models/alerts.py
  └── type_alerte : String(50) libre — pas de CHECK CONSTRAINT PostgreSQL
      Valeurs v1.3 : SCORE_ELEVE | KYC_INCOMPLET | SMURFING
                     PEP_ACTIF   | PEP_ANCIEN    | CARD_TESTING
                     PEP_DETECTE (alias rétrocompatibilité)
```

---

*Document généré le 21 mai 2026 — RiskGuard v1.3*
