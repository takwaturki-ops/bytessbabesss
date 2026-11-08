# Plan de travail — Authentification Backend

*Technologies :* Node.js, Express, PostgreSQL (Neon), bcrypt, JWT, 2FA (TOTP).

## 1. Fonctionnalités à développer

- Register : inscription d'un utilisateur.
- Login : connexion avec email et mot de passe.
- bcrypt : hachage des mots de passe.
- JWT : génération et vérification des tokens.
- Middleware : protection des routes privées.
- Logout : gestion de la désconnexion côté client.
- **2FA (double authentification) :** activation TOTP, envoi du code, vérification au login, désactivation.

## 2. Routes API

- POST /api/auth/register
- POST /api/auth/login
- GET /api/auth/me

## 3. Structure souhaitée

- routes/authRoutes.js
- controllers/authController.js
- middlewares/authMiddleware.js
- services/2faService.js (si séparé)

## 4. Remarques importantes pour éviter les conflits

- Utiliser la connexion PostgreSQL existante (config/database.js), ne pas créer une deuxième connexion.
- Utiliser la base Neon existante, ne pas créer un autre projet ou une autre base.
- Ne pas modifier server.js sans coordination avec la personne responsable du backend.
- Ne pas créer un deuxième serveur Express.
- Ne jamais stocker les mots de passe en clair.
- Vérifier que l'email est unique.
- Utiliser des variables d'environnement pour le secret JWT (JWT_SECRET).
- Ne jamais envoyer le mot de passe ou le hash dans les réponses JSON.

## 5. À la fin

Fournir les routes, les exemples de requêtes/réponses et les instructions pour intégrer et tester l'authentification.
