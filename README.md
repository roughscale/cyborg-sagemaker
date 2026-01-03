# CybORG RL - AWS SageMaker Deployment

Deploy CybORG pentesting reinforcement learning agents to AWS SageMaker for scalable training and evaluation.

## Project Status

DRQN training pipeline deployed and tested. Infrastructure supports DRQN, DQN, PPO, and RecurrentPPO algorithms in both simulation and AWS emulation modes.

**Completed:**
- Terraform infrastructure (IAM, ECR, S3, VPC, CodeBuild)
- Docker build pipeline with selective image building
- DRQN training implementation with hyperparameter optimization
- CloudWatch metrics and TensorBoard integration
- S3 checkpointing and model persistence
- Configuration management (YAML configs, scenarios)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    CodeBuild                                │ │
│  │  Clones Git repos → Builds Docker images → Pushes to ECR  │ │
│  │  Supports selective builds (base/training/evaluation)     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│                            ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    ECR Repositories                        │  │
│  │  - base: PyTorch + all Python dependencies                │  │
│  │  - training: SB3 repos + CybORG + training code           │  │
│  │  - evaluation: SB3 repos + CybORG + Metasploit            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                     │
│  ┌─────────────────────────▼───────────────────────────────┐   │
│  │                   SageMaker                               │   │
│  │  ┌──────────────────┐       ┌──────────────────┐        │   │
│  │  │  Training Jobs   │       │ Processing Jobs  │        │   │
│  │  │  (GPU instances) │       │ (CPU instances)  │        │   │
│  │  │  DRQN, DQN       │       │  Evaluation      │        │   │
│  │  │  PPO, RecPPO     │       │  AWS Emulation   │        │   │
│  │  └────────┬─────────┘       └────────┬─────────┘        │   │
│  │           └──────────────┬────────────┘                  │   │
│  │                          ▼                               │   │
│  │           ┌────────────────────────────┐                 │   │
│  │           │       S3 Bucket            │                 │   │
│  │           │  Models & Checkpoints      │                 │   │
│  │           │  TensorBoard Logs          │                 │   │
│  │           │  Configuration Files       │                 │   │
│  │           └────────────────────────────┘                 │   │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.5
- AWS CLI configured
- Git repositories for cyborg-sagemaker and cyborg

### 1. Configure Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
- `git_repository_url` - cyborg-sagemaker Git repository URL
- `cyborg_repository_url` - CybORG Git repository URL
- `aws_region` - AWS region (default: ap-southeast-2)

### 2. Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

Creates ECR repositories, S3 bucket, IAM roles, CodeBuild project, and optional VPC for AWS emulation.

### 3. Build Docker Images

CodeBuild clones repositories, builds images, and pushes to ECR:

```bash
# Build all images
./scripts/build_images.sh --follow

# Build only training image (pulls base from ECR)
./scripts/build_images.sh --training-only --follow

# Build from specific branches
./scripts/build_images.sh \
  --git-branch feature/new-algo \
  --cyborg-branch develop \
  --sb3-contrib feature/drqn_fixes \
  --follow
```

The base image contains all Python dependencies. Training and evaluation images clone and install code repositories at build time, enabling fast iteration when modifying experimental code.

### 4. Upload Configuration Files

```bash
./scripts/upload_configs.sh
```

### 5. Launch Training Job

```bash
# Basic usage
python scripts/launch_training.py --algorithm drqn --total-steps 500000

# With custom hyperparameters
python scripts/launch_training.py \
  --algorithm drqn \
  --total-steps 500000 \
  --instance-type ml.g4dn.xlarge \
  --hyperparameter use_full_episodes=false \
  --hyperparameter zero_init_lstm_states=true
```

Hyperparameters from `configs/algorithms/drqn.yaml` are automatically loaded and displayed in the SageMaker console (16 parameter display limit). Job metadata (scenario_name, environment_mode) is passed as environment variables.

