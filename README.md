# POC DataPress – Documentation technique

## 1. Contexte et objectifs

### 1.1 Contexte DataPress

DataPress est une PME qui édite des tableaux de bord pour des équipes marketing et e-commerce.  
La plateforme interne actuelle permet notamment :

- d’afficher des indicateurs simples (trafic, campagnes, taux de conversion),
- de centraliser quelques rapports PDF et CSV,
- de fournir une vue synthèse aux responsables marketing.

Toute la plateforme est aujourd’hui hébergée sur **un seul serveur** dans le datacenter de DataPress, sur lequel tournent :

- le **front web**,
- l’**API**,
- la **base de données**,
- des scripts maison exécutés par `cron`.

Cette organisation a plusieurs limites :

- quand le serveur tombe, **toute la plateforme est indisponible** ;
- la mise à jour du front ou de l’API implique souvent une **coupure de service** ;
- il est difficile de **tester une nouvelle version** sans impacter les utilisateurs ;
- la **documentation** est partielle et dispersée.

Le DSI souhaite profiter d’un renouvellement d’infrastructure pour moderniser l’architecture à moyen terme (conteneurs, orchestration, CI/CD), sans se “tromper de direction” dès le départ. D’où la demande de ce **POC**.

### 1.2 Objectifs du POC

Les objectifs fixés par le DSI pour ce POC sont :

1. **Séparer** clairement le front et l’API au lieu d’un hébergement monolithique.
2. Disposer d’un environnement de **recette** plus fiable, permettant de tester des versions sans impacter la production.
3. Commencer à utiliser les **conteneurs Docker** et un **orchestrateur Kubernetes** comme base d’une future migration.
4. Mettre en place un **début de CI/CD**, au minimum un build automatisé de l’API.
5. Produire :
   - une **architecture claire**,
   - des **fichiers de configuration propres**,
   - une **documentation technique**,
   - et une **présentation synthétique** pour la validation par le DSI.

Le POC ne vise pas à reproduire l’intégralité du produit DataPress, mais un **échantillon représentatif** : un front simple, une API minimale, et un pipeline de déploiement cohérent.

---

## 2. Périmètre fonctionnel et technique du POC

### 2.1 Fonctionnel minimal

- Le **front** affiche :
  - un titre : `DataPress – POC`,
  - une **version** (ex. `v1.0 – Environnement de démonstration`),
  - un bouton permettant de **tester l’API** et d’afficher le JSON de réponse.

- L’**API** expose au minimum :
  - `GET /` → renvoie un JSON de type :
    ```json
    { "service": "api", "ts": "2025-11-24T09:09:57.620150Z" }
    ```
  - `GET /health` → renvoie `{"status": "ok"}` et sert de point de contrôle pour les probes Kubernetes.

Aucune base de données n’est intégrée dans ce POC : les données sont simulées (timestamp) afin de se concentrer sur l’architecture de déploiement.

### 2.2 Périmètre technique

Le POC couvre :

- la **containerisation** du front et de l’API avec Docker,
- le **mode développement local** via Docker Compose,
- le **déploiement sur Kubernetes** dans un namespace de recette (`datapress-recette`),
- l’utilisation de **ConfigMap** et **Secret**,
- un début de **CI** sur GitHub Actions (build de l’image API).

---

## 3. Architecture globale

### 3.1 Vue d’ensemble

L’architecture cible du POC se décompose en deux environnements :

- **Mode développement (local)** : Docker Compose
  - 1 conteneur `datapress-api` (FastAPI),
  - 1 conteneur `datapress-front` (HTML statique servi par NGINX).

- **Mode recette (Kubernetes)** :
  - Namespace dédié : `datapress-recette`,
  - `Deployment` + `Service` pour l’API,
  - `Deployment` + `Service` NodePort (ou Ingress) pour le front,
  - `ConfigMap` et `Secret` injectés dans l’API.

### 3.2 Architecture – mode développement (Docker Compose)

- Fichier : `docker-compose.yml`
- Services :
  - **api**
    - build : `app/api/Dockerfile`
    - port exposé : `8080:8000`
  - **front**
    - build : `app/front/Dockerfile`
    - port exposé : `8081:80`
    - dépend du service `api`

