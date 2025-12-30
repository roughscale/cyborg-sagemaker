# Use official PyTorch image (pip-based, slimmer than AWS DLC)
FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

# Build arguments for SB3 repository configuration
ARG SB3_REPO=https://github.com/roughscale/stable-baselines3.git
ARG SB3_BRANCH=master
ARG SB3_CONTRIB_REPO=https://github.com/roughscale/stable-baselines3-contrib.git
ARG SB3_CONTRIB_BRANCH=master

# Set timezone to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

WORKDIR /tmp

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    curl \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install SageMaker Training Toolkit
RUN pip install --no-cache-dir sagemaker-training

# Clone and install custom stable-baselines3 fork
RUN git clone ${SB3_REPO} /opt/stable-baselines3 && \
    cd /opt/stable-baselines3 && \
    git checkout ${SB3_BRANCH} && \
    echo "stable-baselines3: $(git rev-parse HEAD)" && \
    pip install --no-cache-dir -e .

# Clone and install custom sb3-contrib fork
RUN git clone ${SB3_CONTRIB_REPO} /opt/stable-baselines3-contrib && \
    cd /opt/stable-baselines3-contrib && \
    git checkout ${SB3_CONTRIB_BRANCH} && \
    echo "stable-baselines3-contrib: $(git rev-parse HEAD)" && \
    pip install --no-cache-dir -e .

# Install CybORG dependencies
COPY cyborg-sagemaker/docker/base/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Create SageMaker directories
RUN mkdir -p \
    /opt/ml/code \
    /opt/ml/model \
    /opt/ml/checkpoints \
    /opt/ml/output \
    /opt/ml/input/data \
    /opt/ml/input/config

# Set SageMaker environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV SAGEMAKER_PROGRAM=train.py
ENV SAGEMAKER_SUBMIT_DIRECTORY=/opt/ml/code

WORKDIR /opt/ml/code

# Labels for tracking build configuration
LABEL maintainer="CybORG RL Team"
LABEL description="CybORG RL Base Image with PyTorch and custom SB3 forks"
LABEL sb3.repo="${SB3_REPO}"
LABEL sb3.branch="${SB3_BRANCH}"
LABEL sb3_contrib.repo="${SB3_CONTRIB_REPO}"
LABEL sb3_contrib.branch="${SB3_CONTRIB_BRANCH}"

# Default command (will be overridden by SageMaker)
CMD ["python"]
