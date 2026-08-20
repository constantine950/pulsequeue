set -euo pipefail

IMAGE="ghcr.io/constantine950/pulsequeue-worker"
TAG="${1:-latest}"

docker build -f infra/Dockerfile.worker -t "${IMAGE}:${TAG}" .
docker push "${IMAGE}:${TAG}"

echo "Pushed ${IMAGE}:${TAG}"