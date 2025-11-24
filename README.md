Oui, maintenant on va *concrétiser* les livrables demandés dans les documents de sujet :

* **1 doc technique** clair
* **1 présentation “client”** (contenu de slides)

Je te donne tout prêt à copier-coller dans ton dépôt (`docs/`) et dans ton PowerPoint.

---

## 1. Documentation technique (Markdown complet)

👉 Tu peux mettre ça dans un fichier `docs/datapress_doc_technique.md` ou fusionner avec ceux que je t’avais créés.

````markdown
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
````

* API : `http://localhost:8080/` et `http://localhost:8080/health`
* Front : `http://localhost:8081/`

#### 5.1.3 Arrêt

Dans le terminal où tourne Compose :

* `Ctrl+C`, puis éventuellement :

```bash
docker compose down
```

### 5.2 Déploiement Kubernetes (recette)

> Exemple de procédure sur un cluster local type Docker Desktop / Minikube.

#### 5.2.1 Création des objets de base

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
```

#### 5.2.2 Déploiement de l’API

```bash
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml
```

Vérification :

```bash
kubectl get deploy,pods,svc -n datapress-recette
kubectl logs -n datapress-recette <nom_pod_api>
```

#### 5.2.3 Déploiement du front

```bash
kubectl apply -f k8s/front-deployment.yaml
kubectl apply -f k8s/front-service-nodeport.yaml
```

Vérification :

```bash
kubectl get deploy,pods,svc -n datapress-recette
```

Accès front (NodePort) :

* `http://<IP_node>:30080`

Le front doit afficher la page DataPress POC et le bouton “Tester l’API” doit renvoyer le JSON de l’API.

### 5.3 Commandes de diagnostic utiles

* **Lister les ressources** :

  ```bash
  kubectl get all -n datapress-recette
  ```
* **Voir les événements récents** :

  ```bash
  kubectl get events -n datapress-recette --sort-by=.lastTimestamp
  ```
* **Inspecter un pod** :

  ```bash
  kubectl describe pod <nom_pod> -n datapress-recette
  ```
* **Voir les logs** :

  ```bash
  kubectl logs <nom_pod> -n datapress-recette
  ```

---

## 6. CI/CD minimal (GitHub Actions)

Un workflow GitHub Actions `Build API image` est défini dans `.github/workflows/build-api.yml`.

### 6.1 Déclencheurs

* Sur `push` vers la branche `main` (et éventuellement `master`),
* Sur création de Pull Request.

### 6.2 Étapes principales

1. **Checkout du dépôt** (`actions/checkout`).
2. **Setup Docker Buildx** (préparation d’un environnement de build).
3. **Build de l’image API** :

   * exécution de `docker build` dans `app/api/` pour vérifier que l’image `datapress-api` se construit correctement.

### 6.3 Intérêt pour DataPress

* Détection rapide des erreurs de build lors d’un commit,
* Base pour une future chaîne CI/CD plus complète :

  * push d’images vers un registry,
  * déploiement automatique sur un cluster,
  * tests automatisés.

---

## 7. Limites du POC et pistes d’amélioration

### 7.1 Limites actuelles

* Pas de base de données réelle intégrée (simulation simple).
* Pas de TLS ni de gestion de certificats pour l’accès au front.
* Pas d’Ingress Controller configuré.
* Pas d’autoscaling (HPA) ni de stratégies de **rolling update** avancées.
* Pas de monitoring centralisé (Prometheus, Grafana, logs centralisés).
* Pas de NetworkPolicies pour restreindre les flux inter-pods.

### 7.2 Pistes d’évolution

Pour une future version de l’architecture cible, il serait pertinent de :

1. **Intégrer une base de données** (managée ou StatefulSet Kubernetes).
2. **Introduire un Ingress** avec TLS (certificats managés ou Let’s Encrypt).
3. **Mettre en place le monitoring** (Prometheus, Grafana, Loki ou équivalent).
4. **Gérer la sécurité réseau** avec des NetworkPolicies.
5. **Automatiser davantage la CI/CD** :

   * build & push d’images dans un registry privé,
   * déploiement sur un cluster de recette,
   * tests d’acceptation automatisés.
6. **Industrialiser la gestion des secrets** (Vault ou Secret Manager plutôt que des Secrets K8s bruts).

Ce POC fournit donc une **base simple mais cohérente** sur laquelle les équipes DataPress peuvent s’appuyer pour aller vers une architecture conteneurisée plus robuste.

