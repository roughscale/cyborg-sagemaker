# CybORG SageMaker Terraform Infrastructure

This directory contains Terraform infrastructure-as-code for deploying CybORG RL training and evaluation workloads to AWS SageMaker.

## Quick Start

### 1. Prerequisites

- Terraform >= 1.5
- AWS CLI configured with appropriate credentials
- Docker (for building images)

### 2. Configure Variables

Copy the example configuration and customize it:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` to set:
- `git_repository_url` - Your cyborg-sagemaker Git repository URL (required)
- `cyborg_repository_url` - Your CybORG Git repository URL (required)
- `git_branch` - Branch for cyborg-sagemaker (default: "main")
- `cyborg_branch` - Branch for CybORG (default: "main")
- `project_name` - Your project name (default: "cyborg-rl")
- `aws_region` - AWS region (default: "ap-southeast-2")
- `environment` - Environment name (default: "research")
- Other settings as needed

### 3. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Deploy infrastructure
terraform apply
```

This creates:
- 3 ECR repositories (base, training, evaluation)
- CodeBuild project for building Docker images from Git
- S3 bucket for artifacts, models, and checkpoints
- IAM role for SageMaker with necessary permissions
- (Optional) VPC infrastructure for AWS emulation mode

### 4. Build and Push Docker Images

**Option A: Build in AWS with CodeBuild (Recommended)**

```bash
# Trigger CodeBuild to clone Git repos, build images, and push to ECR
./scripts/build_images.sh --follow

# Build from specific branches
./scripts/build_images.sh \
  --git-branch feature/new-algo \
  --cyborg-branch develop \
  --sb3-branch abc123

# Build with custom tag
./scripts/build_images.sh --tag v1.0.0 --follow
```

This clones from Git, builds, and pushes:
- Base image with PyTorch + custom SB3 forks + CybORG
- Training image for running training jobs
- Evaluation image (with Metasploit for AWS emulation)

**Option B: Build Locally (Slower)**

```bash
cd ../docker

# Build and push all images
./build.sh

# Build only training image
./build.sh --training-only
```

### 5. Upload Configuration Files

```bash
./scripts/upload_configs.sh
```

This uploads algorithm configs and scenarios to S3.

### 6. Launch Training Job

Option A: Use the helper script (recommended):

```bash
./scripts/launch_training.sh drqn 500000
```

Option B: Use Terraform variables:

```bash
# Edit terraform.tfvars:
#   launch_training_job = true
#   training_algorithm = "drqn"
#   training_total_steps = 500000

terraform apply
```

## Directory Structure

```
terraform/
├── main.tf                     # Main orchestration (instantiates modules)
├── variables.tf                # Input variables (incl. Git repos)
├── outputs.tf                  # Output values
├── backend.tf                  # Terraform state backend config
├── terraform.tfvars.example    # Example configuration
│
├── modules/
│   ├── base-infrastructure/    # ECR, S3, IAM, VPC, CodeBuild
│   │   ├── main.tf
│   │   ├── iam.tf
│   │   ├── ecr.tf
│   │   ├── s3.tf
│   │   ├── codebuild.tf        # CodeBuild project for Docker builds
│   │   ├── vpc.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│
└── scripts/
    ├── build_images.sh         # Trigger CodeBuild (AWS build)
    ├── launch_training.py      # Launch training jobs (boto3)
    ├── launch_training.sh      # Bash wrapper for launch_training.py
    └── upload_configs.sh       # Upload configs to S3
```

## Modules

### base-infrastructure

Creates core AWS resources needed for SageMaker training:

**Resources:**
- ECR repositories (base, training, evaluation)
- CodeBuild project for building Docker images from Git
- S3 bucket with lifecycle policies
- IAM roles for SageMaker and CodeBuild
- CloudWatch log groups
- (Optional) VPC with NAT gateway for AWS emulation mode

**Usage:**
```hcl
module "base_infrastructure" {
  source = "./modules/base-infrastructure"

  project_name          = "cyborg-rl"
  environment           = "research"
  git_repository_url    = "https://github.com/yourorg/cyborg-sagemaker"
  git_branch            = "main"
  cyborg_repository_url = "https://github.com/yourorg/cyborg"
  cyborg_branch         = "main"
  enable_aws_emulation  = false
}
```

