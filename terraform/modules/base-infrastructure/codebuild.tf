# CodeBuild project for building Docker images
# Builds images in AWS for faster ECR push over internal network

# IAM role for CodeBuild
resource "aws_iam_role" "codebuild_role" {
  name = "${var.project_name}-${var.environment}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "codebuild.amazonaws.com"
      }
    }]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-codebuild-role"
    }
  )
}

# IAM policy for CodeBuild
resource "aws_iam_role_policy" "codebuild_policy" {
  role = aws_iam_role.codebuild_role.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
    ]
  })
}

# CodeBuild project
resource "aws_codebuild_project" "docker_build" {
  name          = "${var.project_name}-${var.environment}-docker-build"
  description   = "Build CybORG Docker images and push to ECR (from Git)"
  build_timeout = 60  # 60 minutes
  service_role  = aws_iam_role.codebuild_role.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  cache {
    type = "LOCAL"
    modes = ["LOCAL_DOCKER_LAYER_CACHE", "LOCAL_SOURCE_CACHE"]
  }

  environment {
    compute_type                = "BUILD_GENERAL1_LARGE"  # 8 vCPUs, 15GB RAM
    image                       = "aws/codebuild/standard:7.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true  # Required for Docker builds

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = data.aws_region.current.name
    }

    environment_variable {
      name  = "ENVIRONMENT"
      value = var.environment
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = "latest"
    }

    # Optional: Can be overridden when starting build
    environment_variable {
      name  = "SB3_REPO"
      value = "https://github.com/roughscale/stable-baselines3.git"
    }

    environment_variable {
      name  = "SB3_BRANCH"
      value = "master"
    }

    environment_variable {
      name  = "SB3_CONTRIB_REPO"
      value = "https://github.com/roughscale/stable-baselines3-contrib.git"
    }

    environment_variable {
      name  = "SB3_CONTRIB_BRANCH"
      value = "master"
    }

    environment_variable {
      name  = "CYBORG_REPO"
      value = var.cyborg_repository_url
    }

    environment_variable {
      name  = "CYBORG_BRANCH"
      value = var.cyborg_branch
    }
  }

  source {
    type            = "GITHUB"
    location        = var.git_repository_url
    git_clone_depth = 1
    buildspec       = "docker/buildspec.yml"

    git_submodules_config {
      fetch_submodules = false
    }
  }

  source_version = var.git_branch

  logs_config {
    cloudwatch_logs {
      group_name  = "/aws/codebuild/${var.project_name}-${var.environment}"
      stream_name = "docker-build"
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-${var.environment}-docker-build"
    }
  )
}
