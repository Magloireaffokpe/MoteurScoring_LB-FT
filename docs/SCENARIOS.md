# Scénarios — RiskGuard (Scoring LBC/FT)

**Version :** 1.0 — Mai 2026
**Contexte :** Institutions de Microfinance (IMF) béninoises
**Référentiel :** Approche basée sur les risques — Loi uniforme UEMOA / GIABA / FATF

---

## A. Scénarios de test (données générées)

Trois profils clients obligatoires créés par `generate_fake_data.py`. Utilisés pour valider le moteur de scoring.

| # | Client | Profil | Risque | Score attendu |
|---|--------|--------|--------|---------------|
| A | Amélie SOGLO | Institutrice, Cotonou, KYC complet, tx régulières | FAIBLE | < 34 |
| B | Koffi BIAOU | Commerçant transfrontalier, Malanville, pics de tx | MOYEN | 34-66 |
| C | Fatima OUÉDRAOGO | PEP + changeur, smurfing Nigeria, KYC invalide | ÉLEVÉ | ≥ 67 |

### Scénario A — Amélie SOGLO (risque FAIBLE)

**Données socio-démographiques :**
- 38 ans, institutrice à Cotonou (Littoral)
- Mariée, 2 enfants, relation bancaire de 4 ans
- Revenus : 185 000 FCFA/mois (fonction publique)

**Profil bancaire :**
- Compte épargne (solde moyen : 550 000 FCFA)
- CNI valide (2+ ans) + passeport valide (4+ ans)
- KYC completion : 95 % — dossier complet

**Activité transactionnelle (mensuelle) :**
- 1 dépôt guichet : 80 000 FCFA
- 1 retrait ATM : 50 000 FCFA
- 1 paiement mobile : 30 000 FCFA
- 1 virement internet (local) : 40 000 FCFA

**Pourquoi le score est FAIBLE :**
- C1 : Fonctionnaire public = risque LOW
- C2 : Transactions régulières, montants cohérents avec le revenu
- C3 : Zone capitale, pays Bénin (non FATF)
- C4 : Compte épargne standard
- C5 : Canaux variés mais classiques (guichet, ATM, mobile, internet)
- C6 : 2 documents valides, loin d'expirer

### Scénario B — Koffi BIAOU (risque MOYEN)

**Données socio-démographiques :**
- 42 ans, commerçant transfrontalier à Malanville (Alibori, frontière Niger/Nigéria)
- Célibataire, relation bancaire de 2 ans
- Revenus : 350 000 FCFA/mois (déclarés)
- Profession risque : HIGH (commerce transfrontalier)

**Profil bancaire :**
- Compte courant (solde moyen : 1 250 000 FCFA)
- CNI valide + passeport expirant dans 20 jours
- KYC completion : 65 % — dossier partiel

**Activité transactionnelle (mensuelle) :**
- Transactions régulières mais pics x2,5 (anomaly_factor)
- 3 virements internationaux vers Nigéria/Togo (200 000 - 600 000 FCFA)
- 7 retraits cash guichet (100 000 - 300 000 FCFA)

**Pourquoi le score est MOYEN :**
- C1 : Profession HIGH (commerce transfrontalier)
- C2 : Pics de transactions x2,5 par rapport au revenu déclaré
- C3 : Zone frontière, virements vers Nigéria et Togo
- C4 : Compte courant standard
- C5 : Internet + guichet
- C6 : Passeport expire dans 20 jours (pénalisé mais pas bloquant)

### Scénario C — Fatima OUÉDRAOGO (risque ÉLEVÉ)

**Données socio-démographiques :**
- 51 ans, changeur de devises informel à Malanville (Alibori)
- Épouse de ministre de l'Économie (PEP avérée)
- Relation bancaire très récente : 45 jours
- Revenus déclarés : 120 000 FCFA/mois (très bas vs activité réelle)
- Profession risque : HIGH (changeur)

**Profil bancaire :**
- Compte courant (solde moyen : 5 000 000 FCFA — très élevé vs revenus déclarés)
- CNI invalide (expirée depuis 10 jours) + passeport expiré (depuis 30 jours)
- KYC completion : 25 % — dossier très incomplet

**Activité transactionnelle :**
- **Smurfing** : 6 virements de 400 000 - 490 000 FCFA vers Nigéria (juste sous 500 000)
- 3 virements de 450 000 - 490 000 FCFA vers Libye (pays FATF)
- 5 retraits cash massifs (300 000 - 490 000 FCFA) au guichet

