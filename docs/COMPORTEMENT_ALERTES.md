# Comportement des alertes et flux associés

> Document technique — RiskGuard | Scoring LBC/FT  
> Version : 1.0 — Mai 2026

---

## 1. Cycle de vie des alertes

### 1.1 Transitions possibles

```
OPEN ──→ UNDER_REVIEW ──→ CLOSED
  │                        ▲
  └────────────────────────┘
     (direct, sans review)
```

Toutes les transitions sont acceptées — il n'y a **pas de machine à états** dans le code.

### 1.2 Endpoint

`PUT /alerts/{alert_id}` — accessible à `compliance_officer` et `admin`.

Corps accepté :
```json
{
  "statut": "OPEN" | "UNDER_REVIEW" | "CLOSED",
  "decision": "texte libre",
  "sar_declare": true | false
}
```

### 1.3 Comportement à la clôture

Quand `statut = CLOSED`, le endpoint enregistre automatiquement :
- `clos_par` ← UUID de l'agent connecté
- `date_cloture` ← datetime UTC courante

### 1.4 Anti-doublon

Toutes les fonctions de création (`create_score_alert_if_needed`, `create_pep_alert_if_needed`, `create_smurfing_alert_if_needed`, `create_kyc_alert_if_needed`, `create_if_not_open`) vérifient systématiquement via `has_open_alert()` qu'aucune alerte OPEN du même type n'existe déjà pour ce client.

Seules les alertes CLOSED peuvent être ré-ouvertes par un nouveau déclenchement.

---

## 2. Ordre exact des opérations — POST /transactions

Quand une transaction est créée, les étapes s'enchaînent dans cet ordre :

```
1. Validation      → Vérifie que le compte appartient au client
2. Persistance     → INSERT transaction + db.flush()
3. Audit           → log_action("CREATE_TRANSACTION")
4. AUTO-RESCORE    → ScoringEngine.calculate_score()
                     ├── Archive ancien score (is_current=false)
                     ├── Persiste nouveau score
                     ├── create_score_alert_if_needed()    → SCORE_ELEVE
                     ├── create_pep_alert_if_needed()      → PEP_DETECTE
                     ├── create_smurfing_alert_if_needed() → SMURFING_DETECTE
                     └── create_kyc_alert_if_needed()      → KYC_INCOMPLET
5. SEUIL GLOBAL    → Cumul toutes opérations (30j) ≥ SEUIL_MONETAIRE (10M XOF)
                     └── create_if_not_open()              → SEUIL_DEPASSE
6. SEUIL ESPÈCES   → Cumul DEPOT GUICHET/ATM (30j) ≥ SEUIL_ESPECES (3M XOF)
                     └── create_if_not_open()              → SEUIL_DEPASSE
7. BÉNÉFICIAIRE    → check_and_alert(tx, db)
                     (seulement si VIREMENT ou PAIEMENT avec destination)
                     └── Crée BENEFICIAIRE_GROUPEMENT si seuils atteints
8. Commit          → db.commit() + retour réponse
```

Les erreurs de scoring (étape 4) sont catchées et loggées sans bloquer la transaction — le
reste de la chaîne (seuils, bénéficiaire) continue de s'exécuter.

---

## 3. Alerte SEUIL_DEPASSE

- **Déclenchée après** le rescore (pas avant)
- **Anti-doublon** : utilise `create_if_not_open()` qui vérifie `has_open_alert()`
- **Deux sous-types** dans le même code d'alerte :
  - Toutes opérations confondues (`SEUIL_MONETAIRE`, défaut 10 000 000 XOF)
  - Espèces uniquement (`SEUIL_ESPECES`, défaut 3 000 000 XOF)
- **Fenêtre configurable** : `FENETRE_CUMUL_JOURS` (défaut 30 jours)
- **Paramètres modifiables** via `PUT /admin/settings/{key}`
- **N'est pas créée par `alert_service.py`** mais directement dans `routers/transactions.py`

---

## 4. Service bénéficiaire groupement

- **Fichier :** `services/beneficiaire_service.py` (122 lignes)
- **Fonction unique :** `check_and_alert(transaction, db)`
- **Appelé uniquement depuis** `POST /transactions` (ligne 195), pas de batch ni d'endpoint dédié
- **Condition :** seulement si `type_op in ("VIREMENT", "PAIEMENT")` ET `destination` non vide
- **Seuils :**
  - ≥ 2 clients distincts vers le même bénéficiaire
  - Ou ≥ 5 transactions vers ce bénéficiaire
  - Ou ≥ 5 000 000 FCFA cumulés vers ce bénéficiaire
- **Fenêtre :** `FENETRE_CUMUL_JOURS` (défaut 30 jours)
- **Normalisation :** minuscule, suppression accents (pas de similarité textuelle avancée)

---

## 5. Catalogue des 49 endpoints (12 routers)

### admin.py (13 endpoints — admin uniquement)

| Verbe | Route | Fonction |
|-------|-------|----------|
| GET | `/scoring-criteria` | `get_scoring_criteria` |
| PUT | `/scoring-criteria/{criteria_id}` | `update_scoring_criteria` |
| GET | `/risk-thresholds` | `get_risk_thresholds` |
| PUT | `/risk-thresholds/{threshold_id}` | `update_risk_threshold` |
| GET | `/settings` | `get_settings` |
| PUT | `/settings/{key}` | `update_setting` |
| GET | `/users` | `list_users` |
| POST | `/users` | `create_user` |
| PUT | `/users/{user_id}/toggle-active` | `toggle_user_active` |
| PUT | `/users/{user_id}/reset-password` | `reset_user_password` |
| POST | `/pep-list/import` | `import_pep_list` |
| POST | `/pep-list` | `add_pep_entry` |
| GET | `/audit-logs` | `get_audit_logs` |

