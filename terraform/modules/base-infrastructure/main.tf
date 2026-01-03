terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# All resources are defined in separate files:
# - iam.tf: SageMaker execution role and policies
# - ecr.tf: ECR repositories for Docker images
# - s3.tf: S3 bucket for artifacts
# - vpc.tf: VPC configuration for AWS emulation mode (optional)
# - variables.tf: Input variables
# - outputs.tf: Module outputs