**Pourquoi le score est ÉLEVÉ :**
- C1 : PEP avérée (liste CENTIF) + profession HIGH + revenus incohérents
- C2 : Fractionnement (smurfing), montants > 1 000 000 FCFA/semaine
- C3 : Zone frontière, destination Nigéria (frontière) + Libye (FATF)
- C4 : Compte courant récent avec gros volumes
- C5 : Internet (virements) + guichet (retraits cash)
- C6 : Aucun document valide (CNI expirée, passeport expiré)

---

## B. Cas d'utilisation métier (Use Cases)

### UC-01 : Connexion au système
| Élément | Valeur |
|---------|--------|
| Acteur | Administrateur, Agent Compliance |
| Déclencheur | Accès à l'URL de l'application |
| Flux | Saisir login/password → système vérifie → JWT cookie posé |
| Post-condition | Session active 8h, redirection vers Dashboard |
| Alternatif | 3 échecs → rate limit 5 min |

### UC-02 : Visualiser le tableau de bord
| Élément | Valeur |
|---------|--------|
| Acteur | Tout utilisateur authentifié |
| Données | KPIs en temps réel (total clients, alertes ouvertes, score moyen, PEP) |
| Rafraîchissement | Polling automatique toutes les 30 secondes |

### UC-03 : Lister et rechercher des clients
| Élément | Valeur |
|---------|--------|
| Acteur | Tout utilisateur authentifié |
| Filtres | Nom, prénom, phone, email, status, kyc_level, zone_geo |
| Tri | Par date_creation (défaut), nom, score |
| Pagination | 25 par page, max 1000 |

### UC-04 : Consulter la fiche client détaillée
| Élément | Valeur |
|---------|--------|
| Acteur | Tout utilisateur authentifié |
| Onglets | KYC (infos + docs + comptes), Scoring (jauge + radar + C1-C6), Alertes |
| Actions | Voir historique des scores, exporter PDF |

### UC-05 : Créer un nouveau client
| Élément | Valeur |
|---------|--------|
| Acteur | Agent Compliance, Administrateur |
| Flux | Stepper 3 étapes (identité → profession/résidence → validation) |
| Post-condition | Client créé + scoring automatique déclenché |

### UC-06 : Modifier un client
| Élément | Valeur |
|---------|--------|
| Acteur | Agent Compliance, Administrateur |
| Champs modifiables | Coordonnées, profession, résidence, statut PEP, status |
| Champs figés | Nom, prénom, date de naissance |

### UC-07 : Créer un compte bancaire
| Élément | Valeur |
|---------|--------|
| Acteur | Agent Compliance, Administrateur |
| Types | COURANT, EPARGNE |
| Info | Solde moyen, date ouverture, status |

### UC-08 : Ajouter un document KYC
| Élément | Valeur |
|---------|--------|
| Acteur | Agent Compliance, Administrateur |
| Types | CNI, PASSEPORT, CARTE_RESIDENT, PERMIS_CONDUIRE |
| Validation | Date d'expiration → document valide/invalide |

### UC-09 : Enregistrer une transaction
| Élément | Valeur |
|---------|--------|
| Acteur | Agent Compliance, Administrateur |
| Flux | Saisie transaction → auto-rescore → création alerte si nécessaire |
| Types | DEPOT, RETRAIT, VIREMENT, PAIEMENT |
| Canaux | GUICHET, MOBILE, INTERNET, ATM |

### UC-10 : Calculer le score LBC/FT
| Élément | Valeur |
|---------|--------|
| Acteur | Agent Compliance, Administrateur, Système (automatique) |
| Déclencheurs | Création client, nouvelle transaction, rescore manuel, rescore batch |
| Critères | C1 (profil) + C2 (transactionnel) + C3 (géographique) + C4 (produit) + C5 (canal) + C6 (KYC) |
| Résultat | Score 0-100 + catégorie FAIBLE/MOYEN/ÉLEVÉ |

### UC-11 : Gérer les alertes
| Élément | Valeur |
|---------|--------|
| Acteur | Agent Compliance, Administrateur |
| Flux | Liste des alertes → filtrer → ouvrir → décider (clôture/SAR) |
| Types d'alerte | SMURFING, CARD_TESTING, HIGH_RISK_COUNTRY, PEP, MANUAL_REVIEW |

### UC-12 : Déclarer un SAR (Suspicious Activity Report)
| Élément | Valeur |
|---------|--------|
| Acteur | Agent Compliance, Administrateur |
| Post-condition | Rapport PDF généré au format CENTIF Bénin, alerte marquée SAR |

