# Limites du POC et pistes d'amélioration

## Limites

- Pas de TLS / certificat géré dans ce POC.
- Pas de supervision avancée (metrics Prometheus, logs centralisés, etc.).
- Pas d'autoscaling (HPA) ni de NetworkPolicies.
- Pas de gestion de base de données réelle.

## Pistes d'amélioration

- Intégrer une base de données managée ou un StatefulSet.
- Ajouter un Ingress Controller avec certificat TLS.
- Ajouter de la supervision (Prometheus, Grafana, Loki, etc.).
- Mettre en place un pipeline CI/CD complet (build + push image + déploiement).
