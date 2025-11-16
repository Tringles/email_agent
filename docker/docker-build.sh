#!/bin/bash
# Build script for Docker images

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
REGISTRY=""
VERSION="latest"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -d|--date)
            BUILD_DATE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -r, --registry REGISTRY   Docker registry (e.g., docker.io/username)"
            echo "  -v, --version VERSION     Image version tag (default: latest)"
            echo "  -d, --date DATE          Build date (default: current date)"
            echo "  -h, --help               Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Build arguments
BUILD_ARGS="--build-arg BUILD_DATE=${BUILD_DATE} --build-arg VCS_REF=${VCS_REF} --build-arg VERSION=${VERSION}"

# Image names
if [ -z "$REGISTRY" ]; then
    APP_IMAGE="email-agent:${VERSION}"
    WORKER_IMAGE="email-agent-worker:${VERSION}"
    BEAT_IMAGE="email-agent-beat:${VERSION}"
else
    APP_IMAGE="${REGISTRY}/email-agent:${VERSION}"
    WORKER_IMAGE="${REGISTRY}/email-agent-worker:${VERSION}"
    BEAT_IMAGE="${REGISTRY}/email-agent-beat:${VERSION}"
fi

echo -e "${GREEN}Building Docker images...${NC}"
echo -e "Registry: ${YELLOW}${REGISTRY:-local}${NC}"
echo -e "Version: ${YELLOW}${VERSION}${NC}"
echo -e "Build Date: ${YELLOW}${BUILD_DATE}${NC}"
echo -e "VCS Ref: ${YELLOW}${VCS_REF}${NC}"
echo ""

# Build app image
echo -e "${GREEN}Building app image: ${APP_IMAGE}${NC}"
docker build -f docker/Dockerfile.app ${BUILD_ARGS} -t ${APP_IMAGE} .
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ App image built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build app image${NC}"
    exit 1
fi

# Build worker image
echo -e "${GREEN}Building worker image: ${WORKER_IMAGE}${NC}"
docker build -f docker/Dockerfile.worker ${BUILD_ARGS} -t ${WORKER_IMAGE} .
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Worker image built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build worker image${NC}"
    exit 1
fi

# Build beat image
echo -e "${GREEN}Building beat image: ${BEAT_IMAGE}${NC}"
docker build -f docker/Dockerfile.beat ${BUILD_ARGS} -t ${BEAT_IMAGE} .
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Beat image built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build beat image${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}All images built successfully!${NC}"
echo ""
echo "Images:"
echo "  - ${APP_IMAGE}"
echo "  - ${WORKER_IMAGE}"
echo "  - ${BEAT_IMAGE}"

# Push images if registry is specified
if [ -n "$REGISTRY" ]; then
    echo ""
    read -p "Push images to registry? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Pushing images...${NC}"
        docker push ${APP_IMAGE}
        docker push ${WORKER_IMAGE}
        docker push ${BEAT_IMAGE}
        echo -e "${GREEN}All images pushed successfully!${NC}"
    fi
fi