Le front et l’API tournent sur le même réseau Docker et peuvent communiquer entre eux. L’utilisateur teste l’API soit directement (`http://localhost:8080/`), soit via le bouton “Tester l’API” sur le front (`http://localhost:8081/`).

### 3.3 Architecture – mode recette (Kubernetes)

Dans le namespace `datapress-recette` :

- **ConfigMap `datapress-config`**
  - Variables simples (ex : `APP_ENV=recette`, bannière).

- **Secret `datapress-secret`**
  - Valeur sensible factice (`DB_PASSWORD` encodé en base64), immuable dans le repo.

- **Deployment `datapress-api`**
  - 2 replicas,
  - image : `datapress-api:latest` (dans un vrai contexte, image d’un registry),
  - probes HTTP sur `/health`,
  - requests / limits mémoire,
  - variables d’environnement injectées depuis la ConfigMap et le Secret.

- **Service `datapress-api`**
  - type : `ClusterIP`,
  - port : `80` → `targetPort: 8000`.

- **Deployment `datapress-front`**
  - 1 replica,
  - image : `datapress-front:latest`,
  - expose le port 80.

- **Service `datapress-front`**
  - type : `NodePort`,
  - port 80 exposé en NodePort (ex. `30080`).

L’accès utilisateur se fait via le NodePort du front, qui lui-même appelle le Service interne `datapress-api`.

---

## 4. Choix techniques détaillés

### 4.1 API (backend)

- Stack : **Python 3 / FastAPI / Uvicorn**.
- Endpoints minimalistes (`/`, `/health`) pour se concentrer sur le packaging et le déploiement.
- Structuration :
  - `app/api/main.py`
  - `app/api/requirements.txt`

Ce choix permet :

- un serveur HTTP asynchrone moderne,
- une intégration simple dans une image Docker légère,
- une bonne compatibilité avec les probes `/health`.

### 4.2 Dockerfile API (multi-stage, non-root)

Le Dockerfile de l’API est multi-étapes :

1. **Étape builder** (basée sur `python:3.12-slim`) :
   - installation des dépendances dans `/app/site-packages`,
   - copie du code applicatif.

2. **Étape runtime** (basée sur `python:3.12-slim`) :
   - création d’un utilisateur système non-root (`datapress`),
   - copie des dépendances et du code depuis l’étape builder,
   - définition de `PYTHONPATH` et de la commande de démarrage `uvicorn`,
   - exposition du port 8000.

Avantages :

- taille d’image réduite (pas d’outils de build dans le runtime),
- meilleure sécurité (processus applicatif non-root),
- pipeline clair entre build et exécution.

### 4.3 Front

- Contenu : page HTML statique simple (`DataPress – POC`, version, bouton “Tester l’API”).
- Servi par **NGINX** via un Dockerfile très léger :
  - basé sur `nginx:alpine`,
  - copie d’un `index.html` dans `/usr/share/nginx/html/`.

L’appel API est réalisé en JavaScript (`fetch`). En mode dev, l’URL cible est `http://localhost:8080/`.

### 4.4 Sécurité & fiabilité (Kubernetes)

- L’API est packagée dans un conteneur **non-root**.
- Les variables sensibles (mot de passe simulé) sont gérées via un **Secret**.
- La configuration non sensible (bannière, environnement) est dans une **ConfigMap**.
- Des **probes HTTP** `/health` sont configurées :
  - `readinessProbe` : assure que le pod est prêt avant d’être mis dans le Service,
  - `livenessProbe` : redémarre le conteneur en cas de dysfonctionnement.
- Des **resources requests/limits** mémoire sont définies pour l’API afin de prévenir les dérives de consommation.

---

## 5. Guide d’exploitation

### 5.1 Mode développement (Docker / Docker Compose)

#### 5.1.1 Prérequis

- Docker et Docker Compose installés.
- Port 8080 et 8081 libres sur la machine.

#### 5.1.2 Lancement

Depuis la racine du projet :

```bash
docker compose up --build
