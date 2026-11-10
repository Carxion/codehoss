kubectl create secret generic db-credentials --from-literal=password=s3cret
kubectl apply -f .
kubectl rollout status deployment/app --timeout=90s
