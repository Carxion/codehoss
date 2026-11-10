docker build -t counter:1 .
docker volume create counts
for i in 1 2 3; do docker run --rm -v counts:/data counter:1; done