**Note:** Training jobs are NOT launched via Terraform. They are transient workloads launched using the Python/bash helper scripts below.

## Helper Scripts

### launch_training.py

Python script using boto3 to launch SageMaker training jobs.

```bash
# Full control with all options
python scripts/launch_training.py \
  --algorithm drqn \
  --total-steps 500000 \
  --instance-type ml.g4dn.xlarge \
  --seed 42 \
  --hyperparameter learning_rate=0.00005 \
  --hyperparameter batch_size=64

# Simple usage
python scripts/launch_training.py --algorithm drqn --total-steps 500000
```

**Key Features:**
- Validates infrastructure and prerequisites
- Checks Docker images exist in ECR
- Verifies configs are uploaded to S3
- Configures CloudWatch metrics automatically
- Supports custom hyperparameters
- Provides monitoring URLs

**Options:**
- `--algorithm` - Algorithm to train (drqn, dqn, ppo, recurrent_ppo)
- `--total-steps` - Total training steps
- `--scenario` - Scenario file (default: <algorithm>_scenario.yaml)
- `--instance-type` - SageMaker instance (default: ml.g4dn.xlarge)
- `--image-tag` - Docker image tag (default: latest)
- `--spot/--no-spot` - Enable spot training (default: enabled)
- `--seed` - Random seed (optional)
- `--environment-mode` - sim or aws (default: sim)
- `--hyperparameter KEY=VALUE` - Custom hyperparameters (repeatable)

### launch_training.sh

Bash wrapper for launch_training.py providing a simpler interface.

```bash
./scripts/launch_training.sh <algorithm> <total_steps> [scenario] [instance_type]

# Examples
./scripts/launch_training.sh drqn 500000
./scripts/launch_training.sh ppo 1000000 ppo_scenario.yaml ml.g4dn.2xlarge
```

**Environment Variables:**
- `SPOT_TRAINING=true|false` - Enable spot instances (default: true)
- `SEED=42` - Set random seed (default: random)

### upload_configs.sh

Uploads configuration files to S3.

```bash
./scripts/upload_configs.sh [--force]

# Examples
./scripts/upload_configs.sh          # Upload only new/modified files
./scripts/upload_configs.sh --force  # Force re-upload all files
```

## Instance Types

### Recommended GPU Instances for Training

| Instance Type | vCPUs | Memory | GPU | Price (On-Demand) | Price (Spot ~70% off) | Use Case |
|--------------|-------|--------|-----|-------------------|----------------------|----------|
| ml.g4dn.xlarge | 4 | 16 GB | 1x T4 (16GB) | $0.526/hr | ~$0.23/hr | DRQN, DQN (200K steps) |
| ml.g4dn.2xlarge | 8 | 32 GB | 1x T4 (16GB) | $0.94/hr | ~$0.42/hr | PPO (400K+ steps) |
| ml.g5.xlarge | 4 | 16 GB | 1x A10G (24GB) | $1.006/hr | ~$0.44/hr | Larger models |

## Cost Estimation

### DRQN Training
- Steps: 200K - 500K
- Instance: ml.g4dn.xlarge (spot)
- Runtime: 4-6 hours
- **Cost: ~$1-2 per run**

### PPO Training
- Steps: 400K - 1M
- Instance: ml.g4dn.2xlarge (spot)
- Runtime: 8-12 hours
- **Cost: ~$3-5 per run**

## Monitoring

### View Training Job Status

```bash
# List all training jobs
aws sagemaker list-training-jobs --sort-by CreationTime --sort-order Descending --max-results 10

# Describe specific job
aws sagemaker describe-training-job --training-job-name <job-name>
```

### Stream Logs

```bash
# Get job name from Terraform output
JOB_NAME=$(terraform output -raw training_job_name)

# Stream logs
aws logs tail /aws/sagemaker/TrainingJobs --follow --filter-pattern $JOB_NAME
```

### View Metrics in CloudWatch

Use the console URLs from Terraform outputs:

```bash
terraform output job_console_url
terraform output cloudwatch_logs_url
terraform output cloudwatch_metrics_url
```

## S3 Structure

