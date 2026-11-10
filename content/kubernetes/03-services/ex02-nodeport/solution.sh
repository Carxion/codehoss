kubectl apply -f deployment.yaml -f public.yaml
kubectl rollout status deployment/web --timeout=90s
