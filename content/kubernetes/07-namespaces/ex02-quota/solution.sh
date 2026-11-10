kubectl apply -f quota.yaml
kubectl apply -f limits.yaml
kubectl apply -f deployment.yaml
for i in $(seq 60); do [ "$(kubectl get pods -n sandbox --field-selector=status.phase=Running -o name | wc -l)" = 3 ] && break; sleep 2; done
