# GitHub Workflow — Conventions Git

Voir la documentation complète dans GITHUB_WORKFLOW_PROFESSIONNEL.md du projet

## Principes

✅ Un commit = une tâche atomique
✅ Messages clairs : type(scope): subject
✅ Branches : feature/fix/docs/chore
✅ Pull requests obligatoires avant merger
✅ Code review requise

## Commandes essentielles

```bash
# Créer branche
git checkout develop
git pull origin develop
git checkout -b feature/marcos/ma-tache

# Committer
git add app/file.py
git commit -m "feat(scope): description"

# Pousser
git push -u origin feature/marcos/ma-tache
```

## Avant la PR

☐ Tests passent
☐ Linting OK
☐ Pas de .env/secrets commités
☐ Message commit clair
☐ Assigné au binôme
