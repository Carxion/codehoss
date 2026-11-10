kubectl apply -f sites.yaml -f ingress.yaml
kubectl rollout status deployment/shop --timeout=90s
kubectl rollout status deployment/blog --timeout=90s
