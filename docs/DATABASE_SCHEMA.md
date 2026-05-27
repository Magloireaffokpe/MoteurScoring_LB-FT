# Schéma de la Base de Données — RiskGuard

**Version :** 1.2 — Mai 2026
**Moteur :** PostgreSQL 15+
**Migration :** Alembic (dossier `backend/alembic/`)
**Extensions :** `pgcrypto` (pour UUID)
**Total :** 14 tables

---

## Relations (graphique FK)

```
user_roles ──< users ──< audit_logs
                  │         │
                  │         └── customers
                  │
                  ├── customers (pep_verified_by)
                  ├── customer_docs (verified_by)
                  └── alerts (clos_par)

countries ──< customers ──< customer_docs
    │          │              customer_accounts ──< transactions
    │          │                  │
    │          ├── alerts        transactions (origine_pays_id, destination_pays_id)
    │          ├── scores
    │          └── audit_logs
    │
    └── pep_list

risk_zones ──< customers
```

---

## 1. `countries` — Pays de résidence / origine / destination

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `Integer` | PK | — | auto-incrément |
| 2 | `code_iso` | `String(3)` | NOT NULL | — | **UNIQUE**, ex: BJ, NG, LY |
| 3 | `name` | `String(100)` | NOT NULL | — | Bénin, Nigéria, Libye... |
| 4 | `is_uemoa` | `Boolean` | OUI | `false` | Membre UEMOA |
| 5 | `is_border` | `Boolean` | OUI | `false` | Pays frontalier du Bénin |
| 6 | `is_fatf` | `Boolean` | OUI | `false` | Liste noire FATF |

**FK reçues :** `customers.pays`, `transactions.origine_pays_id`, `transactions.destination_pays_id`, `pep_list.pays`

---

## 2. `risk_zones` — Zones géographiques de risque

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `Integer` | PK | — | auto-incrément |
| 2 | `name` | `String(100)` | NOT NULL | — | CAPITALE, FRONTIERE, RURALE... |
| 3 | `risk_level` | `String(20)` | NOT NULL | — | FAIBLE, MOYEN, ELEVE, TRES_ELEVE |
| 4 | `source` | `Text` | OUI | — | Référence GIABA / CENTIF Bénin |
| 5 | `description` | `Text` | OUI | — | Justificatif du niveau de risque |

**FK reçues :** `customers.zone_geo`

**Données typiques (seed_db.py) :**
| ID | Name | Risk Level |
|----|------|------------|
| 1 | CAPITALE | FAIBLE |
| 2 | URBAINE | FAIBLE |
| 3 | SEMI_URBAINE | MOYEN |
| 4 | RURALE | MOYEN |
| 5 | FRONTIERE | ELEVE |
| 6 | CONFLIT | TRES_ELEVE |

---

## 3. `scoring_criteria` — Critères de scoring (poids modifiables)

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `Integer` | PK | — | auto-incrément |
| 2 | `code` | `String(5)` | NOT NULL | — | **UNIQUE**, C1..C6 |
| 3 | `weight` | `Numeric(5,2)` | NOT NULL | — | 0.00 – 100.00 |
| 4 | `name` | `String(100)` | NOT NULL | — | Profil client, Transactionnel... |
| 5 | `description` | `Text` | OUI | — | Explication détaillée |
| 6 | `updated_by` | `UUID` | OUI | — | FK → `users.id` |
| 7 | `updated_at` | `DateTime` | OUI | `now()` | Auto mis à jour |

**Données initiales (seed_db.py) :**
| Code | Nom | Poids |
|------|-----|-------|
| C1 | Profil professionnel | 20.00 |
| C2 | Zone géographique | 20.00 |
| C3 | Historique transactionnel | 25.00 |
| C4 | Ancienneté et fidélité | 10.00 |
| C5 | Statut PEP | 15.00 |
| C6 | Cohérence KYC | 10.00 |

---

## 4. `risk_thresholds` — Seuils de risque

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `Integer` | PK | — | auto-incrément |
| 2 | `category` | `String(10)` | NOT NULL | — | **UNIQUE**, FAIBLE/MOYEN/ELEVE |
| 3 | `score_min` | `Integer` | NOT NULL | — | Borne inférieure (incluse) |
| 4 | `score_max` | `Integer` | NOT NULL | — | Borne supérieure (incluse) |
| 5 | `action` | `Text` | OUI | — | Action requise |
| 6 | `updated_at` | `DateTime` | OUI | `now()` | Auto mis à jour |

