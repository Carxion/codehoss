kubectl apply -f config.yaml -f deployment.yaml
kubectl rollout status deployment/worker --timeout=90s
