kubectl apply -f deployment.yaml -f service.yaml
kubectl rollout status deployment/web --timeout=90s
