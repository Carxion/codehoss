kubectl apply -f pod.yaml
kubectl wait --for=condition=Ready pod/shared --timeout=90s
