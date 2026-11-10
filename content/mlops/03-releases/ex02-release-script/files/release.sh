#!/bin/sh
# Usage: sh release.sh VERSION
# TODO: build the image with the build args MODEL_VERSION=$VERSION and MAX_MAE (from the
# environment, default 25000), tag it docker:5000/house-api:$VERSION and
# docker:5000/house-api:latest, and push both. Stop at the first failure (set -e).
