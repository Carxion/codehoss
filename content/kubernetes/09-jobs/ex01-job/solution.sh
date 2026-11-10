kubectl apply -f job.yaml
kubectl wait --for=condition=Complete job/squares --timeout=120s
