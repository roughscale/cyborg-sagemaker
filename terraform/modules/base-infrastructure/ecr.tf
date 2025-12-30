# ECR repository for base image
resource "aws_ecr_repository" "cyborg_base" {
  name                 = "${var.project_name}-${var.environment}/base"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-base"
      Type = "base"
    }
  )
}

# ECR repository for training image
resource "aws_ecr_repository" "cyborg_training" {
  name                 = "${var.project_name}-${var.environment}/training"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-training"
      Type = "training"
    }
  )
}

# ECR repository for evaluation image
resource "aws_ecr_repository" "cyborg_evaluation" {
  name                 = "${var.project_name}-${var.environment}/evaluation"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-evaluation"
      Type = "evaluation"
    }
  )
}

# Lifecycle policy for training repository to manage image retention
resource "aws_ecr_lifecycle_policy" "training_lifecycle" {
  repository = aws_ecr_repository.cyborg_training.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# Lifecycle policy for evaluation repository
resource "aws_ecr_lifecycle_policy" "evaluation_lifecycle" {
  repository = aws_ecr_repository.cyborg_evaluation.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# Lifecycle policy for base repository
resource "aws_ecr_lifecycle_policy" "base_lifecycle" {
  repository = aws_ecr_repository.cyborg_base.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus     = "any"
        countType     = "imageCountMoreThan"
        countNumber   = 5
      }
      action = {
        type = "expire"
      }
    }]
  })
}
