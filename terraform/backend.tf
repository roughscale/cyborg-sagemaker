# Terraform Backend Configuration
#
# This file configures where Terraform stores its state.
#
# Option 1: S3 Backend (Recommended for team/production use)
# Uncomment and configure the S3 backend below to store state remotely.
# This enables state locking and sharing across team members.
#
# terraform {
#   backend "s3" {
#     bucket         = "cyborg-rl-terraform-state"
#     key            = "cyborg-sagemaker/terraform.tfstate"
#     region         = "us-east-1"
#     dynamodb_table = "terraform-state-lock"
#     encrypt        = true
#   }
# }

# Option 2: Local Backend (Default for solo development)
# State is stored in terraform.tfstate file locally.
# This is the default - no configuration needed.
#
# To use local backend, simply comment out or remove the S3 backend above.

# Note: If using S3 backend, create the bucket and DynamoDB table first:
#
# aws s3api create-bucket \
#   --bucket cyborg-rl-terraform-state \
#   --region us-east-1
#
# aws dynamodb create-table \
#   --table-name terraform-state-lock \
#   --attribute-definitions AttributeName=LockID,AttributeType=S \
#   --key-schema AttributeName=LockID,KeyType=HASH \
#   --billing-mode PAY_PER_REQUEST \
#   --region us-east-1
