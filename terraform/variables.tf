# Core Configuration Variables

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "cyborg-rl"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, research, production)"
  type        = string
  default     = "research"
}

# Infrastructure Configuration

variable "enable_aws_emulation" {
  description = "Enable VPC infrastructure for AWS emulation mode"
  type        = bool
  default     = false
}

variable "vpc_cidr" {
  description = "CIDR block for VPC (if AWS emulation enabled)"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones for VPC subnets"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# Docker Image Configuration

variable "docker_image_tag" {
  description = "Tag for Docker images in ECR"
  type        = string
  default     = "latest"
}

variable "git_repository_url" {
  description = "Git repository URL for cyborg-sagemaker (e.g., https://github.com/user/cyborg-sagemaker)"
  type        = string
}

variable "git_branch" {
  description = "Git branch for cyborg-sagemaker repository"
  type        = string
  default     = "main"
}

variable "cyborg_repository_url" {
  description = "Git repository URL for CybORG (e.g., https://github.com/user/cyborg)"
  type        = string
}

variable "cyborg_branch" {
  description = "Git branch for CybORG repository"
  type        = string
  default     = "main"
}

# Common Tags

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {
    Project   = "CybORG-RL"
    ManagedBy = "Terraform"
  }
}
