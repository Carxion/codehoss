kubectl apply -f pvc.yaml -f deployment.yaml
kubectl rollout status deployment/notes --timeout=120s
