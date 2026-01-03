output "sagemaker_execution_role_arn" {
  description = "ARN of SageMaker execution role"
  value       = aws_iam_role.sagemaker_execution_role.arn
}

output "sagemaker_execution_role_name" {
  description = "Name of SageMaker execution role"
  value       = aws_iam_role.sagemaker_execution_role.name
}

output "artifacts_bucket_name" {
  description = "Name of S3 artifacts bucket"
  value       = aws_s3_bucket.artifacts.id
}

output "artifacts_bucket_arn" {
  description = "ARN of S3 artifacts bucket"
  value       = aws_s3_bucket.artifacts.arn
}

output "ecr_repository_urls" {
  description = "URLs of ECR repositories"
  value = {
    base       = aws_ecr_repository.cyborg_base.repository_url
    training   = aws_ecr_repository.cyborg_training.repository_url
    evaluation = aws_ecr_repository.cyborg_evaluation.repository_url
  }
}

output "ecr_repository_arns" {
  description = "ARNs of ECR repositories"
  value = {
    base       = aws_ecr_repository.cyborg_base.arn
    training   = aws_ecr_repository.cyborg_training.arn
    evaluation = aws_ecr_repository.cyborg_evaluation.arn
  }
}

output "vpc_config" {
  description = "VPC configuration for SageMaker jobs (null if not enabled)"
  value = var.enable_aws_emulation ? {
    vpc_id          = aws_vpc.emulation_vpc[0].id
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.sagemaker_sg[0].id]
  } : null
}

output "vpc_id" {
  description = "VPC ID (null if not enabled)"
  value       = var.enable_aws_emulation ? aws_vpc.emulation_vpc[0].id : null
}

output "private_subnet_ids" {
  description = "Private subnet IDs (empty if not enabled)"
  value       = var.enable_aws_emulation ? aws_subnet.private[*].id : []
}

output "security_group_id" {
  description = "Security group ID for SageMaker jobs (null if not enabled)"
  value       = var.enable_aws_emulation ? aws_security_group.sagemaker_sg[0].id : null
}

output "codebuild_project_name" {
  description = "Name of CodeBuild project for building Docker images"
  value       = aws_codebuild_project.docker_build.name
}

output "codebuild_project_arn" {
  description = "ARN of CodeBuild project"
  value       = aws_codebuild_project.docker_build.arn
}
