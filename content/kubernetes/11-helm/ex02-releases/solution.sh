helm install blog ./chart --wait --timeout 120s
helm upgrade blog ./chart --set greeting=Hi --wait --timeout 120s
helm upgrade blog ./chart --set greeting=Hi --set replicas=3 --wait --timeout 120s
helm rollback blog 2 --wait --timeout 120s
