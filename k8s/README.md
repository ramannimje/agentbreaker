Kubernetes deployment notes for AgentBreaker

1. Build and push container image to your registry (example uses GitHub Container Registry):

```bash
docker build -t ghcr.io/<owner>/agentbreaker:latest -f api/Dockerfile .
docker push ghcr.io/<owner>/agentbreaker:latest
```

2. Create secrets (example uses base64 value in `secret-example.yaml` or create via `kubectl create secret generic`).

3. Apply manifests:

```bash
kubectl apply -f k8s/secret-example.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

Adjust resource requests/limits, replicas, and image tags for production.
