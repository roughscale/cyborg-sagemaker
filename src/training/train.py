#!/usr/bin/env python3
"""
SageMaker training entry point for CybORG RL agents.

Environment variables set by SageMaker:
- SM_MODEL_DIR: /opt/ml/model (final model output)
- SM_OUTPUT_DATA_DIR: /opt/ml/output/data (for metrics)
- SM_CHANNEL_CONFIG: /opt/ml/input/data/config
- SM_CHANNEL_SCENARIOS: /opt/ml/input/data/scenarios
- SM_HPS: Hyperparameters as JSON
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Add CybORG to path
sys.path.insert(0, '/opt/ml/code')

from common.constants import SageMakerPaths, Algorithms
from common.logging_config import setup_logging, get_logger
from training.utils.env_factory import create_cyborg_environment
from training.utils.config_loader import (
    load_algorithm_config,
    extract_env_config,
    merge_configs
)
from training.callbacks.sagemaker_callback import SageMakerCallback
from training.callbacks.checkpoint_callback import CheckpointCallback

# Import algorithm trainers
from training.algorithms.drqn import train_drqn, get_drqn_default_hyperparameters

# Setup logging first
setup_logging()
logger = get_logger(__name__)


def parse_args():
    """Parse SageMaker hyperparameters from command line arguments."""
    parser = argparse.ArgumentParser(description='CybORG SageMaker Training')

    # Required hyperparameters
    parser.add_argument('--algorithm', type=str, required=True,
                       choices=Algorithms.ALL,
                       help='RL algorithm to train')
    parser.add_argument('--environment_mode', type=str, default='sim',
                       choices=['sim', 'aws'],
                       help='Environment mode (sim or aws)')
    parser.add_argument('--scenario_name', type=str, required=True,
                       help='Scenario YAML filename')
    parser.add_argument('--total_steps', type=int, required=True,
                       help='Total training timesteps')

    # Algorithm-agnostic hyperparameters
    parser.add_argument('--gamma', type=float, default=0.99,
                       help='Discount factor')
    parser.add_argument('--learning_rate', type=float, default=0.0001,
                       help='Learning rate')
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed for reproducibility')
    parser.add_argument('--device', type=str, default='auto',
                       choices=['auto', 'cuda', 'cpu'],
                       help='Device for training')

    # DQN/DRQN specific
    parser.add_argument('--batch_size', type=int, default=32,
                       help='Minibatch size for training')
    parser.add_argument('--buffer_size', type=int, default=None,
                       help='Replay buffer size (None = total_steps/5)')
    parser.add_argument('--initial_epsilon', type=float, default=1.0,
                       help='Initial exploration rate')
    parser.add_argument('--final_epsilon', type=float, default=0.02,
                       help='Final exploration rate')
    parser.add_argument('--exploration_fraction', type=float, default=0.9,
                       help='Fraction of training for epsilon decay')
    parser.add_argument('--double', type=lambda x: str(x).lower() == 'true', default=True,
                       help='Use Double DQN')
    parser.add_argument('--dueling', type=lambda x: str(x).lower() == 'true', default=True,
                       help='Use Dueling DQN')

    # DRQN specific
    parser.add_argument('--num_prev_seq', type=int, default=20,
                       help='Number of previous transitions in sequence')
    parser.add_argument('--prioritized_replay_alpha', type=float, default=0.9,
                       help='PER alpha (prioritization strength)')
    parser.add_argument('--prioritized_replay_beta0', type=float, default=0.4,
                       help='PER initial beta (importance sampling correction)')

    # PPO specific
    parser.add_argument('--n_steps', type=int, default=1024,
                       help='Number of steps per rollout')
    parser.add_argument('--n_epochs', type=int, default=10,
                       help='Number of epochs per update')
    parser.add_argument('--clip_range', type=float, default=0.1,
                       help='PPO clip range')
    parser.add_argument('--vf_coef', type=float, default=1.0,
                       help='Value function coefficient')
    parser.add_argument('--ent_coef', type=float, default=0.0,
                       help='Entropy coefficient')
    parser.add_argument('--gae_lambda', type=float, default=1.0,
                       help='GAE lambda')
    parser.add_argument('--target_kl', type=float, default=0.01,
                       help='Target KL divergence')

    # SageMaker specific
    parser.add_argument('--tensorboard_sync', type=lambda x: str(x).lower() == 'true', default=True,
                       help='Enable TensorBoard log syncing')
    parser.add_argument('--checkpoint_freq', type=int, default=10000,
                       help='Checkpoint frequency in steps')

    # Environment configuration
    parser.add_argument('--n_envs', type=int, default=1,
                       help='Number of parallel environments')

    args, _ = parser.parse_known_args()
    return args


def get_s3_bucket() -> str:
    """Get S3 bucket name from environment or Terraform output.

    Returns:
        S3 bucket name
    """
    # Try environment variable first
    bucket = os.environ.get('S3_BUCKET')
    if bucket:
        return bucket

    # Try to parse from SageMaker job config
    # SageMaker sets output path like: s3://bucket/path/to/output
    output_path = os.environ.get('SM_OUTPUT_DATA_DIR', '')
    if output_path.startswith('s3://'):
        bucket = output_path.split('/')[2]
        return bucket

    logger.warning("S3_BUCKET not set, checkpoints will not be synced to S3")
    return None


def main():
    """Main training entry point."""
    args = parse_args()

    logger.info("=" * 80)
    logger.info("CybORG SageMaker Training Job")
    logger.info("=" * 80)
    logger.info(f"Algorithm: {args.algorithm}")
    logger.info(f"Environment Mode: {args.environment_mode}")
    logger.info(f"Scenario: {args.scenario_name}")
    logger.info(f"Total Steps: {args.total_steps}")
    logger.info(f"Device: {args.device}")
    if args.seed is not None:
        logger.info(f"Seed: {args.seed}")
    logger.info("=" * 80)
    logger.info("")

    # Load algorithm configuration
    config_path = Path(SageMakerPaths.INPUT_CONFIG) / f"{args.algorithm}.yaml"
    logger.info(f"Loading configuration from: {config_path}")

    if config_path.exists():
        config = load_algorithm_config(str(config_path))
        env_config = extract_env_config(config)
        logger.info("Configuration loaded successfully")
    else:
        logger.warning(f"Configuration file not found: {config_path}")
        logger.warning("Using default configuration")
        env_config = {}

    # Load scenario
    scenario_path = Path(SageMakerPaths.INPUT_SCENARIOS) / args.scenario_name
    logger.info(f"Scenario path: {scenario_path}")

    if not scenario_path.exists():
        logger.error(f"Scenario file not found: {scenario_path}")
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

    # Create environment
    logger.info("")
    logger.info("Creating CybORG environment...")
    env = create_cyborg_environment(
        scenario_path=str(scenario_path),
        mode=args.environment_mode,
        env_config=env_config,
        n_envs=args.n_envs
    )
    logger.info("Environment created successfully")
    logger.info("")

    # Setup callbacks
    callbacks = [
        SageMakerCallback(verbose=1)
    ]

    # Add checkpoint callback
    s3_bucket = get_s3_bucket()
    checkpoint_callback = CheckpointCallback(
        checkpoint_dir=SageMakerPaths.CHECKPOINT_DIR,
        save_freq=args.checkpoint_freq,
        s3_bucket=s3_bucket,
        s3_prefix=f"checkpoints/{args.algorithm}",
        verbose=1
    )
    callbacks.append(checkpoint_callback)

    logger.info(f"Configured {len(callbacks)} training callbacks")
    logger.info("")

    # Train based on algorithm
    algorithm_trainers = {
        Algorithms.DRQN: train_drqn,
        # Add other algorithms here
        # Algorithms.DQN: train_dqn,
        # Algorithms.PPO: train_ppo,
        # Algorithms.RECURRENT_PPO: train_recurrent_ppo,
    }

    if args.algorithm not in algorithm_trainers:
        raise NotImplementedError(f"Algorithm '{args.algorithm}' not yet implemented")

    trainer = algorithm_trainers[args.algorithm]

    logger.info(f"Starting {args.algorithm.upper()} training...")
    logger.info("")

    try:
        model = trainer(
            env=env,
            args=args,
            callbacks=callbacks
        )
    except Exception as e:
        logger.error(f"Training failed with error: {e}", exc_info=True)
        raise

    # Save final model to SageMaker model directory
    model_path = Path(SageMakerPaths.MODEL_DIR) / f"{args.algorithm}.zip"
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"Saving final model to {model_path}")

    try:
        model.save(str(model_path))
        logger.info("Model saved successfully")
    except Exception as e:
        logger.error(f"Failed to save model: {e}", exc_info=True)
        raise

    # Save training metadata
    metadata = {
        'algorithm': args.algorithm,
        'environment_mode': args.environment_mode,
        'total_steps': args.total_steps,
        'scenario': args.scenario_name,
        'hyperparameters': vars(args),
        'observation_space': str(env.observation_space),
        'action_space': str(env.action_space)
    }

    # Add callback statistics if available
    for callback in callbacks:
        if isinstance(callback, SageMakerCallback):
            metadata['training_statistics'] = callback.get_statistics()
            break

    metadata_path = Path(SageMakerPaths.MODEL_DIR) / "metadata.json"
    logger.info(f"Saving metadata to {metadata_path}")

    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.info("Metadata saved successfully")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Training job completed successfully!")
    logger.info("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Training job failed: {e}", exc_info=True)
        sys.exit(1)
