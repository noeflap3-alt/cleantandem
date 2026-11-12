# CleanTandem — déploiement GitHub privé + Railway

**Phase : préproduction avec données fictives exclusivement.** Pas de facturation ni vente activée.

## Mise en ligne

1. Créer un dépôt **privé** `cleantandem` sur GitHub, sans README initial si ChatGPT dépose les fichiers lui-même. Ne rendre le dépôt public à aucun moment.
2. Connecter ce dépôt au projet Railway privé `CleanTandem` déjà créé. Builder : Dockerfile présent à la racine.
3. Ajouter PostgreSQL sur Railway ; vérifier le coût avant de l'activer. Connecter `CT_DATABASE_URL` au `DATABASE_URL` interne de PostgreSQL. **Jamais de mot de passe dans GitHub.**
4. Générer le domaine HTTPS Railway puis définir les variables dans Railway :
   - `CT_PUBLIC_ORIGIN=https://<domaine-railway-exact>` (aucun slash final)
   - `CT_DATABASE_URL=${{Postgres.DATABASE_URL}}` si le service s'appelle Postgres dans Railway (utiliser la référence fournie par Railway)
   - `CT_REGISTRATION_CODE=<code-aléatoire-prive-de-32-caractères-ou-plus>`
   - **Ne pas** créer `CT_DEV_ALLOW_INSECURE`.
5. Déployer et vérifier les pages `/`, `/demo.html`, `/app.html` et `/health`. `/health` doit répondre `status: ok`.
6. Recette : navigateur privé, créer un compte d'essai uniquement avec un code d'invitation ; tester un client **fictif**, un site, un devis et une intervention ; vérifier logout, cookies sécurisés et isolation inter-entreprises.

## Sécurité / juridique avant l'ouverture commerciale

- Aucun client réel, aucun contact client réel, aucun paiement avant audit complet.
- Ajout nécessaire : limitation anti-bruteforce, validation d'adresse mail et réinitialisation sûre du mot de passe, sauvegardes automatiques restaurables, supervision, politique de rétention et conformité RGPD.
- Ajouter CGU/CGV et identification légale de l'éditeur quand l'activité sera lancée ; ne pas exposer inutilement l'identité personnelle dans les emails marketing, mais respecter les mentions légales obligatoires.
- Domaine et ressources Railway peuvent coûter de l'argent en fonction du forfait.

## Tests locaux (facultatifs)

`CT_DEV_ALLOW_INSECURE=1 python -m pytest backend/tests -q`

**Ne jamais définir `CT_DEV_ALLOW_INSECURE=1` sur un service public.**