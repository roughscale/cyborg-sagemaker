#!/usr/bin/env bash
#
# Upload configuration files to S3 for SageMaker training jobs
#
# This script uploads algorithm configs, scenarios, and environment configs
# to the S3 artifacts bucket where SageMaker jobs can access them.
#
# Usage:
#   ./upload_configs.sh [--force]
#
# Options:
#   --force    Force re-upload all files, even if they already exist in S3

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TERRAFORM_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
PROJECT_ROOT="$( cd "$TERRAFORM_DIR/.." && pwd )"
CONFIGS_DIR="$PROJECT_ROOT/configs"

# ============================================================================
# Functions
# ============================================================================

print_usage() {
    cat << EOF
Usage: $0 [--force]

Upload configuration files to S3 for SageMaker training jobs.

This script uploads the following to S3:
  - Algorithm configs (configs/algorithms/*.yaml)
  - Environment scenarios (configs/environments/scenarios/*.yaml)
  - Environment configs (configs/environments/*.yaml)

Options:
  --force    Force re-upload all files, even if they already exist in S3

Examples:
  $0                # Upload only new/modified files
  $0 --force        # Force re-upload all files

Environment Variables:
  AWS_REGION      AWS region (default: from terraform.tfvars or us-east-1)
  AWS_PROFILE     AWS profile to use (optional)

EOF
}

log_info() {
    echo -e "${BLUE}INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

check_dependencies() {
    local missing_deps=()

    if ! command -v terraform &> /dev/null; then
        missing_deps+=("terraform")
    fi

    if ! command -v aws &> /dev/null; then
        missing_deps+=("aws-cli")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        echo "Please install the missing dependencies and try again."
        exit 1
    fi
}

get_terraform_output() {
    local output_name=$1
    cd "$TERRAFORM_DIR"
    terraform output -raw "$output_name" 2>/dev/null || echo ""
}

check_configs_exist() {
    if [ ! -d "$CONFIGS_DIR" ]; then
        log_error "Configs directory not found: $CONFIGS_DIR"
        exit 1
    fi

    if [ ! -d "$CONFIGS_DIR/algorithms" ] && [ ! -d "$CONFIGS_DIR/environments" ]; then
        log_error "No config subdirectories found in $CONFIGS_DIR"
        echo "Expected structure:"
        echo "  configs/"
        echo "    algorithms/       # Algorithm configs (drqn.yaml, etc.)"
        echo "    environments/     # Environment configs"
        echo "      scenarios/      # Scenario YAML files"
        exit 1
    fi
}

# ============================================================================
# Main Script
# ============================================================================

# Parse arguments
FORCE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Check dependencies
check_dependencies

# Check configs directory exists
check_configs_exist

# Get S3 bucket from Terraform
log_info "Getting S3 bucket from Terraform..."
BUCKET=$(get_terraform_output "artifacts_bucket")

if [ -z "$BUCKET" ]; then
    log_error "Could not get S3 bucket from Terraform output."
    echo "Please ensure infrastructure is deployed with 'terraform apply'"
    exit 1
fi

log_success "Found S3 bucket: $BUCKET"

# Get AWS region
AWS_REGION=$(get_terraform_output "aws_region")
if [ -z "$AWS_REGION" ]; then
    AWS_REGION=${AWS_DEFAULT_REGION:-us-east-1}
    log_warning "Could not determine region from Terraform, using: $AWS_REGION"
fi

# Check if bucket exists
if ! aws s3 ls "s3://$BUCKET" --region "$AWS_REGION" &> /dev/null; then
    log_error "S3 bucket not accessible: $BUCKET"
    echo "Please check:"
    echo "  1. AWS credentials are configured"
    echo "  2. Infrastructure is deployed"
    echo "  3. You have access to the bucket"
    exit 1
fi

# Build sync options
SYNC_OPTS=()
if [ "$FORCE" = false ]; then
    SYNC_OPTS+=("--size-only")  # Only upload if size differs
fi

# Upload configs
echo ""
log_info "Uploading configuration files to S3..."
echo ""

cd "$CONFIGS_DIR"

# Count files to upload
TOTAL_FILES=$(find . -type f \( -name "*.yaml" -o -name "*.yml" -o -name "*.json" \) | wc -l)
log_info "Found $TOTAL_FILES configuration file(s) to sync"

# Sync to S3
aws s3 sync . "s3://$BUCKET/configs/" \
    --region "$AWS_REGION" \
    --exclude "*.pyc" \
    --exclude "__pycache__/*" \
    --exclude ".DS_Store" \
    --exclude "*.md" \
    "${SYNC_OPTS[@]}" \
    || {
        log_error "Failed to upload configs to S3"
        exit 1
    }

echo ""
log_success "Configs uploaded successfully!"

# List uploaded files by category
echo ""
echo "Uploaded configurations:"
echo ""

# Algorithm configs
if [ -d "algorithms" ]; then
    echo "Algorithm Configs:"
    aws s3 ls "s3://$BUCKET/configs/algorithms/" --region "$AWS_REGION" | grep -E '\.(yaml|yml)$' | awk '{print "  - " $4}' || true
    echo ""
fi

# Scenarios
if [ -d "environments/scenarios" ]; then
    echo "Scenarios:"
    aws s3 ls "s3://$BUCKET/configs/environments/scenarios/" --region "$AWS_REGION" | grep -E '\.(yaml|yml)$' | awk '{print "  - " $4}' || true
    echo ""
fi

# Summary
echo "S3 Locations:"
echo "  Algorithms: s3://$BUCKET/configs/algorithms/"
echo "  Scenarios:  s3://$BUCKET/configs/environments/scenarios/"
echo ""

log_success "Ready to launch training jobs!"
echo ""
echo "Next steps:"
echo "  1. Build and push Docker images (if not done):"
echo "     cd $PROJECT_ROOT/docker && ./build.sh --push"
echo ""
echo "  2. Launch a training job:"
echo "     $TERRAFORM_DIR/scripts/launch_training.sh drqn 500000"
echo ""
