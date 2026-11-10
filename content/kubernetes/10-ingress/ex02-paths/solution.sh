kubectl apply -f app.yaml -f ingress.yaml
kubectl rollout status deployment/web --timeout=90s
kubectl rollout status deployment/api --timeout=90s
