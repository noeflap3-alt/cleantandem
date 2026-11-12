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
## Liens et état du 12 novembre 2026

- **Démo publique (données fictives uniquement)** : https://cleantandem-demo-production.up.railway.app/
- **Démo interactive** : https://cleantandem-demo-production.up.railway.app/demo.html
- Le service public actuel est une **Railway Function**, dont le code déployé a été synchronisé manuellement avec `frontend/index.html`, `frontend/demo.html`, `frontend/demo.js` et `frontend/styles.css`.
- **Attention : les commits GitHub ne redéploient PAS encore automatiquement** le site. Il faut autoriser le dépôt privé dans les intégrations GitHub du compte Railway puis rattacher la source.
- `Dockerfile` démarre la démo statique isolée. `Dockerfile.backend` conserve la configuration expérimentale FastAPI/PostgreSQL pour une future préproduction sécurisée.
- Pas de base clients réelle, pas de paiement, pas d'abonnement commercialisable ; ne jamais importer de données personnelles réelles.
