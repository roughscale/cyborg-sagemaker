# CybORG RL - AWS SageMaker Deployment

Deploy CybORG pentesting reinforcement learning agents to AWS SageMaker for scalable training and evaluation.

## 🎯 Project Goals

- Train CybORG RL agents (DRQN, DQN, PPO, RecurrentPPO) on AWS SageMaker
- Support both simulation and AWS emulation modes
- Infrastructure as Code with Terraform
- Production-ready with monitoring, checkpointing, and cost optimization

## 📊 Current Status

**Phase 1-4 Complete:** DRQN training pipeline ready for deployment
- ✅ Terraform infrastructure (IAM, ECR, S3, VPC, CodeBuild)
- ✅ CodeBuild for building Docker images in AWS (faster ECR push)
- ✅ Docker containers with configurable SB3 fork versions
- ✅ Training source code (env_factory, train.py, DRQN trainer, callbacks)
- ✅ Configuration management (YAML configs, scenarios)
- ✅ Helper scripts (build_images.sh, launch_training.py, upload_configs.sh)
- ✅ Simplified single-environment setup

**Ready to Deploy:** Infrastructure can be deployed and DRQN training can begin!

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    CodeBuild                                │ │
│  │  Clones Git repos → Builds Docker images → Pushes to ECR  │ │
│  │  (cyborg + cyborg-sagemaker)                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│                            ▼                                     │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    ECR Repositories                        │  │
│  │  - cyborg-rl-research/base       (PyTorch + SB3)         │  │
│  │  - cyborg-rl-research/training   (CybORG + training)     │  │
│  │  - cyborg-rl-research/evaluation (+ Metasploit)          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                     │
│  ┌─────────────────────────▼───────────────────────────────┐   │
│  │                   SageMaker                               │   │
│  │  ┌──────────────────┐       ┌──────────────────┐        │   │
│  │  │  Training Jobs   │       │ Processing Jobs  │        │   │
│  │  │  (GPU instances) │       │ (CPU instances)  │        │   │
│  │  │  - DRQN, DQN     │       │  - Evaluation    │        │   │
│  │  │  - PPO, RecPPO   │       │  - AWS Emulation │        │   │
│  │  └────────┬─────────┘       └────────┬─────────┘        │   │
│  │           └──────────────┬────────────┘                  │   │
│  │                          ▼                               │   │
│  │           ┌────────────────────────────┐                 │   │
│  │           │       S3 Bucket            │                 │   │
│  │           │  - Models/Checkpoints      │                 │   │
│  │           │  - TensorBoard/Configs     │                 │   │
│  │           └────────────────────────────┘                 │   │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.5
- AWS CLI configured
- Git repositories:
  - `cyborg-sagemaker` (this repository)
  - `cyborg` (CybORG source)

### 1. Configure Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and configure:
- `git_repository_url` - Your cyborg-sagemaker Git repository URL
- `cyborg_repository_url` - Your CybORG Git repository URL
- `aws_region` - AWS region (default: ap-southeast-2)
- Other project settings

### 2. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review plan
terraform plan

# Deploy (creates ECR, S3, IAM roles, CodeBuild, optional VPC)
terraform apply
```

### 3. Build and Push Docker Images

**Option A: Build in AWS (Recommended - faster ECR push)**

```bash
# CodeBuild clones Git repos, builds images, pushes to ECR
./scripts/build_images.sh --follow

# Build from specific branches
./scripts/build_images.sh \
  --git-branch feature/new-algo \
  --cyborg-branch develop \
  --sb3-branch abc123

# Build with custom tag
./scripts/build_images.sh --tag v1.0.0 --follow
```

**Option B: Build Locally (slower for large images)**

```bash
cd ../docker

# Build and push all images
./build.sh

# Build only training image
./build.sh --training-only

# Build with specific SB3 commits
SB3_BRANCH=abc123 SB3_CONTRIB_BRANCH=def456 ./build.sh
```

### 4. Upload Configuration Files

```bash
cd ../terraform
./scripts/upload_configs.sh
```

### 5. Launch Training Job

```bash
# Using Python (recommended for full control):
python scripts/launch_training.py --algorithm drqn --total-steps 500000

# Or using bash wrapper for convenience:
./scripts/launch_training.sh drqn 500000

# With custom settings:
python scripts/launch_training.py \
  --algorithm drqn \
  --total-steps 500000 \
  --instance-type ml.g4dn.xlarge \
  --seed 42 \
  --hyperparameter learning_rate=0.00005
```

### 6. Monitor Training

```bash
# Get console URLs
terraform output job_console_url
terraform output cloudwatch_logs_url

