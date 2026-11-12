# CleanTandem — publication sur Railway (préproduction uniquement)

## Ce qui est prêt

- Page commerciale `/`, démo autonome accessible sans inscription `/demo.html`, espace de test avec inscription sur invitation `/app.html`.
- API FastAPI, sessions HTTP-only, protection CSRF, isolation des organisations, base PostgreSQL prise en charge.
- Build Docker et configuration Railway, endpoint de santé `/health`, interface responsive.
- **Ce n'est pas encore un SaaS commercialisable : données fictives uniquement.**

## Déployer sans installer Python sur votre ordinateur

1. Connecter l'application Railway à ChatGPT ; créer ensuite un projet Railway et y rattacher ce code source, ou importer le projet depuis un dépôt Git privé.
2. Dans Railway, ajouter le service PostgreSQL administré ; paramétrer `CT_DATABASE_URL` avec la chaîne interne PostgreSQL du service.
3. Paramétrer `CT_PUBLIC_ORIGIN` à l'URL HTTPS exacte de l'application et `CT_REGISTRATION_CODE` avec une valeur aléatoire de 20+ caractères. Ne jamais renseigner `CT_DEV_ALLOW_INSECURE`.
4. Utiliser le Dockerfile et le fichier railway.toml fournis. Déployer puis vérifier `/health`, `/`, `/demo.html`, `/app.html`.
5. Faire une recette réelle dans un navigateur sur le service publié. Donner le code d'invitation seulement à des testeurs autorisés et interdire les données réelles.

**Coûts :** Railway et PostgreSQL peuvent générer une facture ; contrôler les tarifs et définir une limite compatible avec le budget maximal de 100 € pour ce mois. Aucun service n'a été créé, aucune dépense n'a été engagée.

## Bloquants avant vente

- Authentification à renforcer : validation d'email, réinitialisation de mot de passe, limitation de débit multi-instance, tests d'intrusion, journalisation et supervision.
- Politique de sauvegardes chiffrées, restauration testée, migrations SQL, contrôle d'accès par rôle, conformité RGPD et conformité des exports réglementaires.
- Éditeur légal et CGV/CGU avec approbation expresse de son identité ; pas de vente avant mise en règle.
- Intégration de paiement type Stripe avec webhooks vérifiés, facturation conforme et suivi d'abonnements ; aucun système de paiement n'est branché.

## Rappel commercial

Prix **envisagé** 49 € HT/mois, sans paiement activé. Priorité : essais de 3 entreprises, validation de l'intérêt, puis lancement légal et sécurisé.