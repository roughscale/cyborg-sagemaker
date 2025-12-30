#!/bin/bash
# Trigger CodeBuild to build Docker images in AWS
# CodeBuild pulls source directly from Git repository

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
AWS_PROFILE="${AWS_PROFILE:-default}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
SB3_BRANCH="${SB3_BRANCH:-master}"
SB3_CONTRIB_BRANCH="${SB3_CONTRIB_BRANCH:-master}"
CYBORG_BRANCH="${CYBORG_BRANCH:-main}"
GIT_BRANCH=""
FOLLOW_LOGS=false

# Print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Trigger CodeBuild to build Docker images in AWS"
    echo ""
    echo "Options:"
    echo "  -h, --help                Show this help message"
    echo "  -f, --follow              Follow build logs in real-time"
    echo "  --profile <name>          AWS profile to use (default: default)"
    echo "  --tag <tag>               Docker image tag (default: latest)"
    echo "  --git-branch <branch>     Git branch to build from for cyborg-sagemaker (default: configured in Terraform)"
    echo "  --cyborg-branch <branch>  Git branch to build from for CybORG (default: main)"
    echo "  --sb3-branch <branch>     SB3 branch/commit (default: master)"
    echo "  --sb3-contrib <branch>    SB3-contrib branch/commit (default: master)"
    echo ""
    echo "Environment Variables:"
    echo "  AWS_PROFILE               AWS profile to use"
    echo "  IMAGE_TAG                 Docker image tag"
    echo "  CYBORG_BRANCH             CybORG branch/commit"
    echo "  SB3_BRANCH                SB3 branch/commit"
    echo "  SB3_CONTRIB_BRANCH        SB3-contrib branch/commit"
    echo ""
    echo "Examples:"
    echo "  # Build with defaults and follow logs"
    echo "  $0 --follow"
    echo ""
    echo "  # Build with custom tag"
    echo "  $0 --tag v1.0.0"
    echo ""
    echo "  # Build from specific Git branch"
    echo "  $0 --git-branch feature/new-algorithm"
    echo ""
    echo "  # Build with specific CybORG branch"
    echo "  $0 --cyborg-branch develop"
    echo ""
    echo "  # Build with specific SB3 commits"
    echo "  $0 --sb3-branch abc123 --sb3-contrib def456"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -f|--follow)
            FOLLOW_LOGS=true
            shift
            ;;
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --git-branch)
            GIT_BRANCH="$2"
            shift 2
            ;;
        --cyborg-branch)
            CYBORG_BRANCH="$2"
            shift 2
            ;;
        --sb3-branch)
            SB3_BRANCH="$2"
            shift 2
            ;;
        --sb3-contrib)
            SB3_CONTRIB_BRANCH="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Get Terraform outputs
echo -e "${GREEN}Loading infrastructure information...${NC}"
TERRAFORM_DIR="$(dirname "$0")/.."
cd "$TERRAFORM_DIR"

CODEBUILD_PROJECT=$(terraform output -raw codebuild_project_name 2>/dev/null)
AWS_REGION=$(terraform output -raw aws_region 2>/dev/null)

if [ -z "$CODEBUILD_PROJECT" ] || [ -z "$AWS_REGION" ]; then
    echo -e "${RED}Error: Could not get Terraform outputs. Make sure infrastructure is deployed.${NC}"
    exit 1
fi

echo -e "${GREEN}CodeBuild Project: ${CODEBUILD_PROJECT}${NC}"
echo -e "${GREEN}Region: ${AWS_REGION}${NC}"
echo ""

# Build environment variables override array
ENV_OVERRIDES="name=IMAGE_TAG,value=$IMAGE_TAG,type=PLAINTEXT name=CYBORG_BRANCH,value=$CYBORG_BRANCH,type=PLAINTEXT name=SB3_BRANCH,value=$SB3_BRANCH,type=PLAINTEXT name=SB3_CONTRIB_BRANCH,value=$SB3_CONTRIB_BRANCH,type=PLAINTEXT"

# Build command
START_BUILD_CMD="aws codebuild start-build \
    --project-name $CODEBUILD_PROJECT \
    --profile $AWS_PROFILE \
    --region $AWS_REGION \
    --environment-variables-override $ENV_OVERRIDES"

# Add source version if git branch specified
if [ -n "$GIT_BRANCH" ]; then
    echo -e "${GREEN}Building from Git branch: ${GIT_BRANCH}${NC}"
    START_BUILD_CMD="$START_BUILD_CMD --source-version $GIT_BRANCH"
fi

# Start CodeBuild
echo -e "${GREEN}Starting CodeBuild...${NC}"
BUILD_ID=$(eval "$START_BUILD_CMD --query 'build.id' --output text")

echo -e "${GREEN}✓ Build started: ${BUILD_ID}${NC}"
echo ""

# Print configuration
echo -e "${YELLOW}Build Configuration:${NC}"
echo "  Image Tag:        $IMAGE_TAG"
echo "  CybORG Branch:    $CYBORG_BRANCH"
echo "  SB3 Branch:       $SB3_BRANCH"
echo "  SB3 Contrib:      $SB3_CONTRIB_BRANCH"
if [ -n "$GIT_BRANCH" ]; then
    echo "  Sagemaker Branch: $GIT_BRANCH"
fi
echo ""

# Print monitoring URLs
echo -e "${YELLOW}Monitor build:${NC}"
echo "  Console: https://console.aws.amazon.com/codesuite/codebuild/projects/${CODEBUILD_PROJECT}/build/${BUILD_ID}?region=${AWS_REGION}"
echo "  Logs:    https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#logsV2:log-groups/log-group//aws/codebuild/${CODEBUILD_PROJECT%%:*}"
echo ""

# Follow logs if requested
if [ "$FOLLOW_LOGS" = true ]; then
    echo -e "${GREEN}Following build logs (Ctrl+C to stop)...${NC}"
    echo ""

    # Wait for log stream to be created
    sleep 5

    # Tail the logs
    LOG_GROUP="/aws/codebuild/$(echo $CODEBUILD_PROJECT | cut -d: -f1)"
    aws logs tail "$LOG_GROUP" \
        --follow \
        --format short \
        --filter-pattern "$BUILD_ID" \
        --profile "$AWS_PROFILE" \
        --region "$AWS_REGION" 2>/dev/null || true
else
    echo -e "${YELLOW}Tip: Use --follow to stream build logs in real-time${NC}"
    echo ""
    echo "Check build status with:"
    echo "  aws codebuild batch-get-builds --ids $BUILD_ID --profile $AWS_PROFILE --region $AWS_REGION"
fi
