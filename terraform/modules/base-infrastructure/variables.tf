variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "cyborg-rl"
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
}

variable "enable_aws_emulation" {
  description = "Enable VPC for AWS emulation mode"
  type        = bool
  default     = false
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones for subnets"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

variable "git_repository_url" {
  description = "Git repository URL for cyborg-sagemaker CodeBuild source (e.g., https://github.com/user/cyborg-sagemaker)"
  type        = string
}

variable "git_branch" {
  description = "Git branch to use for cyborg-sagemaker repository"
  type        = string
  default     = "main"
}

variable "cyborg_repository_url" {
  description = "Git repository URL for CybORG (e.g., https://github.com/user/cyborg)"
  type        = string
}

variable "cyborg_branch" {
  description = "Git branch to use for CybORG repository"
  type        = string
  default     = "main"
}
