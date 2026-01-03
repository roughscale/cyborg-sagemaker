#!/bin/bash
# Build script for CybORG SageMaker Docker images with configurable SB3 versions

set -e

# Default values
SB3_REPO="${SB3_REPO:-https://github.com/roughscale/stable-baselines3.git}"
SB3_BRANCH="${SB3_BRANCH:-master}"
SB3_CONTRIB_REPO="${SB3_CONTRIB_REPO:-https://github.com/roughscale/stable-baselines3-contrib.git}"
SB3_CONTRIB_BRANCH="${SB3_CONTRIB_BRANCH:-master}"
AWS_PROFILE="${AWS_PROFILE:-default}"
AWS_REGION="${AWS_REGION:-ap-southeast-2}"
ENVIRONMENT="${ENVIRONMENT:-research}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Auto-detect AWS account ID from profile if not set
if [ -z "$AWS_ACCOUNT_ID" ]; then
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --profile ${AWS_PROFILE} --query Account --output text 2>/dev/null || echo "")
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build CybORG SageMaker Docker images"
    echo ""
    echo "Options:"
    echo "  -h, --help                    Show this help message"
    echo "  --base-only                   Build only base image"
    echo "  --training-only               Build only training image"
    echo "  --evaluation-only             Build only evaluation image"
    echo "  --build-only                  Build images but don't push to ECR"
    echo "  --push-only                   Push existing images to ECR without building"
    echo "  --profile <name>              AWS profile to use (default: default)"
    echo ""
    echo "Environment Variables:"
    echo "  SB3_REPO                      Stable-baselines3 repository URL"
    echo "                                (default: https://github.com/roughscale/stable-baselines3.git)"
    echo "  SB3_BRANCH                    Stable-baselines3 branch/tag/commit"
    echo "                                (default: master)"
    echo "  SB3_CONTRIB_REPO              Stable-baselines3-contrib repository URL"
    echo "                                (default: https://github.com/roughscale/stable-baselines3-contrib.git)"
    echo "  SB3_CONTRIB_BRANCH            Stable-baselines3-contrib branch/tag/commit"
    echo "                                (default: master)"
    echo "  AWS_ACCOUNT_ID                AWS account ID (auto-detected from profile if not set)"
    echo "  AWS_REGION                    AWS region (default: ap-southeast-2)"
    echo "  AWS_PROFILE                   AWS profile to use (default: default)"
    echo "  ENVIRONMENT                   Environment name (default: dev)"
    echo "  IMAGE_TAG                     Docker image tag (default: latest)"
    echo ""
    echo "Note: By default, images are built AND pushed to ECR."
    echo "      AWS account ID is automatically detected from your AWS profile."
    echo "      Use --build-only to skip pushing, or --push-only to skip building."
    echo ""
    echo "Examples:"
    echo "  # Build and push all images (AWS account ID auto-detected)"
    echo "  $0"
    echo ""
    echo "  # Build only, don't push to ECR"
    echo "  $0 --build-only"
    echo ""
    echo "  # Push only (assumes images already built)"
    echo "  $0 --push-only"
    echo ""
    echo "  # Build with specific AWS profile"
    echo "  $0 --profile myprofile"
    echo ""
    echo "  # Build with specific commit hashes"
    echo "  SB3_BRANCH=abc123 SB3_CONTRIB_BRANCH=def456 $0"
    echo ""
    echo "  # Explicitly set AWS account ID (overrides auto-detection)"
    echo "  AWS_ACCOUNT_ID=123456789012 $0"
    echo ""
    echo "  # Build only base image without pushing"
    echo "  $0 --base-only --build-only"
    exit 1
}

# Parse arguments
BUILD_BASE=true
BUILD_TRAINING=true
BUILD_EVALUATION=true
PUSH_TO_ECR=true  # Default: build AND push
BUILD_IMAGES=true

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        --base-only)
            BUILD_TRAINING=false
            BUILD_EVALUATION=false
            shift
            ;;
        --training-only)
            BUILD_BASE=false
            BUILD_EVALUATION=false
            shift
            ;;
        --evaluation-only)
            BUILD_BASE=false
            BUILD_TRAINING=false
            shift
            ;;
        --build-only)
            PUSH_TO_ECR=false
            shift
            ;;
        --push-only)
            BUILD_IMAGES=false
            PUSH_TO_ECR=true
            shift
            ;;
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Check if we're in the correct directory
if [ ! -f "docker/base/Dockerfile" ]; then
    echo -e "${RED}Error: Must run from project root (cyborg-sagemaker/)${NC}"
    exit 1
fi

# Check if we need to be in parent directory for docker context
PARENT_DIR=$(dirname $(pwd))
if [ ! -d "../cyborg" ]; then
    echo -e "${YELLOW}Warning: ../cyborg directory not found. Docker build may fail if CybORG source is needed.${NC}"
fi

# Print build configuration
echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}CybORG SageMaker Docker Build${NC}"
echo -e "${GREEN}==================================================================${NC}"
echo "SB3 Repository:        ${SB3_REPO}"
echo "SB3 Branch/Commit:     ${SB3_BRANCH}"
echo "SB3-Contrib Repo:      ${SB3_CONTRIB_REPO}"
echo "SB3-Contrib Branch:    ${SB3_CONTRIB_BRANCH}"
echo "AWS Profile:           ${AWS_PROFILE}"
if [ "$PUSH_TO_ECR" = true ]; then
    if [ -n "$AWS_ACCOUNT_ID" ]; then
        echo "AWS Account ID:        ${AWS_ACCOUNT_ID} (auto-detected)"
    else
        echo "AWS Account ID:        ${YELLOW}Not detected${NC}"
    fi
    echo "AWS Region:            ${AWS_REGION}"
