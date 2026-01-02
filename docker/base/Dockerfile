# Base image with all Python dependencies for SB3, SB3-contrib, and CybORG
# This image rarely changes (only when dependencies update)
FROM pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime

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

# Install all Python dependencies for SB3, SB3-contrib, and CybORG
# This includes all dependencies so that pip install -e in training image is fast
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

# Labels for tracking
LABEL maintainer="CybORG RL Team"
LABEL description="CybORG RL Base Image with PyTorch and all dependencies"

# Default command (will be overridden by SageMaker)
CMD ["python"]
