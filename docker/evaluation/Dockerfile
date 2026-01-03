# Evaluation container - clones code repositories and adds Metasploit
# This image rebuilds quickly when code changes (dependencies pre-installed in base)
FROM cyborg-rl-base:latest

# Build arguments for repository configuration
ARG SB3_REPO=https://github.com/roughscale/stable-baselines3.git
ARG SB3_BRANCH=master
ARG SB3_CONTRIB_REPO=https://github.com/roughscale/stable-baselines3-contrib.git
ARG SB3_CONTRIB_BRANCH=master
ARG CYBORG_REPO=https://github.com/roughscale/cyborg.git
ARG CYBORG_BRANCH=main

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

# Clone and install stable-baselines3
RUN git clone ${SB3_REPO} /opt/stable-baselines3 && \
    cd /opt/stable-baselines3 && \
    git checkout ${SB3_BRANCH} && \
    echo "stable-baselines3: $(git rev-parse HEAD)" && \
    pip install --no-cache-dir -e .

# Clone and install stable-baselines3-contrib
RUN git clone ${SB3_CONTRIB_REPO} /opt/stable-baselines3-contrib && \
    cd /opt/stable-baselines3-contrib && \
    git checkout ${SB3_CONTRIB_BRANCH} && \
    echo "stable-baselines3-contrib: $(git rev-parse HEAD)" && \
    pip install --no-cache-dir -e .

# Clone CybORG
RUN git clone ${CYBORG_REPO} /opt/cyborg && \
    cd /opt/cyborg && \
    git checkout ${CYBORG_BRANCH} && \
    echo "CybORG: $(git rev-parse HEAD)"

# Copy CybORG source to working directory
COPY cyborg/CybORG/CybORG /opt/ml/code/CybORG

# Copy evaluation source code
COPY cyborg-sagemaker/src/evaluation /opt/ml/code/evaluation
COPY cyborg-sagemaker/src/common /opt/ml/code/common

# Set working directory
WORKDIR /opt/ml/processing

# Labels for tracking build configuration
LABEL maintainer="CybORG RL Team"
LABEL description="CybORG RL Evaluation Container for SageMaker (with Metasploit)"
LABEL type="evaluation"
LABEL sb3.repo="${SB3_REPO}"
LABEL sb3.branch="${SB3_BRANCH}"
LABEL sb3_contrib.repo="${SB3_CONTRIB_REPO}"
LABEL sb3_contrib.branch="${SB3_CONTRIB_BRANCH}"
LABEL cyborg.repo="${CYBORG_REPO}"
LABEL cyborg.branch="${CYBORG_BRANCH}"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import torch; import stable_baselines3; import gymnasium; import pymetasploit3" || exit 1

# Entry point for SageMaker Processing Jobs
ENTRYPOINT ["python", "/opt/ml/code/evaluation/evaluate.py"]
