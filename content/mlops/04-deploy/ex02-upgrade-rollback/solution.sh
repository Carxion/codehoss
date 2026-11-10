sh release.sh 1.0.0
kubectl apply -f k8s/
kubectl rollout status deployment/house-api --timeout=120s
sh release.sh 1.1.0
kubectl set image deployment/house-api api=docker:5000/house-api:1.1.0
kubectl rollout status deployment/house-api --timeout=120s
kubectl rollout undo deployment/house-api
kubectl rollout status deployment/house-api --timeout=120s
