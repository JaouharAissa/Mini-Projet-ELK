# Mini-Projet ELK : Monitoring et analyse de logs de sécurité

Plateforme de collecte, d'indexation et de visualisation de logs de sécurité
(Scénario C : Sécurité et Authentification).

**Étudiant :** Jaouhar Aissa
**Encadrant :** M. Mohamed Najeh Issaoui, IT Business School

## Stack
Elasticsearch / Logstash / Kibana 8.x, Flask 3, MongoDB 7, Redis 7, Docker Compose.

## Démarrage rapide
```bash
git clone https://github.com/JaouharAissa/Mini-Projet-ELK.git
cd Mini-Projet-ELK
cp .env.example .env     # puis modifier les mots de passe
docker compose up -d --build
```

Temps de démarrage estimé : à compléter (premier lancement avec téléchargement des images).

## Accès
| Service | URL |
|---|---|
| Application web | http://localhost:8000 |
| Kibana | http://localhost:5601 |
| Elasticsearch | http://localhost:9200 |

## Arrêt
```bash
docker compose down        # arrêter
docker compose down -v     # arrêter et supprimer les volumes
```

## Structure
- `elk/` : configuration Elasticsearch, Logstash, Kibana
- `webapp/` : application Flask
- `scripts/` : génération de données de test
- `tests/` : tests pytest
- `docs/` : documentation et captures

## Avancement
- [x] Sprint 1 : Analyse et conception
- [ ] Sprint 2 : Infrastructure Docker et backend
- [ ] Sprint 3 : Frontend, authentification, Kibana
- [ ] Sprint 4 : Alerting
- [ ] Sprint 5 : Observabilité et tests
- [ ] Sprint 6 : Documentation et livraison
