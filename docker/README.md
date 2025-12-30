# Docker Images for CybORG SageMaker Deployment

This directory contains Dockerfiles and build scripts for creating the CybORG SageMaker training and evaluation containers.

## Build Options

### **Option A: AWS CodeBuild (Recommended)**
- Builds images in AWS cloud
- Clones source from Git repositories
- Triggered via `terraform/scripts/build_images.sh`

### **Option B: Local Build**
- Builds images on your local machine
- Good for development and testing
- Uses `docker/build.sh` script

## Image Architecture

```
┌─────────────────────────────────────────────────────┐
│  Base Image (cyborg-rl-base)                        │
│  - PyTorch 2.0.1 + CUDA 11.7                        │
│  - Custom SB3 forks (configurable via build args)  │
│  - CybORG dependencies                              │
└────────────────┬────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
┌────────────────┐  ┌──────────────────┐
│ Training Image │  │ Evaluation Image │
│ - CybORG src   │  │ - CybORG src     │
│ - Training code│  │ - Eval code      │
│ - SageMaker TK │  │ - Metasploit     │
└────────────────┘  └──────────────────┘
```

## Build Arguments

The base image supports the following build arguments to configure which versions of the SB3 libraries to use:

| Argument | Default | Description |
|----------|---------|-------------|
| `SB3_REPO` | `https://github.com/roughscale/stable-baselines3.git` | Stable-Baselines3 repository URL |
| `SB3_BRANCH` | `master` | Branch, tag, or commit hash to checkout |
| `SB3_CONTRIB_REPO` | `https://github.com/roughscale/stable-baselines3-contrib.git` | SB3-Contrib repository URL |
| `SB3_CONTRIB_BRANCH` | `master` | Branch, tag, or commit hash to checkout |

## Quick Start

### Option A: Build with CodeBuild (Recommended)

```bash
cd /path/to/cyborg-sagemaker/terraform

# Build all images in AWS and push to ECR (with real-time logs)
./scripts/build_images.sh --follow

# Build with custom tag
./scripts/build_images.sh --tag v1.0.0 --follow

# Build from specific Git branches
./scripts/build_images.sh \
  --git-branch feature/new-algo \
  --cyborg-branch develop \
  --sb3-branch abc123def

# Build with custom SB3 commits for reproducibility
./scripts/build_images.sh \
  --sb3-branch abc123def456 \
  --sb3-contrib def456abc123 \
  --tag 20251231
```

### Option B: Build Locally

```bash
cd /path/to/cyborg-sagemaker

# Build all images with default branches (master)
./docker/build.sh

# Build and push all images to ECR
./docker/build.sh

# Build with specific commit hashes for reproducibility
SB3_BRANCH=abc123 SB3_CONTRIB_BRANCH=def456 ./docker/build.sh

# Build only training image (faster iteration)
./docker/build.sh --training-only

# Build locally without pushing
./docker/build.sh --build-only

# Or use environment file
cp docker/build.env.example docker/build.env
# Edit build.env with your settings
source docker/build.env
./docker/build.sh
```

## Manual Build Examples

### Base Image with Custom SB3 Versions

```bash
docker build \
  --build-arg SB3_BRANCH=abc123def456 \
  --build-arg SB3_CONTRIB_BRANCH=def456abc123 \
  -t cyborg-rl-base:custom \
  -f docker/base/Dockerfile \
  ..
```

### Training Image

```bash
# For local development (doesn't require ECR base)
docker build \
  -t cyborg-rl-training:latest \
  -f docker/training/Dockerfile \
  ..

# For ECR deployment
docker build \
  --build-arg AWS_ACCOUNT_ID=123456789012 \
  --build-arg AWS_REGION=ap-southeast-2 \
  --build-arg ENVIRONMENT=dev \
  -t cyborg-rl-training:latest \
  -f docker/training/Dockerfile \
  ..
```

### Evaluation Image

```bash
docker build \
  -t cyborg-rl-evaluation:latest \
  -f docker/evaluation/Dockerfile \
  ..
```

## Inspecting Built Images

### Check SB3 Versions

```bash
# Check installed version
docker run --rm cyborg-rl-base:latest python -c \
  "import stable_baselines3; print(stable_baselines3.__version__)"

# Check labels
docker inspect cyborg-rl-base:latest | grep -A 10 Labels
```