### 6. Monitor Training

```bash
# Stream logs
JOB_NAME=<training-job-name>
aws logs tail /aws/sagemaker/TrainingJobs --follow --filter-pattern $JOB_NAME
```

CloudWatch metrics available in SageMaker console:
- episode_reward, episode_length, episode_number, total_timesteps
- exploration_rate, loss, per_beta (DRQN-specific)

## Project Structure

```
cyborg-sagemaker/
├── terraform/
│   ├── main.tf, variables.tf, outputs.tf
│   ├── modules/
│   │   └── base-infrastructure/         # ECR, S3, IAM, VPC, CodeBuild
│   └── scripts/
│       ├── build_images.sh              # Trigger CodeBuild
│       ├── launch_training.py           # Launch training via boto3
│       └── upload_configs.sh            # Upload configs to S3
│
├── docker/
│   ├── base/                            # Dependencies only
│   ├── training/                        # Clone repos + training code
│   ├── evaluation/                      # Clone repos + Metasploit
│   ├── buildspec.yml                    # CodeBuild spec with selective builds
│   └── build.sh                         # Local build script
│
├── src/
│   ├── common/                          # Shared constants and logging
│   ├── training/
│   │   ├── train.py                     # Entry point (reads env vars)
│   │   ├── algorithms/                  # DRQN trainer
│   │   ├── callbacks/                   # CloudWatch, checkpointing
│   │   └── utils/                       # Env factory, config, S3
│   └── evaluation/                      # Evaluation implementation
│
└── configs/
    ├── algorithms/                      # DRQN hyperparameters
    └── environments/scenarios/          # DRQN scenario
```

## Key Technologies

- Cloud: AWS SageMaker, CodeBuild, S3, ECR, VPC
- IaC: Terraform
- Containers: Docker, PyTorch 2.0.1
- ML: Stable-Baselines3 (custom forks with DRQN)
- RL Algorithms: DRQN, DQN, PPO, Recurrent PPO
- Environment: CybORG (pentesting simulation)

## Docker Build Strategy

Base image contains all Python dependencies for SB3, SB3-contrib, and CybORG. Training and evaluation images clone repositories and install code with `pip install -e`, enabling fast rebuilds when code changes:

- Dependency change: rebuild base image (slow, ~10-15 min)
- Code change: rebuild training/evaluation only (fast, ~2-3 min)

The `--training-only`, `--base-only`, and `--evaluation-only` flags control which images to build.

## Cost Estimates

**Docker Builds:**
- CodeBuild: $0.15-0.30 per build (15-20 min)
- ECR Storage: $0.10/GB/month (6-8GB total)

**Training (per run):**
- DRQN: $1-2 (200K steps, 4-6 hours, ml.g4dn.xlarge spot)
- PPO: $3-5 (400K steps, 8-12 hours, ml.g4dn.2xlarge spot)

**Evaluation:**
- Simulation: $0.02-0.06 (100 episodes, 30 min, ml.m5.large spot)
- AWS Emulation: $0.80-1.20 (10 episodes, 2-3 hours, ml.c5.2xlarge)

**Infrastructure (monthly):**
- S3 + ECR + CloudWatch: $2-10

## Dependencies

**Custom Forks:**
- [stable-baselines3](https://github.com/roughscale/stable-baselines3)
- [stable-baselines3-contrib](https://github.com/roughscale/stable-baselines3-contrib) (DRQN with full episode support)

**Source Code:**
- CybORG: `/home/boloughlin/projects/roughscale/research/rl/cyborg/CybORG/CybORG/`
- Reference: `/home/boloughlin/projects/roughscale/research/rl/cyborg/CybORG/openai_*_msf_test.py`

## License

Inherits licenses from CybORG, Stable-Baselines3 (MIT), and AWS SageMaker (AWS Customer Agreement).

---

**Last Updated:** 2026-01-03