fi
echo "Environment:           ${ENVIRONMENT}"
echo "Image Tag:             ${IMAGE_TAG}"
echo -e "${GREEN}==================================================================${NC}"
echo ""

# Note: Using official PyTorch image from Docker Hub (no authentication needed)
if [ "$BUILD_IMAGES" = true ]; then
    echo -e "${GREEN}Using official PyTorch image from Docker Hub (pytorch/pytorch:2.0.1-cuda11.7)${NC}"
    echo ""
fi

# Build base image
if [ "$BUILD_IMAGES" = true ] && [ "$BUILD_BASE" = true ]; then
    echo -e "${GREEN}Building base image...${NC}"
    docker build \
        --build-arg SB3_REPO="${SB3_REPO}" \
        --build-arg SB3_BRANCH="${SB3_BRANCH}" \
        --build-arg SB3_CONTRIB_REPO="${SB3_CONTRIB_REPO}" \
        --build-arg SB3_CONTRIB_BRANCH="${SB3_CONTRIB_BRANCH}" \
        -t cyborg-rl-base:${IMAGE_TAG} \
        -f docker/base/Dockerfile \
        ..

    echo -e "${GREEN}✓ Base image built successfully${NC}"
    echo ""

    # Show installed versions
    echo -e "${YELLOW}Checking installed SB3 versions...${NC}"
    docker run --rm cyborg-rl-base:${IMAGE_TAG} python -c "
import stable_baselines3 as sb3
import sb3_contrib
print(f'stable-baselines3: {sb3.__version__}')
print(f'sb3-contrib: {sb3_contrib.__version__}')
" || echo -e "${YELLOW}Could not verify versions (this is normal)${NC}"
    echo ""
fi

# Build training image
if [ "$BUILD_IMAGES" = true ] && [ "$BUILD_TRAINING" = true ]; then
    echo -e "${GREEN}Building training image...${NC}"
    docker build \
        -t cyborg-rl-training:${IMAGE_TAG} \
        -f docker/training/Dockerfile \
        ..

    echo -e "${GREEN}✓ Training image built successfully${NC}"
    echo ""
fi

# Build evaluation image
if [ "$BUILD_IMAGES" = true ] && [ "$BUILD_EVALUATION" = true ]; then
    echo -e "${GREEN}Building evaluation image...${NC}"
    docker build \
        -t cyborg-rl-evaluation:${IMAGE_TAG} \
        -f docker/evaluation/Dockerfile \
        ..

    echo -e "${GREEN}✓ Evaluation image built successfully${NC}"
    echo ""
fi

# Push to ECR if requested
if [ "$PUSH_TO_ECR" = true ]; then
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        echo -e "${RED}Error: AWS_ACCOUNT_ID must be set for --push${NC}"
        exit 1
    fi

    echo -e "${GREEN}Logging in to your ECR repository (${AWS_REGION})...${NC}"
    aws ecr get-login-password --region ${AWS_REGION} --profile ${AWS_PROFILE} | \
        docker login --username AWS --password-stdin \
        ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

    ECR_BASE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/cyborg-rl-${ENVIRONMENT}"

    if [ "$BUILD_BASE" = true ]; then
        echo -e "${GREEN}Pushing base image...${NC}"
        docker tag cyborg-rl-base:${IMAGE_TAG} ${ECR_BASE}/base:${IMAGE_TAG}
        docker push ${ECR_BASE}/base:${IMAGE_TAG}
        echo -e "${GREEN}✓ Base image pushed${NC}"
    fi

    if [ "$BUILD_TRAINING" = true ]; then
        echo -e "${GREEN}Pushing training image...${NC}"
        docker tag cyborg-rl-training:${IMAGE_TAG} ${ECR_BASE}/training:${IMAGE_TAG}
        docker push ${ECR_BASE}/training:${IMAGE_TAG}
        echo -e "${GREEN}✓ Training image pushed${NC}"
    fi

    if [ "$BUILD_EVALUATION" = true ]; then
        echo -e "${GREEN}Pushing evaluation image...${NC}"
        docker tag cyborg-rl-evaluation:${IMAGE_TAG} ${ECR_BASE}/evaluation:${IMAGE_TAG}
        docker push ${ECR_BASE}/evaluation:${IMAGE_TAG}
        echo -e "${GREEN}✓ Evaluation image pushed${NC}"
    fi
fi

echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}Build complete!${NC}"
echo -e "${GREEN}==================================================================${NC}"

# Show summary
echo ""
if [ "$BUILD_IMAGES" = true ]; then
    echo "Built images:"
    if [ "$BUILD_BASE" = true ]; then
        echo "  - cyborg-rl-base:${IMAGE_TAG}"
    fi
    if [ "$BUILD_TRAINING" = true ]; then
        echo "  - cyborg-rl-training:${IMAGE_TAG}"
    fi
    if [ "$BUILD_EVALUATION" = true ]; then
        echo "  - cyborg-rl-evaluation:${IMAGE_TAG}"
    fi
fi

if [ "$PUSH_TO_ECR" = true ]; then
    echo ""
    echo "Pushed to ECR:"
    if [ "$BUILD_BASE" = true ]; then
        echo "  - ${ECR_BASE}/base:${IMAGE_TAG}"
    fi
    if [ "$BUILD_TRAINING" = true ]; then
        echo "  - ${ECR_BASE}/training:${IMAGE_TAG}"
    fi
    if [ "$BUILD_EVALUATION" = true ]; then
        echo "  - ${ECR_BASE}/evaluation:${IMAGE_TAG}"
    fi
fi

echo ""
if [ "$BUILD_IMAGES" = true ]; then
    echo "To inspect image labels:"
    echo "  docker inspect cyborg-rl-base:${IMAGE_TAG} | grep -A 10 Labels"
fi