### UC-13 : Administrer les critères de scoring
| Élément | Valeur |
|---------|--------|
| Acteur | Administrateur uniquement |
| Action | Modifier le poids (0-100) de chaque critère C1-C6 |
| Impact | Le rescore recalcule tous les scores avec les nouveaux poids |

### UC-14 : Gérer la liste PEP
| Élément | Valeur |
|---------|--------|
| Acteur | Administrateur uniquement |
| Actions | Ajout manuel, import CSV, activation/désactivation |

### UC-15 : Consulter le journal d'audit
| Élément | Valeur |
|---------|--------|
| Acteur | Administrateur uniquement |
| Traçabilité | Qui a fait quoi, sur quel client, depuis quelle IP, à quel moment |

### UC-16 : Exporter des données
| Élément | Valeur |
|---------|--------|
| Acteur | Agent Compliance, Administrateur |
| Exports | Fiche client PDF, transactions CSV, rapport SAR PDF |

---

## C. Règles métier

### Règle 1 — Catégorisation du score
```
FAIBLE : 0-33  → Surveillance normale
MOYEN  : 34-66 → Surveillance renforcée
ÉLEVÉ  : 67-100 → Déclaration CENTIF obligatoire
```

### Règle 2 — Valeurs des critères (poids modifiables)

| Code | Nom | Poids défaut | Déclencheurs |
|------|-----|-------------|--------------|
| C1 | Profil client | 15 % | Profession à risque, PEP, incohérence revenus |
| C2 | Transactionnel | 20 % | Smurfing, montant > 1M FCFA, volume hebdo |
| C3 | Géographique | 20 % | Zone frontière/FATF, virements internationaux |
| C4 | Produit/Service | 15 % | Type de compte, ancienneté |
| C5 | Canal | 15 % | Internet, mobile (vs guichet) |
| C6 | KYC | 15 % | Document invalide/expiré, KYC incomplet |

### Règle 3 — Délais de traitement
- Alerte non traitée → escalade après 7 jours ouvrés
- Score recalculé automatiquement à chaque nouvelle transaction
- Rescore batch de tous les clients possible depuis l'API

### Règle 4 — Conservation des données
- Scores archivés (historique complet, `is_current` pour le score actif)
- Audit logs conservés indéfiniment
- Transactions conservées (pas de purge automatique)

---

## D. Rôles et permissions

| Rôle | Dashboard | Clients (lecture) | Clients (écriture) | Admin | Exports |
|------|-----------|-------------------|-------------------|-------|---------|
| ADMIN | ✓ | ✓ | ✓ | ✓ | ✓ |
| COMPLIANCE | ✓ | ✓ | ✓ | ✗ | ✓ |

**Note :** Le rôle `VIEWER` (lecture seule) n'est pas implémenté dans cette version.

---

## E. Diagrammes de séquence (flux critiques)

### Flux 1 : Connexion
```
Utilisateur → Frontend       : Saisit login/password
Frontend    → POST /auth/login : {login, password}
Backend     → Base de données : Vérifie credentials
Backend     → Frontend       : JWT + cookie httpOnly
Frontend    → GET /auth/me   : Valide la session (silent=true)
Backend     → Frontend       : {id, login, role, is_active}
Frontend    → DashboardPage  : Redirection
```

### Flux 2 : Création de transaction avec auto-rescore
```
Agent      → Frontend          : Remplit le formulaire transaction
Frontend   → POST /customers/{id}/transactions : {compte_id, montant, type_op, ...}
Backend    → Base de données   : INSERT transaction
Backend    → ScoringEngine     : _score()
Backend    → Base de données   : INSERT score (is_current=true, ancien → false)
Backend    → AlertService      : Vérifie seuils → INSERT alerte si score > 66
Backend    → Frontend          : {transaction, new_score_global, new_score_category}
Frontend   → Affiche           : Transaction créée + nouveau score
```

### Flux 3 : Rescore batch
```
Admin      → Frontend              : Clique "Recalculer tous les scores"
Frontend   → POST /scoring/rescore-all : (requête)
Backend    → Pour chaque client    : _score(client)
Backend    → Base de données       : 503x INSERT score
Backend    → AlertService          : Vérifie seuils
Backend    → Frontend              : {rescored: 503, critical: 12}
Frontend   → Affiche notification  : "503 scores recalculés, 12 clients critiques"
```
