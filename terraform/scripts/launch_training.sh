#!/usr/bin/env bash
#
# Wrapper script for launch_training.py
#
# This provides a simpler interface for launching training jobs.
# For more options, use launch_training.py directly.
#
# Usage:
#   ./launch_training.sh <algorithm> <total_steps> [scenario] [instance_type]
#
# Examples:
#   ./launch_training.sh drqn 500000
#   ./launch_training.sh ppo 1000000 ppo_scenario.yaml ml.g4dn.2xlarge

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if Python script exists
if [ ! -f "$SCRIPT_DIR/launch_training.py" ]; then
    echo "ERROR: launch_training.py not found"
    exit 1
fi

# Parse arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <algorithm> <total_steps> [scenario] [instance_type]"
    echo ""
    echo "Examples:"
    echo "  $0 drqn 500000"
    echo "  $0 ppo 1000000 ppo_scenario.yaml ml.g4dn.2xlarge"
    echo ""
    echo "For more options, use: python launch_training.py --help"
    exit 1
fi

ALGORITHM=$1
TOTAL_STEPS=$2
SCENARIO=${3:-}
INSTANCE_TYPE=${4:-ml.g4dn.xlarge}

# Build Python command
CMD=("python3" "$SCRIPT_DIR/launch_training.py"
     "--algorithm" "$ALGORITHM"
     "--total-steps" "$TOTAL_STEPS"
     "--instance-type" "$INSTANCE_TYPE")

# Add scenario if provided
if [ -n "$SCENARIO" ]; then
    CMD+=("--scenario" "$SCENARIO")
fi

# Add spot training flag from environment variable
if [ "${SPOT_TRAINING:-true}" = "false" ]; then
    CMD+=("--no-spot")
fi

# Add seed from environment variable
if [ -n "${SEED:-}" ]; then
    CMD+=("--seed" "$SEED")
fi

# Execute Python script
exec "${CMD[@]}"