### View Build Configuration

```bash
# See which branch/commit was used
docker inspect cyborg-rl-base:latest --format '{{.Config.Labels}}'
```

## Image Labels

All images include labels for tracking:

- `sb3.repo`: Stable-Baselines3 repository URL
- `sb3.branch`: Branch/tag/commit used
- `sb3_contrib.repo`: SB3-Contrib repository URL
- `sb3_contrib.branch`: Branch/tag/commit used

## Files

- **base/Dockerfile**: Base image with PyTorch and SB3 forks
- **base/requirements.txt**: CybORG dependencies
- **training/Dockerfile**: Training container with SageMaker Training Toolkit
- **evaluation/Dockerfile**: Evaluation container with Metasploit
- **evaluation/metasploit-setup.sh**: Metasploit installation script
- **buildspec.yml**: AWS CodeBuild build specification
- **build.sh**: Local build script with argument support
- **build.env.example**: Example environment configuration for local builds

## Troubleshooting

### Build fails with git checkout error

The specified branch/commit doesn't exist. Check:
```bash
# List available branches
git ls-remote --heads https://github.com/roughscale/stable-baselines3.git

# List available tags
git ls-remote --tags https://github.com/roughscale/stable-baselines3.git
```

### Docker context issues

The Dockerfiles expect to be built from the parent directory (research/rl/) because they need to access the `cyborg/` directory. The build script handles this automatically.

### ECR authentication

If push fails:
```bash
aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.ap-southeast-2.amazonaws.com
```

## Best Practices

### For Development
- Use `main` branch for latest features
- Use local builds without --push
- Iterate quickly with --base-only when testing changes

### For Production
- **Always use specific commit hashes** for reproducibility
- Tag images with dates or versions (e.g., `IMAGE_TAG=2024-12-27`)
- Document which commits were used in training runs
- Test locally before pushing to ECR

### Example Production Build

```bash
# Get current commit hashes
cd /path/to/stable-baselines3
SB3_COMMIT=$(git rev-parse HEAD)

cd /path/to/stable-baselines3-contrib
SB3_CONTRIB_COMMIT=$(git rev-parse HEAD)

# Build with specific commits
cd /path/to/cyborg-sagemaker
SB3_BRANCH=$SB3_COMMIT \
SB3_CONTRIB_BRANCH=$SB3_CONTRIB_COMMIT \
IMAGE_TAG=$(date +%Y%m%d) \
AWS_ACCOUNT_ID=123456789012 \
./docker/build.sh --push

# Document the build
echo "Training run 2024-12-27:" > builds.log
echo "  SB3: $SB3_COMMIT" >> builds.log
echo "  SB3-Contrib: $SB3_CONTRIB_COMMIT" >> builds.log
```

## Size Optimization

The multi-stage build reduces image size:
- Builder stage: ~8GB (includes build tools, git, source code)
- Runtime base: ~6GB (only runtime dependencies)
- Training: ~6.5GB (base + CybORG + training code)
- Evaluation: ~8.5GB (base + CybORG + eval code + Metasploit)

## CodeBuild Configuration

The `buildspec.yml` file defines the CodeBuild process:

1. **pre_build**: Login to ECR, clone CybORG repository, set environment variables
2. **build**: Build base → training → evaluation images sequentially
3. **post_build**: Tag and push all images to ECR

CodeBuild environment variables (can be overridden when triggering builds):
- `IMAGE_TAG`: Docker image tag (default: latest)
- `ENVIRONMENT`: Environment name (default: research)
- `CYBORG_REPO`: CybORG repository URL
- `CYBORG_BRANCH`: CybORG branch/commit
- `SB3_REPO`: Stable-Baselines3 repository URL
- `SB3_BRANCH`: SB3 branch/commit
- `SB3_CONTRIB_REPO`: SB3-Contrib repository URL
- `SB3_CONTRIB_BRANCH`: SB3-Contrib branch/commit

## Next Steps

After building images:
1. Verify images in ECR: Check AWS Console → ECR
2. Upload configs to S3: `cd ../terraform && ./scripts/upload_configs.sh`
3. Launch SageMaker training job: `python scripts/launch_training.py --algorithm drqn --total-steps 750000`
