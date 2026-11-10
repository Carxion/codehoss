sh release.sh 1.0.0
sh release.sh 1.1.0
kubectl apply -f k8s/ -f canary.yaml
kubectl rollout status deployment/house-api --timeout=120s
kubectl rollout status deployment/house-api-canary --timeout=120s