After deployment, your S3 bucket will have the following structure:

```
s3://<bucket>/
├── configs/
│   ├── algorithms/          # YAML configs for each algorithm
│   │   ├── drqn.yaml
│   │   ├── dqn.yaml
│   │   ├── ppo.yaml
│   │   └── recurrent_ppo.yaml
│   └── environments/
│       └── scenarios/       # Scenario YAML files
│           ├── drqn_scenario.yaml
│           └── ...
│
├── models/                  # Trained models by algorithm
│   ├── drqn/
│   │   └── <job-name>/
│   │       └── output/
│   │           └── model.tar.gz
│   └── ...
│
├── checkpoints/             # Training checkpoints
│   └── <job-name>/
│       ├── checkpoint_10000.zip
│       └── ...
│
└── tensorboard/             # TensorBoard logs
    └── <algorithm>/
        └── <job-name>/
```

## Workflows

### Initial Setup

```bash
# 1. Configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars

# 2. Deploy infrastructure
terraform init
terraform apply

# 3. Build and push images
cd ../docker
./build.sh --push

# 4. Upload configs
cd ../terraform
./scripts/upload_configs.sh
```

### Launch Training

```bash
# Option 1: Helper script
./scripts/launch_training.sh drqn 500000

# Option 2: Terraform variables
# Edit terraform.tfvars: launch_training_job = true
terraform apply
```

### Monitor Training

```bash
# Stream logs
JOB_NAME=$(terraform output -raw training_job_name)
aws logs tail /aws/sagemaker/TrainingJobs --follow --filter-pattern $JOB_NAME

# Check status
aws sagemaker describe-training-job --training-job-name $JOB_NAME
```

### Download Trained Model

```bash
# Get model S3 URI
MODEL_URI=$(terraform output -raw model_artifacts_s3_uri)

# Download model
aws s3 cp $MODEL_URI ./model.tar.gz

# Extract model
tar -xzf model.tar.gz
```

## Troubleshooting

### Infrastructure not deployed

**Error:** "Could not get S3 bucket from Terraform output"

**Solution:**
```bash
terraform apply
```

### Docker images not found

**Error:** "Training image not found in ECR"

**Solution:**
```bash
cd ../docker
./build.sh --push
```

### Configs not found in S3

**Error:** "Algorithm config not found in S3"

**Solution:**
```bash
./scripts/upload_configs.sh
```

### Training job fails immediately

Check CloudWatch logs:
```bash
JOB_NAME=$(terraform output -raw training_job_name)
aws logs tail /aws/sagemaker/TrainingJobs --filter-pattern $JOB_NAME
```

Common issues:
- Scenario file not found in S3
- Invalid hyperparameters
- Image not pushed to ECR
- IAM role missing permissions

### Out of memory errors

Solutions:
- Increase instance type (ml.g4dn.2xlarge)
- Reduce batch_size hyperparameter
- Reduce num_prev_seq (for DRQN)

## Advanced Configuration

### Custom SB3 Forks

To use specific commits of stable-baselines3:

```bash
cd ../docker
SB3_BRANCH=abc123 SB3_CONTRIB_BRANCH=def456 ./build.sh --push
```

### AWS Emulation Mode

To enable VPC for AWS emulation:

```hcl
# In terraform.tfvars
enable_aws_emulation = true
vpc_cidr = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]
```

### Custom Hyperparameters

```hcl
# In terraform.tfvars
training_hyperparameters = {
  learning_rate      = "0.00005"
  num_prev_seq       = "30"
  exploration_fraction = "0.8"
}
```

These will be merged with defaults from `configs/algorithms/drqn.yaml`.

## Clean Up

To destroy all infrastructure:

```bash
# Warning: This deletes all resources including S3 bucket!
terraform destroy
```

To keep models but clean up infrastructure:

```bash
# Download models first
aws s3 sync s3://$(terraform output -raw artifacts_bucket)/models/ ./saved-models/

# Then destroy
terraform destroy
```

## Next Steps

After successful training:
1. Download and evaluate models locally
2. Implement evaluation-job module for SageMaker Processing jobs
3. Set up CI/CD pipeline for automated training
4. Implement hyperparameter tuning with SageMaker HPO
