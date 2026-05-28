# CHANGELOG — RiskGuard (Scoring LBC/FT)

**Date :** 28 mai 2026  
**Version :** 1.3  
**Migration :** `cb780a8f74e2` — Ajout de 3 colonnes à la table `alerts`

---

## Résumé des modifications

### 🗄️ Base de données — Migration `cb780a8f74e2`

**3 colonnes ajoutées à `alerts` :**

| Colonne | Type | Contrainte | But |
|---------|------|-----------|-----|
| `score_id` | `UUID` | FK → `scores.id`, ON DELETE SET NULL | Lier l'alerte au score qui l'a déclenchée |
| `beneficiaire_nom` | `String(200)` | NULL | Nom normalisé du bénéficiaire suspect (alerte BENEFICIAIRE_GROUPEMENT) |
| `tx_ids` | `JSONB` | NULL | `["uuid1","uuid2"]` — UUIDs des transactions liées à l'alerte |

**Changements post-migration :**
- `FK alerts.score_id → scores.id` avec `ON DELETE SET NULL`
- Migration hors `.gitignore` → versionnée comme les 4 migrations existantes

---

### 🔧 Backend — Modèles

**`app/models/alerts.py` :**
- Ajout des 3 colonnes SQLAlchemy : `score_id`, `beneficiaire_nom`, `tx_ids` (JSONB)
- Nouvelle relation `score = relationship("Score")`

**`app/models/scores.py` :**
- Ajout de la relation inverse : `alerts = relationship("Alert")`

---

### 🔧 Backend — Schémas Pydantic

**`app/schemas/alert.py` :**
- `AlertCreate` : ajout des champs optionnels `score_id`, `beneficiaire_nom`, `tx_ids`
- `AlertResponse` : ajout des 3 champs en lecture
- Nouveau schéma `BeneficiaireGroupement` pour l'endpoint groupements

---

### 🔧 Backend — Routers

**`app/routers/alerts.py` :**
- Nouveau : `GET /alerts/groupements/beneficiaire` — liste des bénéficiaires suspects
- Nouveau : `GET /alerts/groupements/beneficiaire/{nom}` — détail d'un groupement
- Total endpoints alerts : 5 → 7

**`app/routers/scoring.py` :**
- Passage de `score_id=new_score.id` aux alertes `SCORE_ELEVE`, `PEP_DETECTE`, `SMURFING_DETECTE`

**`app/routers/transactions.py` :**
- Passage de `score_id=score.id` et `tx_ids=[tx.id]` aux alertes seuil

---

### 🔧 Backend — Services

**`app/services/alert_service.py` :**
- `create_alert()` : nouveaux paramètres `score_id`, `tx_ids`, `beneficiaire_nom`
- `create_if_not_open()` : idem
- Fix UUID → str : conversion `[str(u) for u in tx_ids]` pour compatibilité SQLite

**`app/services/beneficiaire_service.py` :**
- Passage de `beneficiaire_nom=dest_normalized` et `tx_ids=[transaction.id]`

---

### 🐍 Backend — Scripts

**`scripts/generate_fake_data.py` et `scripts/clean_fake_data.py` :**
- Ordre cleanup inversé : `Alert.delete()` avant `Score.delete()` (plus logique)

---

### 🎨 Frontend

**Nouveau fichier :**
- `src/pages/AlertDetailPage.jsx` — page dédiée `/alerts/:id` avec client lié, score (ScorePanel), transactions liées

**Modifications :**
- `src/App.jsx` : route `/alerts/:id`
- `src/pages/AlertsPage.jsx` : onglet "Groupements bénéficiaires" + modale avec liste des clients cliquables
- `src/pages/ClientDetailPage.jsx` : colonne type alerte cliquable → `/alerts/:id`
- `src/services/alertService.js` : méthodes `listGroupements()` et `getGroupementDetail(nom)`

---

### 🐛 Bugs corrigés

| Bug | Cause | Fichier | Solution |
|-----|-------|---------|----------|
| ScorePanel affiche 420.75/100 | `Object.entries()` incluait `C1_raw`…`C6_raw` | `ScorePanel.jsx` | `.filter(([key]) => /^C[1-6]$/.test(key))` |
| Montant affiche "XOF XOF" | `formatAmount(v) + row.devise` | `AlertsPage.jsx` | `formatAmount(v, row.devise)` |
| `TypeError: UUID not JSON serializable` | `tx_ids` contenait des UUID Python | `alert_service.py` | `tx_ids_str = [str(u) for u in tx_ids]` |

---

### 📚 Documentation mise à jour

| Fichier | Changement |
|---------|-----------|
| `DATABASE_SCHEMA.md` | 3 colonnes alerts + FK score_id |
| `API_CONTRACT.md` | 2 nouveaux endpoints + réponse enrichie (47→49 routes) |
| `COMPORTEMENT_ALERTES.md` | Table alerts 5→7 endpoints |
| `SCENARIOS.md` | Nouveau scénario D — Bénéficiaire groupé |
| `DEPLOYMENT.md` | Migration checklist |
| `TESTING_GUIDE.md` | Dépannage UUID + stats tests |

---