### alerts.py (5 endpoints — compliance + admin)

| Verbe | Route | Fonction |
|-------|-------|----------|
| GET | `/alerts` | `list_alerts` |
| GET | `/alerts/{alert_id}` | `get_alert` |
| POST | `/alerts` | `create_alert` |
| PUT | `/alerts/{alert_id}` | `update_alert` |
| GET | `/customers/{customer_id}/alerts` | `get_customer_alerts` |

### auth.py (2 endpoints — public)

| Verbe | Route | Fonction |
|-------|-------|----------|
| POST | `/auth/login` | `login` |
| GET | `/auth/me` | `get_me` |

### customer_accounts.py (3 endpoints — compliance + admin)

| Verbe | Route | Fonction |
|-------|-------|----------|
| GET | `/customers/{customer_id}/accounts` | `get_customer_accounts` |
| GET | `/accounts/{account_id}` | `get_account` |
| POST | `/customers/{customer_id}/accounts` | `create_account` |

### customer_docs.py (3 endpoints — compliance + admin)

| Verbe | Route | Fonction |
|-------|-------|----------|
| GET | `/customers/{customer_id}/documents` | `get_customer_documents` |
| GET | `/documents/{doc_id}` | `get_document` |
| POST | `/customers/{customer_id}/documents` | `create_document` |

### customers.py (4 endpoints — compliance + admin)

| Verbe | Route | Fonction |
|-------|-------|----------|
| GET | `/clients` | `list_clients` |
| GET | `/clients/{customer_id}` | `get_client` |
| POST | `/clients` | `create_client` |
| PUT | `/clients/{customer_id}` | `update_client` |

### dashboard.py (3 endpoints — compliance + admin)

| Verbe | Route | Fonction |
|-------|-------|----------|
| GET | `/dashboard/stats` | `get_dashboard_stats` |
| GET | `/dashboard/alerts` | `get_dashboard_alerts` |
| GET | `/dashboard/pep` | `get_pep_clients` |

### exports.py (3 endpoints — compliance + admin)

| Verbe | Route | Fonction |
|-------|-------|----------|
| GET | `/exports/customer/{customer_id}/pdf` | `export_customer_pdf` |
| GET | `/exports/transactions/{customer_id}/csv` | `export_transactions_csv` |
| GET | `/exports/sar/{alert_id}/pdf` | `export_sar_pdf` |

### pep.py (1 endpoint — compliance + admin)

| Verbe | Route | Fonction |
|-------|-------|----------|
| GET | `/pep` | `list_pep` |

### referentials.py (4 endpoints — GET public, POST/PUT admin)

| Verbe | Route | Fonction |
|-------|-------|----------|
| GET | `/countries` | `get_countries` |
| POST | `/countries` | `create_country` |
| PUT | `/countries/{country_id}` | `update_country` |
| GET | `/risk-zones` | `get_risk_zones` |

### scoring.py (5 endpoints — compliance + admin)

| Verbe | Route | Fonction |
|-------|-------|----------|
| POST | `/scoring` | `create_scoring` |
| POST | `/scoring/rescore` | `rescore_customer` |
| GET | `/scores/{score_id}` | `get_score` |
| GET | `/customers/{customer_id}/scores` | `get_customer_scores` |
| POST | `/scoring/rescore-all` | `rescore_all_customers` |

### transactions.py (3 endpoints — compliance + admin)

| Verbe | Route | Fonction |
|-------|-------|----------|
| GET | `/customers/{customer_id}/transactions` | `get_customer_transactions` |
| GET | `/transactions/{transaction_id}` | `get_transaction` |
| POST | `/customers/{customer_id}/transactions` | `create_transaction` |

---

## 6. Rescore batch

`POST /scoring/rescore-all` est déclaré `async def` mais **exécuté de façon synchrone** (aucun `await`, pas de `BackgroundTasks`, pas de Celery).

- Traite par lots de 20 clients avec `db.commit()` intermédiaire
- Les erreurs individuelles sont catchées et loggées, le batch continue
- Un seul audit log `ACTION_SCORING_RESCORE_ALL` en fin de traitement
- Bloque la requête HTTP jusqu'à la fin

---

## 7. Administration

### Fonctionnalités admin disponibles

| Domaine | Endpoint | Description |
|---------|----------|-------------|
| Poids scoring | `PUT /scoring-criteria/{id}` | Modifier les poids C1-C6 (validation somme = 100%) |
| Seuils risque | `PUT /risk-thresholds/{id}` | Modifier les bornes FAIBLE/MOYEN/ELEVE (validation contiguïté) |
| Paramètres | `PUT /settings/{key}` | Ajuster SEUIL_MONETAIRE, SEUIL_ESPECES, FENETRE_CUMUL_JOURS |
| Utilisateurs | `POST /users` | Créer un agent (admin ou compliance_officer) |
| Utilisateurs | `PUT /users/{id}/toggle-active` | Activer/désactiver (auto-désactivation interdite) |
| Utilisateurs | `PUT /users/{id}/reset-password` | Réinitialiser le mot de passe |
| PEP | `POST /pep-list/import` | Import CSV avec dédoublonnage nom+prénom |
| PEP | `POST /pep-list` | Ajout manuel |
| Pays | `POST /countries`, `PUT /countries/{id}` | Créer/modifier un pays |
| Audit | `GET /audit-logs` | Logs filtrés (user_id, action, pagination) |

**Principe :** Aucun endpoint DELETE — les entrées sont modifiées ou désactivées, jamais supprimées.