**Données initiales :**
| Catégorie | Min | Max | Action |
|-----------|-----|-----|--------|
| FAIBLE | 0 | 33 | Surveillance normale |
| MOYEN | 34 | 66 | Surveillance renforcée |
| ELEVE | 67 | 100 | Déclaration CENTIF |

---

## 5. `user_roles` — Rôles des utilisateurs

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `Integer` | PK | — | auto-incrément |
| 2 | `name` | `String(50)` | NOT NULL | — | **UNIQUE**, ADMIN / COMPLIANCE |
| 3 | `permissions` | `JSONB` | NOT NULL | `{}` | Décoratif (sécurité via role.name) |

---

## 6. `users` — Utilisateurs du système

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `UUID` | PK | `uuid4()` | Généré automatiquement |
| 2 | `login` | `String(50)` | NOT NULL | — | **UNIQUE** |
| 3 | `password_hash` | `String(255)` | NOT NULL | — | bcrypt hash |
| 4 | `role_id` | `Integer` | NOT NULL | — | FK → `user_roles.id` |
| 5 | `is_active` | `Boolean` | OUI | `true` | Compte actif/désactivé |
| 6 | `last_login` | `DateTime` | OUI | — | Dernière connexion |
| 7 | `created_at` | `DateTime` | OUI | `now()` | Date de création |

---

## 7. `customers` — Clients (table centrale)

**23 colonnes — la table centrale du schéma.**

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `UUID` | PK | `uuid4()` | |
| 2 | `nom` | `String(100)` | NOT NULL | — | |
| 3 | `prenom` | `String(100)` | NOT NULL | — | |
| 4 | `date_naissance` | `Date` | OUI | — | |
| 5 | `phone` | `String(20)` | OUI | — | **UNIQUE**, format +229XXXXXXXX |
| 6 | `email` | `String(150)` | OUI | — | **UNIQUE** |
| 7 | `profession_code` | `String(50)` | OUI | — | Code métier (COMMERCANT...) |
| 8 | `profession_name` | `String(150)` | OUI | — | Libellé profession |
| 9 | `profession_risk` | `String(10)` | OUI | — | LOW / MEDIUM / HIGH |
| 10 | `revenus_declares` | `Numeric(15,2)` | OUI | — | Revenus mensuels FCFA |
| 11 | `city` | `String(100)` | OUI | — | Ville (béninoise) |
| 12 | `region` | `String(100)` | OUI | — | Département (Bénin) |
| 13 | `latitude` | `String(20)` | OUI | — | Coordonnées GPS |
| 14 | `longitude` | `String(20)` | OUI | — | Coordonnées GPS |
| 15 | `zone_geo` | `Integer` | OUI | — | FK → `risk_zones.id`, **indexé** |
| 16 | `pays` | `Integer` | OUI | — | FK → `countries.id`, **indexé** |
| 17 | `statut_pep` | `Boolean` | OUI | `false` | **Indexé** |
| 18 | `pep_verified_by` | `UUID` | OUI | — | FK → `users.id` |
| 19 | `kyc_level` | `String(10)` | OUI | `"LOW"` | **Indexé** |
| 20 | `kyc_completion` | `Integer` | OUI | `0` | % completion |
| 21 | `status` | `String(20)` | OUI | `"ACTIVE"` | ACTIVE / INACTIVE / SUSPENDED |
| 22 | `date_creation` | `DateTime` | OUI | `now()` | Date d'ouverture |
| 23 | `updated_at` | `DateTime` | OUI | `now()` | Auto mis à jour |

**Relations :**
- `customers.risk_zone` → `risk_zones.id`
- `customers.country` → `countries.id`
- `customers.documents` → `customers_docs` (cascade delete)
- `customers.accounts` → `customer_accounts` (cascade delete)
- `customers.alerts` → `alerts`
- `customers.scores` → `scores`

---

## 8. `customers_docs` — Documents KYC des clients

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `UUID` | PK | `uuid4()` | |
| 2 | `client_id` | `UUID` | NOT NULL | — | FK → `customers.id`, CASCADE, **indexé** |
| 3 | `type_doc` | `String(50)` | NOT NULL | — | CNI / PASSEPORT / CARTE_RESIDENT / PERMIS_CONDUIRE |
| 4 | `numero` | `String(100)` | OUI | — | N° de document |
| 5 | `date_expiration` | `Date` | OUI | — | Si passé → document invalide |
| 6 | `verified_by` | `UUID` | OUI | — | FK → `users.id` |
| 7 | `created_at` | `DateTime` | OUI | `now()` | |

