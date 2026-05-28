# Contrat API — RiskGuard (Scoring LBC/FT)

**Version :** 1.2 — Mai 2026
**Base URL (dev) :** `http://localhost:8000`
**Base URL (prod) :** `https://moteurscoring-lb-ft.onrender.com`
**Frontend :** `https://moteur-scoring-lb-ft.vercel.app`
**Auth :** JWT (Bearer) via cookie `access_token` (httpOnly, secure, samesite=lax)
**Content-Type :** `application/json` (sauf uploads multipart)
**Docs auto :** `/docs` (Swagger) | `/redoc` (ReDoc)
**Health :** `GET /` → `{"status":"ok","app":"RiskGuard API","version":"1.0.0"}`

---

## Codes d'erreur standard

| Code | Signification |
|------|---------------|
| 400 | Requête invalide |
| 401 | Non authentifié (token manquant/expiré) |
| 403 | Accès refusé (rôle insuffisant) |
| 404 | Ressource introuvable |
| 409 | Conflit (doublon email/phone) |
| 422 | Validation Pydantic échouée |
| 429 | Rate limit dépassé (login : 5/min) |
| 500 | Erreur serveur interne |

---

## 1. Authentification — `/auth`

### `POST /auth/login`
Connexion — retourne un JWT (8h) + cookie httpOnly.

**Rate limit :** 5 req/min/IP

**Request :**
```json
{ "login": "admin", "password": "***" }
```

