# CleanTandem — édition pilote 12 novembre 2026

## Statut : prêt pour hébergement de démonstration, pas pour vente

- `/` : page d’accueil responsive, 49 € HT/mois annoncé comme **tarif envisagé**.
- `/demo.html` : vraie démo interactive, sans compte, données fictives dans le navigateur.
- `/app.html` : environnement pilote backend FastAPI, inscriptions par code en hébergement et organisations séparées.
- `/health` : contrôle de santé serveur et base.
- Déploiement Docker compatible Railway ; voir `DEPLOIEMENT_SANS_PYTHON.md`.

### Tests exécutés

- 7 tests API existants réussis.
- Le parcours navigateur simulé couvre l'accueil, 5 vues de démo, la création d’un client fictif et l'affichage mobile (pas d'erreur JavaScript détectée).
- 6 routes du serveur vérifiées avec FastAPI TestClient.
- **Le vrai déploiement cloud et le checkout ne sont pas encore réalisés.**

### Limites

Aucune donnée réelle ; pas de vente ni de facture ; nom/prénom de l'éditeur non publiés ; pas de paiement.
Une connexion à un hébergeur Railway (ou équivalent) est nécessaire pour obtenir un lien public vers cette version.