# Or stream logs directly
JOB_NAME=$(terraform output -raw training_job_name)
aws logs tail /aws/sagemaker/TrainingJobs --follow --filter-pattern $JOB_NAME
```

## 📁 Project Structure

```
cyborg-sagemaker/
├── terraform/
│   ├── main.tf                     # ✅ Main orchestration
│   ├── variables.tf                # ✅ Input variables (incl. Git repos)
│   ├── outputs.tf                  # ✅ Output values
│   ├── backend.tf                  # ✅ State backend config
│   ├── terraform.tfvars.example    # ✅ Example configuration
│   ├── modules/
│   │   ├── base-infrastructure/    # ✅ ECR, S3, IAM, VPC, CodeBuild
│   │   └── evaluation-job/         # ⏳ SageMaker processing jobs (future)
│   └── scripts/
│       ├── build_images.sh         # ✅ Trigger CodeBuild
│       ├── launch_training.py      # ✅ Launch training (boto3)
│       ├── launch_training.sh      # ✅ Bash wrapper
│       └── upload_configs.sh       # ✅ Upload configs to S3
│
├── docker/
│   ├── base/                       # ✅ Base image (PyTorch + SB3)
│   ├── training/                   # ✅ Training container
│   ├── evaluation/                 # ✅ Evaluation container
│   ├── buildspec.yml               # ✅ CodeBuild build spec
│   ├── build.sh                    # ✅ Local build script
│   └── build.env.example           # ✅ Example build config
│
├── src/
│   ├── common/                     # ✅ Shared utilities
│   ├── training/                   # ✅ DRQN training (DQN, PPO, RecurrentPPO pending)
│   │   ├── train.py                # ✅ Main entry point
│   │   ├── algorithms/             # ✅ DRQN trainer
│   │   ├── callbacks/              # ✅ CloudWatch, checkpointing
│   │   └── utils/                  # ✅ Env factory, config, S3
│   └── evaluation/                 # ⏳ Evaluation implementation
│
├── configs/
│   ├── algorithms/                 # ✅ DRQN config (others pending)
│   └── environments/
│       └── scenarios/              # ✅ DRQN scenario
│
└── scripts/                        # ⏳ Utility scripts
```

**Legend:** ✅ Complete | ⏳ Pending

## 🛠️ Key Technologies

- **Cloud:** AWS SageMaker, CodeBuild, S3, ECR, VPC
- **IaC:** Terraform
- **Containers:** Docker, PyTorch Official Images
- **ML:** PyTorch 2.0.1, Stable-Baselines3 (custom forks)
- **RL Algorithms:** DRQN, DQN, PPO, Recurrent PPO
- **Environment:** CybORG (pentesting simulation)

## 💰 Cost Estimates

### Docker Builds:
- **CodeBuild:** ~$0.15-0.30 per build (15-20 min on BUILD_GENERAL1_LARGE)
- **ECR Storage:** ~$0.10/GB/month (images are ~6-8GB total)

### Training (per run):
- **DRQN:** ~$1-2 (200K steps, 4-6 hours on ml.g4dn.xlarge spot)
- **PPO:** ~$3-5 (400K steps, 8-12 hours on ml.g4dn.2xlarge spot)

### Evaluation:
- **Simulation:** ~$0.02-0.06 (100 episodes, 30 min on ml.m5.large spot)
- **AWS Emulation:** ~$0.80-1.20 (10 episodes, 2-3 hours on ml.c5.2xlarge)

### Infrastructure (monthly):
- **S3 + ECR + CloudWatch:** ~$2-10 depending on retention policies

## 📚 Documentation

- **[terraform/README.md](terraform/README.md)** - Detailed Terraform usage guide
- **[terraform/modules/training-job/README.md](terraform/modules/training-job/README.md)** - Training job module docs
- **[Original Plan](/home/boloughlin/.claude/plans/cuddly-plotting-globe.md)** - Complete architecture design

## 🔗 Dependencies

### Custom Forks:
- [stable-baselines3](https://github.com/roughscale/stable-baselines3) - Custom DRQN/DQN implementations
- [stable-baselines3-contrib](https://github.com/roughscale/stable-baselines3-contrib) - DRQN, Recurrent PPO

### Source Code:
- CybORG: `/home/boloughlin/projects/roughscale/research/rl/cyborg/CybORG/CybORG/`
- Reference training: `/home/boloughlin/projects/roughscale/research/rl/cyborg/CybORG/openai_*_msf_test.py`

## 🤝 Contributing

This is a research project. To contribute:

1. Review the README files in terraform/ and training-job module for current status
2. Choose a pending task (DQN, PPO, RecurrentPPO trainers, or evaluation implementation)
3. Implement following the architecture in the original plan
4. Test locally before deploying to SageMaker

## 📝 License

Inherits licenses from:
- CybORG project
- Stable-Baselines3 (MIT)
- AWS SageMaker (AWS Customer Agreement)

## 🆘 Support

For questions or issues:
1. Check the terraform/README.md for detailed deployment instructions
2. Review existing training scripts in `/home/boloughlin/projects/roughscale/research/rl/cyborg/CybORG/`
3. Consult [AWS SageMaker documentation](https://docs.aws.amazon.com/sagemaker/)

---

**Status:** DRQN training pipeline complete and ready for deployment!
**Last Updated:** 2025-12-31

**Next Steps:**
1. Configure Git repos in `terraform/terraform.tfvars`
2. Deploy infrastructure: `cd terraform && terraform apply`
3. Build Docker images: `./scripts/build_images.sh --follow`
4. Upload configs: `./scripts/upload_configs.sh`
5. Launch DRQN training: `python scripts/launch_training.py --algorithm drqn --total-steps 750000`
