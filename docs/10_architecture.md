# Architecture proposée

## Vue d'ensemble

- **Mode développement** : Docker Compose, deux services (`api`, `front`).
- **Mode recette** : Kubernetes dans le namespace `datapress-recette`.

## Mode développement

- Service `api` (FastAPI) exposé sur `localhost:8080`.
- Service `front` (HTML + NGINX) exposé sur `localhost:8081`.
- Communication front → API via l'URL `http://localhost:8080/` (exemple simple).

## Mode recette (Kubernetes)

- Namespace : `datapress-recette`.
- `Deployment` + `Service` pour l'API (`datapress-api`).
  - 2 replicas.
  - Probes de liveness / readiness sur `/health`.
  - ConfigMap + Secret pour la configuration.
- `Deployment` + `Service` de type `NodePort` pour le front (`datapress-front`).
  - Accès externe via le NodePort 30080.
