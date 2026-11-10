#!/bin/sh
# Usage: sh release.sh VERSION
set -e
VERSION=${1:?usage: sh release.sh VERSION}
IMAGE=docker:5000/house-api
docker build -q --build-arg MODEL_VERSION="$VERSION" --build-arg MAX_MAE="${MAX_MAE:-25000}" \
  -t "$IMAGE:$VERSION" -t "$IMAGE:latest" .
docker push -q "$IMAGE:$VERSION"
docker push -q "$IMAGE:latest"
echo "released $IMAGE:$VERSION"
