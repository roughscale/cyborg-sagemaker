# Training container - inherits from locally built base image
# When pushed to ECR, this will be tagged appropriately
FROM cyborg-rl-base:latest

# Copy CybORG source code (from context root)
# Exclude unnecessary files via .dockerignore
COPY cyborg/CybORG/CybORG /opt/ml/code/CybORG

# Copy training source code
COPY cyborg-sagemaker/src/training /opt/ml/code/training
COPY cyborg-sagemaker/src/common /opt/ml/code/common

# Install any training-specific dependencies (if needed)
# COPY docker/training/requirements-training.txt /tmp/requirements-training.txt
# RUN pip install --no-cache-dir -r /tmp/requirements-training.txt

# Set working directory
WORKDIR /opt/ml/code

# Set entry point to training script
ENV SAGEMAKER_PROGRAM=training/train.py

# Labels for tracking
LABEL maintainer="CybORG RL Team"
LABEL description="CybORG RL Training Container for SageMaker"
LABEL type="training"

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import torch; import stable_baselines3; import gymnasium" || exit 1

# Use SageMaker Training Toolkit entry point
ENTRYPOINT ["train"]
