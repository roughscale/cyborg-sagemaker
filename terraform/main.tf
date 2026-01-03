# Main Terraform Configuration for CybORG SageMaker
#
# This file instantiates the base infrastructure module and optionally
# launches a training job if configured via variables.

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.tags
  }
}

# Get current AWS account and region info
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Base Infrastructure Module
# Creates ECR repositories, S3 buckets, IAM roles, and optionally VPC
module "base_infrastructure" {
  source = "./modules/base-infrastructure"

  project_name           = var.project_name
  environment            = var.environment
  enable_aws_emulation   = var.enable_aws_emulation
  vpc_cidr               = var.vpc_cidr
  availability_zones     = var.availability_zones
  git_repository_url     = var.git_repository_url
  git_branch             = var.git_branch
  cyborg_repository_url  = var.cyborg_repository_url
  cyborg_branch          = var.cyborg_branch

  tags = var.tags
}

# Note: Training jobs are NOT managed by Terraform
# SageMaker training jobs are transient workloads, not persistent infrastructure.
# Use the helper scripts to launch training jobs:
#   ./scripts/launch_training.sh <algorithm> <total_steps>
#
# The training job variables in variables.tf are kept for documentation
# and potential future use with null_resource provisioners if needed.
