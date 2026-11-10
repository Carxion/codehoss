kubectl apply -f deployment.yaml
kubectl rollout status deployment/slow --timeout=120s
