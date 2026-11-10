kubectl apply -f deployment.yaml -f service.yaml
kubectl rollout status deployment/shop --timeout=90s
