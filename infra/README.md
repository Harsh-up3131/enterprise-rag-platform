# Infrastructure notes

## Production compose profile

Use the production-oriented stack with:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

This profile adds:
- a reverse proxy via nginx
- production-oriented service restart policies
- a production environment profile for the API and worker

## TLS and certificates

For real deployments, mount TLS certs into `infra/nginx/certs/` and update the nginx config to serve HTTPS.