**Response 200 :**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user_id": "uuid",
  "role": "admin"
}
```

**Erreurs :** 401 (bad credentials), 429 (rate limit)

### `GET /auth/me`
Infos de l'utilisateur courant. Utilisé pour revalider une session cookie.

**Response 200 :**
```json
{ "id": "uuid", "login": "admin", "role": "admin", "is_active": true }
```

---

## 2. Clients — `GET /api/clients`

**Permissions :** tous les utilisateurs authentifiés (GET) | `require_compliance_or_admin` (POST/PUT)

### `GET /api/clients`
Liste paginée des clients.

**Query params :** `skip` (0), `limit` (25, max 1000), `search` (nom/prenom/phone/email), `status`, `kyc_level`, `statut_pep` (bool), `zone_geo`

**Response 200 :**
```json
{
  "items": [
    {
      "id": "uuid", "nom": "SOGLO", "prenom": "Amélie",
      "phone": "+22966110001", "email": "amelie@imf-test.bj",
      "profession_code": "FONCT_PUBL", "profession_name": "Institutrice",
      "profession_risk": "LOW", "revenus_declares": 185000.0,
      "city": "Cotonou", "region": "Littoral",
      "zone_geo": 1, "pays": 1,
      "kyc_level": "LOW", "kyc_completion": 95,
      "statut_pep": false, "status": "ACTIVE",
      "date_creation": "2025-01-15T10:30:00"
    }
  ],
  "total": 500,
  "skip": 0,
  "limit": 25
}
```

### `GET /api/clients/{customer_id}`
Détail complet d'un client.

**Response 200 :** mêmes champs que ci-dessus + `date_naissance`, `latitude`, `longitude`, `updated_at`, `documents[]`, `accounts[]`

### `POST /api/clients`
Créer un client. Déclenche scoring automatique (si algorithme actif).

**Request :**
```json
{
  "nom": "BIAOU", "prenom": "Koffi", "date_naissance": "1990-05-15",
  "phone": "+22966123456", "email": "koffi@example.bj",
  "profession_code": "COMMERCANT", "revenus_declares": 500000,
  "pays": 1, "zone_geo": 1,
  "city": "Cotonou", "region": "Littoral"
}
```

**Champs obligatoires :** `nom`, `prenom`, `profession_code`, `phone`
**Champs optionnels :** `email`, `date_naissance`, `revenus_declares`, `pays`, `zone_geo`, `city`, `region`, `statut_pep`, `kyc_completion`, `kyc_level`, `status`

**Response 201 :** `CustomerSummary`

### `PUT /api/clients/{customer_id}`
Modifier un client.

**Champs modifiables :** `phone`, `email`, `profession_code`, `profession_name`, `profession_risk`, `revenus_declares`, `pays`, `zone_geo`, `city`, `region`, `statut_pep`, `status`, `kyc_completion`, `kyc_level`
**Champs ignorés (identité figée) :** `nom`, `prenom`, `date_naissance`

**Response 200 :** `CustomerSummary`

---

## 3. Alertes — `/api`

**Permissions :** tous utilisateurs (GET) | `require_compliance_or_admin` (POST/PUT)

### `GET /api/alerts`
Liste paginée/filtrée des alertes.

**Query params :** `skip` (0), `limit` (25), `statut` (OPEN/CLOSED), `type_alerte`, `sar_declare` (bool)

**Response 200 :**
```json
{
  "items": [{
    "id": "uuid", "client_id": "uuid",
    "type_alerte": "SCORE_ELEVE", "statut": "OPEN",
    "decision": null, "sar_declare": false,
    "score_id": "uuid", "beneficiaire_nom": null, "tx_ids": null,
    "date_creation": "2026-05-21T10:30:00", "date_cloture": null,
    "clos_par": null
  }],
  "total": 20,
  "skip": 0,
  "limit": 25
}
```

**Types d'alertes utilisés par le système :**

| Type | Déclencheur |
|------|-------------|
| `SCORE_ELEVE` | Score global ≥ 67 |
| `PEP_DETECTE` | Correspondance PEP active ou ancienne (c5_score ≥ 50) |
| `SMURFING_DETECTE` | Fractionnement probable détecté dans C3 |
| `KYC_INCOMPLET` | Taux de complétion KYC < 40 % |
| `SEUIL_DEPASSE` | Dépassement de seuil transactionnel |
| `BENEFICIAIRE_GROUPEMENT` | Bénéficiaire suspect lié à un groupement |

### `GET /api/alerts/{alert_id}`
Détail d'une alerte. Inclut les champs `score_id`, `beneficiaire_nom`, `tx_ids` si renseignés.

### `GET /api/alerts/groupements/beneficiaire`
Liste des bénéficiaires suspects regroupés (alerte `BENEFICIAIRE_GROUPEMENT`).

**Response 200 :**
```json
[
  {
    "beneficiaire_nom": "OUEDRAOGO FATIMA",
    "nb_clients": 3,
    "nb_transactions": 7,
    "premiere_alerte": "2026-05-21T10:30:00",
    "derniere_alerte": "2026-05-25T14:00:00"
  }
]
```

### `GET /api/alerts/groupements/beneficiaire/{nom}`
Détail d'un groupement : liste des alertes pour ce bénéficiaire.

### `GET /api/customers/{customer_id}/alerts`
Alertes d'un client spécifique.

### `POST /api/alerts`
Créer une alerte manuelle.

**Request :**
```json
{
  "client_id": "uuid",
  "type_alerte": "SCORE_ELEVE",
  "statut": "OPEN",
  "decision": null,
  "sar_declare": false
}
```

**Note :** le champ `type_alerte` accepte toute chaîne (ex: `PEP_DETECTE`, `SMURFING_DETECTE`, `KYC_INCOMPLET`).

**Response 201 :** `AlertResponse`

### `PUT /api/alerts/{alert_id}`
Mettre à jour une alerte (clôture, déclaration SAR, décision).

**Request :**
```json
{
  "statut": "CLOSED",
  "decision": "Alerte confirmée après vérification documentaire",
  "sar_declare": true
}
```

**Response 200 :** `AlertResponse`

---

## 4. Dashboard — `/api/dashboard`

**Permissions :** tous utilisateurs authentifiés

### `GET /api/dashboard/stats`
KPIs globaux en temps réel.

**Response 200 :**
```json
{
  "total_clients": 503,
  "total_clients_high_risk": 45,
  "total_clients_medium_risk": 120,
  "total_clients_low_risk": 338,
  "kyc_completion_rate": 72.5,
  "open_alerts": 18,
  "avg_score_global": 38.2,
  "pep_count": 15,
  "transactions_30d": 1200,
  "total_pep_entries": 15
}
```

### `GET /api/dashboard/alerts`
5 dernières alertes ouvertes.

### `GET /api/dashboard/pep`
Clients marqués PEP actifs.

---

## 5. Administration — `/api/admin`

**Permissions :** `require_admin` uniquement

### `GET /api/admin/scoring-criteria`
Liste des 6 critères de scoring avec leurs poids.

**Response 200 :**
```json
{
  "items": [
    { "id": 1, "code": "C1", "name": "Profil professionnel", "weight": 20.00 },
    { "id": 2, "code": "C2", "name": "Zone géographique", "weight": 20.00 },
    { "id": 3, "code": "C3", "name": "Historique transactionnel", "weight": 25.00 },
    { "id": 4, "code": "C4", "name": "Ancienneté et fidélité", "weight": 10.00 },
    { "id": 5, "code": "C5", "name": "Statut PEP", "weight": 15.00 },
    { "id": 6, "code": "C6", "name": "Cohérence KYC", "weight": 10.00 }
  ],
  "total": 6
}
```

### `PUT /api/admin/scoring-criteria/{criteria_id}`
Modifier le poids d'un critère.

**Query params :** `weight` (float, 0-100)

**Response 200 :** `{ "message": "Poids du critère C3 mis à jour à 30.00" }`

### `GET /api/admin/risk-thresholds`
Seuils de risque.

**Response 200 :**
```json
{
  "items": [
    { "id": 1, "category": "FAIBLE", "score_min": 0, "score_max": 33, "action": "Surveillance normale" },
    { "id": 2, "category": "MOYEN",  "score_min": 34, "score_max": 66, "action": "Surveillance renforcée" },
    { "id": 3, "category": "ELEVE",  "score_min": 67, "score_max": 100, "action": "Déclaration CENTIF" }
  ],
  "total": 3
}
```

### `PUT /api/admin/risk-thresholds/{threshold_id}`
Modifier un seuil.

**Request :** `{ "score_min": 30, "score_max": 65, "action": "Surveillance renforcée" }`

### `GET /api/admin/users`
Liste des utilisateurs du système.

### `POST /api/admin/users`
Créer un nouvel utilisateur.

**Request :** `{ "login": "agent01", "password": "securePass123", "role_name": "COMPLIANCE" }`

**Response 201 :** `{ "id": "uuid", "login": "agent01", "role": "COMPLIANCE", "is_active": true }`

### `PUT /api/admin/users/{user_id}/toggle-active`
Activer/désactiver un utilisateur.

### `PUT /api/admin/users/{user_id}/reset-password`
Réinitialiser le mot de passe.

**Request :** `{ "new_password": "newSecurePass456" }`

### `POST /api/admin/pep-list/import`
Importer une liste PEP depuis un fichier CSV (multipart/form-data).

### `POST /api/admin/pep-list`
Ajouter manuellement une entrée PEP.

**Request :**
```json
{
  "nom": "ADJAGBA", "prenom": "Alassane",
  "fonction": "Ministre de l'Économie",
  "pays": 1,
  "source": "CENTIF",
  "date_debut": "2020-01-01",
  "date_fin": null
}
```

### `GET /api/admin/audit-logs`
Journal d'audit filtré.

**Query params :** `skip`, `limit`, `user_id`, `action`

---

## 6. Comptes clients — `/api`

**Permissions :** tous utilisateurs (GET) | `require_compliance_or_admin` (POST)

### `GET /api/customers/{customer_id}/accounts`
Liste des comptes d'un client.

### `GET /api/accounts/{account_id}`
Détail d'un compte.

### `POST /api/customers/{customer_id}/accounts`
Créer un compte.

**Request :** `{ "type_compte": "COURANT", "solde_moyen": 500000, "date_ouverture": "2026-01-01", "status": "ACTIF" }`

---

## 7. Documents KYC — `/api`

**Permissions :** tous utilisateurs (GET) | `require_compliance_or_admin` (POST)

### `GET /api/customers/{customer_id}/documents`
Liste des documents d'un client.

### `GET /api/documents/{doc_id}`
Détail d'un document.

### `POST /api/customers/{customer_id}/documents`
Ajouter un document.

**Request :** `{ "type_doc": "CNI", "numero": "CNI1234567", "date_expiration": "2028-05-21" }`

---

## 8. Transactions — `/api`

**Permissions :** tous utilisateurs (GET) | `require_compliance_or_admin` (POST)

### `GET /api/customers/{customer_id}/transactions`
Liste paginée des transactions d'un client.

**Query params :** `skip`, `limit`, `days` (nb jours dans le passé), `type_op`

### `GET /api/transactions/{transaction_id}`
Détail d'une transaction.

### `POST /api/customers/{customer_id}/transactions`
Créer une transaction. Déclenche **auto-rescore** du client et **création d'alerte** si le score dépasse un seuil.

**Request :**
```json
{
  "compte_id": "uuid",
  "montant": 500000.00,
  "devise": "XOF",
  "type_op": "VIREMENT",
  "canal": "INTERNET",
  "origine": "Compte personnel",
  "destination": "Fournisseur Nigéria",
  "origine_pays_id": 1,
  "destination_pays_id": 2
}
```

**Response 201 :** inclut `TransactionResponse` + `new_score_global` (int) + `new_score_category` (string)

---

## 9. PEP — `/api`

### `GET /api/pep`
Liste paginée des entrées PEP.

**Query params :** `skip`, `limit`, `search` (nom/prénom), `active` (bool)

---

## 10. Référentiels — `/api`

**Permissions :** tous utilisateurs (GET) | `require_admin` (POST pays)

### `GET /api/countries`
Liste des pays.

**Response 200 :**
```json
[
  { "id": 1, "code_iso": "BJ", "name": "Bénin", "is_uemoa": true, "is_border": false, "is_fatf": false },
  { "id": 2, "code_iso": "NG", "name": "Nigéria", "is_uemoa": false, "is_border": true, "is_fatf": false },
  { "id": 3, "code_iso": "LY", "name": "Libye", "is_uemoa": false, "is_border": false, "is_fatf": true }
]
```

### `POST /api/countries`
Ajouter un pays.

### `GET /api/risk-zones`
Liste des zones géographiques.

---

## 11. Scoring — `/api`

**Permissions :** tous utilisateurs (GET) | `require_compliance_or_admin` (POST)

### `POST /api/scoring`
Calculer le score initial d'un client (C1-C6, smurfing).

**Request :** `{ "customer_id": "uuid" }`

### `POST /api/scoring/rescore`
Re-calculer le score (remplace le score courant).

**Request :** `{ "customer_id": "uuid" }`

### `POST /api/scoring/rescore-all`
Re-calculer le score de **tous** les clients.

**Response 200 :**
```json
{ "rescored": 503, "critical": 12 }
```

### `GET /api/scores/{score_id}`
Détail d'un score spécifique.

### `GET /api/customers/{customer_id}/scores`
Historique des scores d'un client.

**Response Score :**
```json
{
  "id": "uuid", "customer_id": "uuid",
  "score_global": 42, "risk_category": "MOYEN",
  "scored_by": "AUTOMATED", "scored_at": "2026-05-21T10:30:00",
  "is_current": true,
  "detail_json": { "C1": 15.0, "C2": 10.0, "C3": 0.0, "C4": 5.0, "C5": 2.0, "C6": 10.0 }
}
```

---

## 12. Exports — `/api/exports`

**Permissions :** `require_compliance_or_admin`

### `GET /api/exports/customer/{customer_id}/pdf`
Fiche client PDF (StreamingResponse).

### `GET /api/exports/transactions/{customer_id}/csv`
Transactions CSV.

**Query params :** `days` (default 90, max 730)

### `GET /api/exports/sar/{alert_id}/pdf`
Rapport SAR CENTIF Bénin (PDF).

---

## Résumé des permissions

| Niveau | Routes | Rôle requis |
|--------|--------|-------------|
| **Public** | `GET /` (health) | Aucun |
| **Auth simple** | `POST /auth/login` | Aucun |
| **Utilisateur** | `GET /auth/me`, `GET /api/clients`, `GET /api/alerts`, `GET /api/dashboard/*`, `GET /api/pep`, `GET /api/countries`, `GET /api/risk-zones`, `GET /api/scores/*`, `GET /api/customers/*/scores`, `GET /api/customers/*/accounts`, `GET /api/customers/*/documents`, `GET /api/customers/*/transactions` | `get_current_user` |
| **Compliance + Admin** | `POST/PUT /api/clients`, `POST/PUT /api/alerts`, `POST /api/customers/*/accounts`, `POST /api/customers/*/documents`, `POST /api/customers/*/transactions`, `POST /api/scoring/*`, `GET /api/exports/*` | `require_compliance_or_admin` |
| **Admin only** | `GET/PUT /api/admin/*`, `POST /api/countries` | `require_admin` |

---

## Total : 49 routes

| Module | Routes | GET | POST | PUT |
|--------|--------|-----|------|-----|
| Auth | 2 | 1 | 1 | — |
| Clients | 4 | 2 | 1 | 1 |
| Alertes | 7 | 5 | 1 | 1 |
| Dashboard | 3 | 3 | — | — |
| Admin | 11 | 4 | 3 | 4 |
| Comptes | 3 | 2 | 1 | — |
| Documents | 3 | 2 | 1 | — |
| Transactions | 3 | 2 | 1 | — |
| PEP | 1 | 1 | — | — |
| Référentiels | 3 | 2 | 1 | — |
| Scoring | 5 | 2 | 3 | — |
| Exports | 3 | 3 | — | — |
| Health | 1 | 1 | — | — |
| **Total** | **49** | **30** | **13** | **6** |
