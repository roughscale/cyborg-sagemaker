# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Get current AWS region
data "aws_region" "current" {}

# Main S3 bucket for all artifacts
resource "aws_s3_bucket" "artifacts" {
  bucket = "${var.project_name}-${var.environment}-artifacts-${data.aws_caller_identity.current.account_id}"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-artifacts"
      Environment = var.environment
    }
  )
}

# Enable versioning for artifacts bucket
resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Block public access to artifacts bucket
resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-side encryption for artifacts bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy to manage old artifacts
resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "delete-old-checkpoints"
    status = "Enabled"

    filter {
      prefix = "checkpoints/"
    }

    expiration {
      days = 30
    }
  }

  rule {
    id     = "delete-old-tensorboard-logs"
    status = "Enabled"

    filter {
      prefix = "tensorboard/"
    }

    expiration {
      days = 90
    }
  }

  rule {
    id     = "transition-old-models"
    status = "Enabled"

    filter {
      prefix = "models/"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Create folder structure via S3 objects with zero bytes
resource "aws_s3_object" "folder_structure" {
  for_each = toset([
    "configs/",
    "configs/algorithms/",
    "configs/environments/",
    "configs/environments/scenarios/",
    "configs/jobs/",
    "models/",
    "models/drqn/",
    "models/dqn/",
    "models/ppo/",
    "models/recurrent_ppo/",
    "checkpoints/",
    "checkpoints/drqn/",
    "checkpoints/dqn/",
    "checkpoints/ppo/",
    "checkpoints/recurrent_ppo/",
    "tensorboard/",
    "tensorboard/drqn/",
    "tensorboard/dqn/",
    "tensorboard/ppo/",
    "tensorboard/recurrent_ppo/",
    "evaluation-results/",
    "evaluation-results/drqn/",
    "evaluation-results/dqn/",
    "evaluation-results/ppo/",
    "evaluation-results/recurrent_ppo/",
    "jobs/"
  ])

  bucket  = aws_s3_bucket.artifacts.id
  key     = each.value
  content = ""

  tags = var.tags
}
