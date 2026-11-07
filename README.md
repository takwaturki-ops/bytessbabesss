# SmartFin AI

Prototype réalisé pendant le hackathon **TechX ENIT x ENICarthage 2026-2027**, défi **The Autonomous FinTech Team**.

SmartFin AI est une équipe d'agents IA spécialisés qui gère un parcours client et financier de bout en bout : présenter une offre, comprendre les besoins et objections du client, accompagner un paiement **simulé**, analyser les résultats, proposer des améliorations et contrôler les risques de sécurité.

> Toutes les données sont fictives. Aucun vrai paiement n'est déclenché, aucune donnée bancaire n'est collectée ou stockée.

## Les agents

| Agent | Rôle | Type |
| --- | --- | --- |
| Voice Sales Agent | Présente les formations, répond au client, détecte l'intention d'achat | LLM |
| Customer Intelligence Agent | Extrait besoins, objections, niveau d'intérêt et sentiment | LLM |
| Payment Agent | Simule le paiement et suit son statut | Règles codées |
| Financial Data Analyst | Résume les KPI calculés en SQL | LLM sur KPI calculés |
| Business Strategy Agent | Propose des recommandations justifiées par les données | LLM |
| Security & Fraud Detection Agent | Détecte les opérations anormales et les attaques par Prompt Injection, génère des alertes, demande une validation humaine | Règles codées |

Le LLM ne décide jamais d'autoriser un paiement : cette décision repose sur des règles codées et testables.

## Architecture

```
React  --HTTP-->  Node.js (API)  --HTTP + X-API-Key-->  Agents Python
                       |
                       +--SQL-->  PostgreSQL

n8n : orchestration du workflow de chat (webhook), appelle les agents Python
      et les routes internes de Node.js
```

- **React** : chat, catalogue, dashboard, alertes, validation humaine, journal.
- **Node.js** : API publique et admin, accès exclusif à PostgreSQL, calcul des KPI.
- **n8n** : workflows qui enchaînent les agents (chat, analyse, validation humaine).
- **Agents Python** : une route par agent, entrées et sorties JSON validées.
- **PostgreSQL** : clients, cours, commandes, transactions, alertes, interactions, approbations, recommandations, événements.

Le détail des routes et des formats JSON est dans [`docs/api-contracts.md`](docs/api-contracts.md).

## Structure du dépôt

```
bytessbabesss/
├── frontend/     React
├── backend/      Node.js (routes, accès PostgreSQL)
├── agents/       Python (un fichier par agent)
├── n8n/          workflows exportés en JSON
├── db/           schema.sql, seed.sql
├── docs/         api-contracts.md, architecture.png
├── .env.example
└── README.md
```

## Prérequis

- Node.js
- Python 3
- PostgreSQL
- n8n (Docker conseillé)
- Une clé API d'un fournisseur de LLM

## Installation

1. Cloner le dépôt puis copier `.env.example` vers `.env` et remplir les valeurs (ne jamais committer `.env`).
2. Créer la base et charger `db/schema.sql` puis `db/seed.sql`.
3. Lancer chaque service dans son dossier (commandes à adapter à votre configuration) :
   - `backend/` : installer les dépendances puis démarrer l'API (port 4000)
   - `agents/` : installer les dépendances puis démarrer le service (port 8001)
   - `frontend/` : installer les dépendances puis démarrer l'interface (port 5173)
4. Importer les workflows de `n8n/` dans n8n, créer les credentials (en-tête `X-API-Key`, clé du LLM) et activer les workflows.

## Variables d'environnement

Voir `.env.example`. Les valeurs sont fictives ; les vrais secrets restent dans l'environnement local et dans les credentials n8n.

| Variable | Utilisée par | Rôle |
| --- | --- | --- |
| `DATABASE_URL` | Node.js | Connexion PostgreSQL (utilisateur à droits limités) |
| `INTERNAL_API_KEY` | Node.js, agents, n8n | Clé partagée pour les appels internes |
| `ADMIN_TOKEN` | Node.js, React (admin) | Accès aux routes dashboard, alertes, journal, approbations |
| `AGENTS_BASE_URL` | Node.js, n8n | URL du service d'agents |
| `LLM_API_KEY`, `LLM_MODEL` | Agents | Fournisseur de LLM (jamais exposé côté React) |
| `VITE_API_BASE_URL` | React | URL de l'API Node.js |

## Scénario de démonstration

1. Un client discute avec le Sales Agent (texte, ou voix via le navigateur).
2. Customer Intelligence analyse l'intérêt et les objections.
3. Si le client veut acheter, la commande est créée puis contrôlée par l'agent Sécurité.
4. Selon le risque : paiement simulé accepté, mis en attente de validation humaine, ou bloqué.
5. Le dashboard affiche les KPI, les alertes et les recommandations.
6. Démonstration d'une attaque par Prompt Injection : le message est bloqué et une alerte est créée.

## Sécurité

- Moindre privilège : chaque agent ne reçoit que les données nécessaires et n'accède pas à la base.
- Utilisateur PostgreSQL limité, sans suppression sur les journaux.
- Journal des actions des agents et des paiements, consultable dans l'interface.
- Filtrage des messages (Prompt Injection) avant tout appel aux agents.
- Validation humaine avant toute action financière sensible.
- Échec fermé : si le contrôle de sécurité est indisponible, la transaction n'est jamais autorisée automatiquement.
- Aucun secret dans le code ni dans le dépôt.

## Limites du prototype

- Paiements entièrement simulés, aucune intégration bancaire réelle.
- Les règles antifraude sont simples et fixes (seuils, tentatives répétées, cohérence du montant).
- Les réponses des agents LLM peuvent contenir des erreurs : les sorties sont validées, mais pas garanties exactes.
- Les décisions sensibles nécessitent une supervision humaine.

## Statut

- [ ] Contrat d'API validé par l'équipe
- [ ] Workflow de chat n8n
- [ ] Agents Python
- [ ] API Node.js et base PostgreSQL
- [ ] Interface React et dashboard
- [ ] Démonstration de bout en bout

## Équipe

À compléter (noms et rôles).