**Propriété calculée :** `valide` = `date_expiration >= date.today()`

---

## 9. `customer_accounts` — Comptes bancaires des clients

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `UUID` | PK | `uuid4()` | |
| 2 | `client_id` | `UUID` | NOT NULL | — | FK → `customers.id`, CASCADE, **indexé** |
| 3 | `type_compte` | `String(50)` | OUI | — | COURANT / EPARGNE |
| 4 | `solde_moyen` | `Numeric(15,2)` | OUI | `0` | Solde moyen estimé |
| 5 | `date_ouverture` | `Date` | OUI | — | Date d'ouverture |
| 6 | `status` | `String(50)` | OUI | `"ACTIF"` | ACTIF / INACTIF / BLOQUÉ |
| 7 | `created_at` | `DateTime` | OUI | `now()` | |

**Relations :** `accounts.transactions` → `transactions` (cascade delete)

---

## 10. `transactions` — Transactions financières

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `UUID` | PK | `uuid4()` | |
| 2 | `compte_id` | `UUID` | NOT NULL | — | FK → `customer_accounts.id`, CASCADE, **indexé** |
| 3 | `montant` | `Numeric(15,2)` | NOT NULL | — | En FCFA (XOF) |
| 4 | `devise` | `String(5)` | OUI | `"XOF"` | |
| 5 | `type_op` | `String(50)` | OUI | — | DEPOT / RETRAIT / VIREMENT / PAIEMENT |
| 6 | `date_op` | `DateTime` | OUI | `now()` | **Indexé** |
| 7 | `canal` | `String(50)` | OUI | — | GUICHET / MOBILE / INTERNET / ATM |
| 8 | `origine` | `Text` | OUI | — | Libellé origine |
| 9 | `destination` | `Text` | OUI | — | Libellé destination |
| 10 | `origine_pays_id` | `Integer` | OUI | — | FK → `countries.id`, **indexé** |
| 11 | `destination_pays_id` | `Integer` | OUI | — | FK → `countries.id`, **indexé** |

**Relations :**
- `transactions.account` → `customer_accounts`
- `transactions.origine_pays` → `countries`
- `transactions.destination_pays` → `countries`

---

## 11. `alerts` — Alertes LBC/FT

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `UUID` | PK | `uuid4()` | |
| 2 | `client_id` | `UUID` | NOT NULL | — | FK → `customers.id`, CASCADE, **indexé** |
| 3 | `clos_par` | `UUID` | OUI | — | FK → `users.id` |
| 4 | `type_alerte` | `String(50)` | NOT NULL | — | SCORE_ELEVE / KYC_INCOMPLET / PEP_DETECTE / SMURFING_DETECTE / SEUIL_DEPASSE / BENEFICIAIRE_GROUPEMENT |
| 5 | `statut` | `String(20)` | NOT NULL | `"OPEN"` | OPEN / CLOSED, **indexé** |
| 6 | `decision` | `Text` | OUI | — | Commentaire de clôture |
| 7 | `sar_declare` | `Boolean` | NOT NULL | `false` | SAR transmis à CENTIF |
| 8 | `date_creation` | `DateTime` | OUI | `now()` | |
| 9 | `date_cloture` | `DateTime` | OUI | — | |

---

## 12. `audit_logs` — Journal d'audit

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `UUID` | PK | `uuid4()` | |
| 2 | `user_id` | `UUID` | NOT NULL | — | FK → `users.id`, **indexé** |
| 3 | `client_id` | `UUID` | OUI | — | FK → `customers.id`, **indexé** (nullable pour actions globales) |
| 4 | `action` | `String(100)` | NOT NULL | — | CLIENT_CREATED, SCORE_COMPUTED, ALERT_CLOSED... |
| 5 | `timestamp` | `DateTime` | OUI | `now()` | |
| 6 | `ip_address` | `String(45)` | OUI | — | Adresse IP source |

---