```

---

## 2. Présentation “client” (contenu de slides)

👉 Tu peux créer un PPT “POC DataPress – Conteneurs & Kubernetes” et copier ce contenu slide par slide.

### Slide 1 – Titre

**Titre :**  
> POC DataPress – Conteneurs & Kubernetes  

**Sous-titre :**  
> Séparation front / API, environnement de recette et CI minimale  

**Bas de page :**  
> Équipe consulting – Date

---

### Slide 2 – Contexte DataPress

**Titre :** Contexte et problématique

**Points :**

- PME éditrice de tableaux de bord pour équipes marketing.
- Plateforme interne actuelle **monolithique** sur un seul serveur.
- Sur la même machine : front, API, base de données, scripts `cron`.
- Incidents récents → indisponibilité globale, MEP risquées, peu de recette.
- Besoin de préparer une **modernisation** (conteneurs, orchestration, CI/CD).

---

### Slide 3 – Objectifs du POC

**Titre :** Objectifs

**Points :**

- Séparer clairement **front** et **API**.
- Disposer d’un environnement de **recette** plus fiable.
- Démarrer l’usage de **Docker** et de **Kubernetes**.
- Mettre en place un **début de CI/CD** (build automatisé).
- Fournir :
  - une architecture cible simple,
  - des fichiers de configuration propres,
  - une documentation technique + une présentation de synthèse.

---

### Slide 4 – Périmètre fonctionnel

**Titre :** Périmètre fonctionnel POC

**Points :**

- Front :
  - Page `DataPress – POC`,
  - Affichage d’une **version** (ex. `v1.0 POC`),
  - Bouton pour **tester l’API** et afficher sa réponse.
- API :
  - `GET /` → JSON `{ "service": "api", "ts": … }`,
  - `GET /health` → utilisé par les probes Kubernetes.
- Pas de base de données réelle : données simulées (timestamp), focus sur le déploiement.

---

### Slide 5 – Architecture globale

**Titre :** Vue d’ensemble de l’architecture

**Contenu :**

- Schéma (à dessiner) avec :
  - Mode dev : poste développeur → Docker Compose → `front` + `api`.
  - Mode recette : utilisateurs → NodePort front → Service front → Service API → pods API.
- Séparation nette front / API.
- Namespace dédié `datapress-recette` pour la recette.

---

### Slide 6 – Mode développement (Docker)

**Titre :** Mode développement – Docker Compose

**Points :**

- Fichier `docker-compose.yml` :
  - Service `api` (FastAPI, port 8080),
  - Service `front` (NGINX statique, port 8081).
- Lancement simple :
  - `docker compose up --build`
- Tests :
  - `http://localhost:8080/` et `/health` pour l’API,
  - `http://localhost:8081/` pour le front.
- Objectif : itération rapide, environnement isolé.

---

### Slide 7 – Mode recette (Kubernetes)

**Titre :** Mode recette – Kubernetes

**Points :**

- Namespace : `datapress-recette`.
- API :
  - `Deployment` 2 replicas,
  - `Service` **ClusterIP** sur port 80,
  - probes `/health` + requests/limits mémoire.
- Front :
  - `Deployment` 1 replica,
  - `Service` **NodePort** (ex. 30080) pour accès externe.
- Utilisation de :
  - `ConfigMap` pour la configuration non sensible,
  - `Secret` pour une valeur sensible (mot de passe simulé).

---

### Slide 8 – Sécurité & fiabilité

**Titre :** Sécurité et fiabilité

**Points :**

- API packagée dans un conteneur **non-root**.
- Séparation front / API → meilleure isolation.
- Probes Kubernetes `/health` :
  - `readiness` → ne reçoit du trafic que lorsqu’elle est prête,
  - `liveness` → redémarrage automatique en cas de blocage.
- **Resources** définies (requests/limits) pour maîtriser la consommation.
- ConfigMap / Secret :
  - Configuration claire,
  - Différenciation config vs secrets.

---

### Slide 9 – CI/CD minimal

**Titre :** CI/CD – Build automatisé

**Points :**

- Workflow GitHub Actions : `Build API image`.
- Déclenchement :
  - `push` sur la branche `main`,
  - Pull Requests.
- Étapes :
  - Checkout du code,
  - Setup Docker Buildx,
  - Build de l’image API.
- Bénéfices :
  - Vérification automatique que l’API se build,
  - Base pour un pipeline de déploiement complet.

---

### Slide 10 – Limites et suite

**Titre :** Limites du POC & recommandations

**Points :**

- Limites :
  - Pas de base de données réelle,
  - Pas d’Ingress ni de TLS,
  - Pas d’autoscaling ni de supervision avancée,
  - Pas de NetworkPolicies.
- Recommandations :
  - Intégrer une base de données gérée,
  - Ajouter un Ingress + TLS,
  - Mettre en place monitoring et logs centralisés,
  - Étendre la CI/CD (registry, déploiement automatique),
  - Travailler la sécurité réseau (NetworkPolicies).

---

Si tu veux, je peux aussi te générer un **fichier .pptx** directement (avec ces slides déjà créées) que tu pourras télécharger et ajuster, ou bien adapter la doc technique en PDF.
```
