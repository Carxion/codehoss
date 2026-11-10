kubectl apply -f deployment.yaml
kubectl rollout status deployment/limited --timeout=90s
