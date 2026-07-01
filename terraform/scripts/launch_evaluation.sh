#!/usr/bin/env bash
# Bash wrapper for launch_evaluation.py
#
# Usage:
#   ./scripts/launch_evaluation.sh <algorithm> <training-job-name> [n_episodes] [mode]
#
# Examples:
#   ./scripts/launch_evaluation.sh drqn cyborg-rl-drqn-20260101-120000
#   ./scripts/launch_evaluation.sh recurrent_ppo cyborg-rl-recurrent-ppo-20260101-120000 50
#   ./scripts/launch_evaluation.sh drqn cyborg-rl-drqn-20260101-120000 100 aws
#
# Environment Variables:
#   DETERMINISTIC=false   Disable deterministic policy (default: true)
#   IMAGE_TAG=v1.0.0      Docker image tag (default: latest)

set -e

ALGORITHM="${1:?Usage: $0 <algorithm> <training-job-name> [n_episodes] [mode]}"
TRAINING_JOB="${2:?Usage: $0 <algorithm> <training-job-name> [n_episodes] [mode]}"
N_EPISODES="${3:-100}"
MODE="${4:-sim}"

DETERMINISTIC="${DETERMINISTIC:-true}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python "${SCRIPT_DIR}/launch_evaluation.py" \
    --algorithm "${ALGORITHM}" \
    --training-job-name "${TRAINING_JOB}" \
    --n-eval-episodes "${N_EPISODES}" \
    --environment-mode "${MODE}" \
    --image-tag "${IMAGE_TAG}" \
    $( [ "${DETERMINISTIC}" = "false" ] && echo "--no-deterministic" )
