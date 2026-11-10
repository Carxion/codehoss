kubectl apply -f .
kubectl rollout status deployment/greeter --timeout=90s