## 13. `pep_list` — Liste des Personnes Exposées Politiquement

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `UUID` | PK | `uuid4()` | |
| 2 | `pays` | `Integer` | OUI | — | FK → `countries.id` |
| 3 | `nom` | `String(100)` | NOT NULL | — | **Indexé** |
| 4 | `prenom` | `String(100)` | NOT NULL | — | |
| 5 | `fonction` | `String(200)` | OUI | — | Ministre, Député, Ambassadeur... |
| 6 | `date_debut` | `Date` | OUI | — | Début du mandat |
| 7 | `date_fin` | `Date` | OUI | — | Fin du mandat (null = en cours) |
| 8 | `source` | `String(100)` | OUI | — | GIABA, CENTIF, ONU |
| 9 | `active` | `Boolean` | NOT NULL | `true` | Auto-computé par trigger SQLAlchemy |

---

## 14. `scores` — Scores LBC/FT

| # | Champ | Type | Nullable | Défaut | Notes |
|---|-------|------|----------|--------|-------|
| 1 | `id` | `UUID` | PK | `uuid4()` | |
| 2 | `client_id` | `UUID` | NOT NULL | — | FK → `customers.id`, **indexé** |
| 3 | `score_global` | `Integer` | NOT NULL | — | 0–100 |
| 4 | `detail_json` | `JSONB` | NOT NULL | — | `{"C1": 15.0, "C2": 10.0, "C3": 0.0, "C4": 5.0, "C5": 2.0, "C6": 10.0}` |
| 5 | `categorie` | `String(10)` | NOT NULL | — | FAIBLE / MOYEN / ELEVE |
| 6 | `is_current` | `Boolean` | OUI | `true` | Un seul `true` par client |
| 7 | `date_calcul` | `DateTime` | OUI | `now()` | |
| 8 | `calcule_par` | `String(50)` | OUI | `"AUTOMATED"` | AUTOMATED / MANUAL |

**Index :** `(client_id, is_current)` partiel pour trouver rapidement le score actif.

---

## Résumé des contraintes

### Index uniques
| Table | Colonne(s) | Raison |
|-------|-----------|--------|
| `countries` | `code_iso` | Un seul pays par code ISO |
| `scoring_criteria` | `code` | C1..C6 uniques |
| `risk_thresholds` | `category` | FAIBLE/MOYEN/ELEVE uniques |
| `user_roles` | `name` | ADMIN, COMPLIANCE uniques |
| `users` | `login` | Login unique |
| `customers` | `phone` | Téléphone unique |
| `customers` | `email` | Email unique |

### Clés étrangères (18 FK)
| Source | Cible | Comportement |
|--------|-------|-------------|
| `customers.zone_geo` | `risk_zones.id` | RESTRICT |
| `customers.pays` | `countries.id` | RESTRICT |
| `customers.pep_verified_by` | `users.id` | SET NULL |
| `customers_docs.client_id` | `customers.id` | **CASCADE** |
| `customers_docs.verified_by` | `users.id` | SET NULL |
| `customer_accounts.client_id` | `customers.id` | **CASCADE** |
| `transactions.compte_id` | `customer_accounts.id` | **CASCADE** |
| `transactions.origine_pays_id` | `countries.id` | RESTRICT |
| `transactions.destination_pays_id` | `countries.id` | RESTRICT |
| `alerts.client_id` | `customers.id` | **CASCADE** |
| `alerts.clos_par` | `users.id` | SET NULL |
| `scores.client_id` | `customers.id` | **CASCADE** (corrigé par migration abc123456789) |
| `audit_logs.user_id` | `users.id` | RESTRICT |
| `audit_logs.client_id` | `customers.id` | SET NULL |
| `pep_list.pays` | `countries.id` | RESTRICT |
| `scoring_criteria.updated_by` | `users.id` | SET NULL |
| `users.role_id` | `user_roles.id` | RESTRICT |

### Cascades DELETE
✅ `customers_docs.client_id → CASCADE`
✅ `customer_accounts.client_id → CASCADE`
✅ `transactions.compte_id → CASCADE`
✅ `alerts.client_id → CASCADE`
✅ `scores.client_id` — **CASCADE** (migration abc123456789)

---

## Statistiques volumétriques (500 clients)

| Table | Lignes estimées |
|-------|----------------|
| `customers` | 503 |
| `customer_accounts` | ~503 |
| `customers_docs` | ~1 000 |
| `transactions` | ~12 000 |
| `scores` | ~1 500 |
| `alerts` | ~20 |
| `pep_list` | ~15 |
| `users` | 3 (admin + agents) |
| `audit_logs` | Variable |

**Taille estimée :** ~50-100 MB (hors index)
