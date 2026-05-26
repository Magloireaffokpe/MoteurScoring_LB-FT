# Rapport Plateforme — RiskGuard (Scoring LBC/FT)

## Vue d'ensemble

**RiskGuard** est un système automatisé de scoring du risque de blanchiment de capitaux et de financement du terrorisme (LBC/FT) destiné aux institutions de microfinance (IMF) au Bénin. Il calcule un score de risque de 0 à 100 pour chaque client afin d'aider les agents de conformité à identifier les comportements suspects.

---

## 1. Cycle de vie du client sur la plateforme

### 1.1 Création du client

L'agent de conformité crée un client dans le système avec ses informations personnelles :

- Nom, prénom, date de naissance, nationalité
- Profession, revenu mensuel déclaré
- Adresse, zone géographique, téléphone, email

Le système **calcule automatiquement le score de risque** dès la création du client.

### 1.2 Ajout des documents KYC

Pour chaque client, on peut ajouter des pièces justificatives :

- CNI, passeport, permis, attestation, fiche de paie, etc.
- Le système vérifie la **validité des documents** (date d'expiration)
- Le **taux de complétude KYC** est mis à jour automatiquement

### 1.3 Ouverture de comptes

Les comptes bancaires (COURANT ou EPARGNE) sont créés et liés au client.

### 1.4 Enregistrement des transactions

Les transactions (DEPOT, RETRAIT, VIREMENT, PAIEMENT) sont enregistrées avec :

- Montant, date, canal (GUICHET, MOBILE, INTERNET, ATM)
- Pays source/destination

**Chaque transaction déclenche un nouveau calcul du score.**

---

## 2. Le moteur de scoring (cœur du système)

Le score global (0-100) est calculé à partir de **6 critères pondérés** :

### C1 — Profil professionnel (poids : 20 %)

- Évalue le risque associé à la profession du client
- 3 niveaux : FAIBLE (0/100), MOYEN (35/100), ÉLEVÉ (100/100)
- Vérifie la cohérence entre le revenu déclaré et le profil
- Exemples : agriculteur, enseignant → FAIBLE ; commerçant → MOYEN ; bureau de change → ÉLEVÉ

### C2 — Zone géographique (poids : 20 %)

- Évalue le risque de la localisation du client
- 6 zones : CAPITALE, URBAINE, RURALE, FRONTIÈRE, CONFLIT
- Majorations selon le pays : pays listés noirs GAFI, pays frontaliers, pays non-UEMOA

### C3 — Transactions sur 90 jours (poids : 25 %) — **le plus important**

Analyse poussée du comportement transactionnel :

| Détection | Description |
|-----------|-------------|
| **Volume inhabituel** | Ratio volume total / revenu déclaré |
| **Fréquence anormale** | Plus de 5 transactions par jour |
| **Retraits répétés** | Retraits en espèces fréquents |
| **Smurfing** | ≥ 3 transactions suspectes sur 7 jours, total ≥ 3× revenu mensuel, montants proches du seuil (400k-499k XOF) |
| **Card testing** | ≥ 2 micro-transactions ≤ 1 000 XOF sur carte |
| **Duplicatas** | Même montant arrondi + même destination dans 24h |
| **Destinations à risque** | Transactions vers des pays à haut risque |

### C4 — Ancienneté relation client (poids : 10 %)

- < 6 mois → note élevée (risque)
- 6-12 mois → note moyenne
- 1-3 ans → note faible
- \> 3 ans → très faible

### C5 — Statut PPE (poids : 15 %)

Correspond à la norme GAFI R.12 :

- PPE actif → score 100/100
- Ancien PPE → score 50/100
- Aucun → 0/100

### C6 — Cohérence KYC (poids : 10 %)

- Validité des documents
- Cohérence revenu vs transactions
- Taux de complétude du dossier

### Calcul final

```
Score global = (C1 × 0.20) + (C2 × 0.20) + (C3 × 0.25) + (C4 × 0.10) + (C5 × 0.15) + (C6 × 0.10)
```

Les poids sont **configurables** via l'interface admin.

---

## 3. Catégorisation du risque

| Catégorie | Intervalle | Action |
|-----------|-----------|--------|
| **FAIBLE** | 0 – 33 | Aucune action requise |
| **MOYEN** | 34 – 66 | Surveillance renforcée |
| **ÉLEVÉ** | 67 – 100 | Déclaration de soupçon (SAR) |

---

## 4. Génération d'alertes

Après chaque scoring, des alertes sont créées automatiquement si des conditions sont remplies :

- **SCORE_ELEVE** : score global ≥ 67
- **PEP_ACTIF** : PPE actif détecté
- **PEP_ANCIEN** : ancien PPE détecté
- **SMURFING** : tentative de structuration de transactions
- **CARD_TESTING** : micro-transactions suspects sur carte
- **KYC_INCOMPLET** : dossier KYC < 40 % de complétude

Un mécanisme anti-doublon empêche la création d'alertes identiques si une alerte est déjà ouverte.

---

## 5. Export et déclaration

La plateforme permet de générer :

- **Fiche client PDF** — profil complet du client avec score et historique
- **Transactions CSV** — export des transactions pour analyse
- **Rapport de soupçon (SAR) PDF** — format CENTIF Bénin pour déclaration aux autorités

---

## 6. Rôles et accès

| Rôle | Permissions |
|------|------------|
| **Admin** | Accès complet : configuration des poids, seuils, gestion des utilisateurs, import liste PPE |
| **Agent de conformité** | Opérations quotidiennes : gestion clients, scoring, alertes, exports |

Authentification par JWT (8h de validité) avec limitation de taux (5 tentatives/min/IP).

---

## 7. Tableau de bord

Le dashboard présente en temps réel :

- Nombre total de clients
- Répartition par catégorie de risque (FAIBLE/MOYEN/ÉLEVÉ)
- Alertes ouvertes
- Score moyen de la plateforme
- Nombre de PPE

---

## 8. Flux complet (résumé)

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

---

## 9. Conformité réglementaire

Le système s'aligne sur :

- **Recommandations du GAFI** (R.1, R.12, R.16, R.20, R.29)
- **Directives BCEAO** pour les IMF de l'UEMOA
- **CENTIF Bénin** pour les déclarations de soupçon
- Loi n° 2018-16 sur le LBC/FT au Bénin
