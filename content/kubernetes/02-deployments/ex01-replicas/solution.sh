kubectl apply -f deployment.yaml
kubectl rollout status deployment/web --timeout=90s
