set -euo pipefail

IMAGE="ghcr.io/constantine950/pulsequeue-api"
TAG="${1:-latest}"

docker build -f infra/Dockerfile.api -t "${IMAGE}:${TAG}" .
docker push "${IMAGE}:${TAG}"

echo "Pushed ${IMAGE}:${TAG}"