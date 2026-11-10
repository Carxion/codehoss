sh release.sh 1.0.0
kubectl apply -f k8s/
kubectl rollout status deployment/house-api --timeout=120s
