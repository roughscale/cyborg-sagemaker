# Evaluation container - inherits from locally built base image and adds Metasploit
# When pushed to ECR, this will be tagged appropriately
FROM cyborg-rl-base:latest

# Install Metasploit Framework for AWS emulation mode
USER root

# Install Metasploit dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    software-properties-common \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy and run Metasploit setup script
COPY cyborg-sagemaker/docker/evaluation/metasploit-setup.sh /tmp/metasploit-setup.sh
RUN chmod +x /tmp/metasploit-setup.sh && \
    /tmp/metasploit-setup.sh && \
    rm /tmp/metasploit-setup.sh

# Install pymetasploit3 for Python integration
RUN pip install --no-cache-dir pymetasploit3==1.0.3 pyvelociraptor==0.1.3

# Copy CybORG source code (from context root)
COPY cyborg/CybORG/CybORG /opt/ml/code/CybORG

# Copy evaluation source code
COPY cyborg-sagemaker/src/evaluation /opt/ml/code/evaluation
COPY cyborg-sagemaker/src/common /opt/ml/code/common

# Set working directory
WORKDIR /opt/ml/processing

# Labels for tracking
LABEL maintainer="CybORG RL Team"
LABEL description="CybORG RL Evaluation Container for SageMaker (with Metasploit)"
LABEL type="evaluation"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import torch; import stable_baselines3; import gymnasium; import pymetasploit3" || exit 1

# Entry point for SageMaker Processing Jobs
ENTRYPOINT ["python", "/opt/ml/code/evaluation/evaluate.py"]
