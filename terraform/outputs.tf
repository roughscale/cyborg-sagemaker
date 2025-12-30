# Terraform Outputs
#
# These outputs provide important information about the deployed infrastructure
# and training jobs. Access them with:
#   terraform output
#   terraform output -raw <output_name>

# ============================================================================
# Infrastructure Outputs
# ============================================================================

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = data.aws_region.current.name
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "artifacts_bucket" {
  description = "S3 bucket for training artifacts, models, and checkpoints"
  value       = module.base_infrastructure.artifacts_bucket_name
}

output "artifacts_bucket_arn" {
  description = "ARN of the S3 artifacts bucket"
  value       = module.base_infrastructure.artifacts_bucket_arn
}

# ============================================================================
# ECR Repository Outputs
# ============================================================================

output "ecr_base_repository" {
  description = "ECR repository URL for base Docker image"
  value       = module.base_infrastructure.ecr_repository_urls["base"]
}

output "ecr_training_repository" {
  description = "ECR repository URL for training Docker image"
  value       = module.base_infrastructure.ecr_repository_urls["training"]
}

output "ecr_evaluation_repository" {
  description = "ECR repository URL for evaluation Docker image"
  value       = module.base_infrastructure.ecr_repository_urls["evaluation"]
}

# ============================================================================
# IAM Outputs
# ============================================================================

output "sagemaker_execution_role_arn" {
  description = "ARN of the SageMaker execution role"
  value       = module.base_infrastructure.sagemaker_execution_role_arn
}

output "sagemaker_execution_role_name" {
  description = "Name of the SageMaker execution role"
  value       = module.base_infrastructure.sagemaker_execution_role_name
}

# ============================================================================
# VPC Outputs (only if AWS emulation enabled)
# ============================================================================

output "vpc_id" {
  description = "VPC ID for AWS emulation mode (null if disabled)"
  value       = var.enable_aws_emulation ? module.base_infrastructure.vpc_id : null
}

output "private_subnet_ids" {
  description = "Private subnet IDs for AWS emulation mode (empty if disabled)"
  value       = var.enable_aws_emulation ? module.base_infrastructure.private_subnet_ids : []
}

output "security_group_id" {
  description = "Security group ID for SageMaker jobs (null if AWS emulation disabled)"
  value       = var.enable_aws_emulation ? module.base_infrastructure.security_group_id : null
}

# ============================================================================
# CodeBuild Outputs
# ============================================================================

output "codebuild_project_name" {
  description = "CodeBuild project for building Docker images"
  value       = module.base_infrastructure.codebuild_project_name
}

output "codebuild_console_url" {
  description = "AWS Console URL for CodeBuild project"
  value       = "https://console.aws.amazon.com/codesuite/codebuild/projects/${module.base_infrastructure.codebuild_project_name}?region=${data.aws_region.current.name}"
}

# ============================================================================
# Training Job Information
# ============================================================================
# Note: Training jobs are launched via scripts, not Terraform.
# Use the following S3 paths to locate your training outputs:

output "models_s3_path" {
  description = "S3 path where trained models are saved"
  value       = "s3://${module.base_infrastructure.artifacts_bucket_name}/models/"
}

output "checkpoints_s3_path" {
  description = "S3 path where training checkpoints are saved"
  value       = "s3://${module.base_infrastructure.artifacts_bucket_name}/checkpoints/"
}

output "tensorboard_s3_path" {
  description = "S3 path where TensorBoard logs are saved"
  value       = "s3://${module.base_infrastructure.artifacts_bucket_name}/tensorboard/"
}

output "configs_s3_path" {
  description = "S3 path where configs are uploaded"
  value       = "s3://${module.base_infrastructure.artifacts_bucket_name}/configs/"
}

# ============================================================================
# Monitoring URLs
# ============================================================================

output "sagemaker_console_url" {
  description = "AWS Console URL for SageMaker training jobs"
  value       = "https://console.aws.amazon.com/sagemaker/home?region=${data.aws_region.current.name}#/jobs"
}

output "cloudwatch_console_url" {
  description = "AWS Console URL for CloudWatch logs"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#logsV2:log-groups"
}

# ============================================================================
# Quick Start Commands
# ============================================================================

output "docker_login_command" {
  description = "Command to authenticate Docker with ECR"
  value       = "aws ecr get-login-password --region ${data.aws_region.current.name} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com"
}

output "s3_sync_configs_command" {
  description = "Command to sync configs to S3"
  value       = "aws s3 sync ../configs s3://${module.base_infrastructure.artifacts_bucket_name}/configs/ --exclude '*.pyc' --exclude '__pycache__/*'"
}

output "next_steps" {
  description = "Next steps after infrastructure deployment"
  value       = <<-EOT
    Infrastructure deployed successfully!

    Next steps:
    1. Build and push Docker images (recommended - builds in AWS for faster ECR push):
       ./scripts/build_images.sh --follow

       Or build locally (slower upload to ECR):
       cd ../docker && ./build.sh --push

    2. Upload configs to S3:
       ./scripts/upload_configs.sh

    3. Launch a training job:
       python scripts/launch_training.py --algorithm drqn --total-steps 500000
       # Or use the bash wrapper:
       ./scripts/launch_training.sh drqn 500000

    4. Monitor training:
       - Jobs: https://console.aws.amazon.com/sagemaker/home?region=${data.aws_region.current.name}#/jobs
       - Logs: https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#logsV2:log-groups

    5. Download trained models:
       aws s3 sync s3://${module.base_infrastructure.artifacts_bucket_name}/models/ ./models/
  EOT
}
