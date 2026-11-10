kubectl apply -f namespace.yaml
kubectl apply -n shop -f deployment.yaml
kubectl rollout status deployment/web -n shop --timeout=90s
