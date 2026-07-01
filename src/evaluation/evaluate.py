#!/usr/bin/env python3
"""
SageMaker Processing Job entry point for CybORG RL evaluation.

Environment variables (set by launch_evaluation.py):
- ALGORITHM:          Algorithm name (drqn, recurrent_ppo, dqn, ppo)
- SCENARIO_NAME:      Scenario YAML filename
- N_EVAL_EPISODES:    Number of evaluation episodes (default: 100)
- DETERMINISTIC:      Use deterministic policy (default: true)
- ENVIRONMENT_MODE:   sim or aws (default: sim)
- DEVICE:             Torch device for inference (default: auto)
"""

import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, '/opt/ml/code')

from common.constants import SageMakerPaths, Algorithms, EnvironmentModes
from common.logging_config import setup_logging, get_logger
from training.utils.env_factory import create_cyborg_environment
from training.utils.config_loader import load_algorithm_config, extract_env_config
from evaluation.utils.model_loader import extract_model_archive, load_model
from evaluation.utils.metrics import compute_metrics, save_metrics, print_metrics

setup_logging()
logger = get_logger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description='CybORG SageMaker Evaluation')

    parser.add_argument('--algorithm', type=str,
                        default=os.getenv('ALGORITHM'),
                        choices=Algorithms.ALL)
    parser.add_argument('--scenario_name', type=str,
                        default=os.getenv('SCENARIO_NAME'))
    parser.add_argument('--n_eval_episodes', type=int,
                        default=int(os.getenv('N_EVAL_EPISODES', '100')))
    parser.add_argument('--deterministic',
                        type=lambda x: x.lower() != 'false',
                        default=os.getenv('DETERMINISTIC', 'true').lower() != 'false')
    parser.add_argument('--environment_mode', type=str,
                        default=os.getenv('ENVIRONMENT_MODE', 'sim'),
                        choices=EnvironmentModes.ALL)
    parser.add_argument('--device', type=str,
                        default=os.getenv('DEVICE', 'auto'),
                        choices=['auto', 'cuda', 'cpu'])

    args, _ = parser.parse_known_args()

    if not args.algorithm:
        raise ValueError("ALGORITHM must be set via --algorithm or the ALGORITHM env var")
    if not args.scenario_name:
        raise ValueError("SCENARIO_NAME must be set via --scenario_name or the SCENARIO_NAME env var")

    return args


def main():
    args = parse_args()

    logger.info("=" * 80)
    logger.info("CybORG SageMaker Evaluation Job")
    logger.info("=" * 80)
    logger.info(f"Algorithm:    {args.algorithm}")
    logger.info(f"Mode:         {args.environment_mode}")
    logger.info(f"Scenario:     {args.scenario_name}")
    logger.info(f"Episodes:     {args.n_eval_episodes}")
    logger.info(f"Deterministic:{args.deterministic}")
    logger.info(f"Device:       {args.device}")
    logger.info("=" * 80)

    # Load environment config from processing input channel
    config_path = Path(SageMakerPaths.PROCESSING_CONFIG) / f"{args.algorithm}.yaml"
    if config_path.exists():
        config = load_algorithm_config(str(config_path))
        env_config = extract_env_config(config)
        logger.info(f"Loaded env config from {config_path}")
    else:
        logger.warning(f"Config not found at {config_path}, using defaults")
        env_config = {}

    # Locate scenario file
    scenario_path = Path(SageMakerPaths.PROCESSING_SCENARIOS) / args.scenario_name
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario not found: {scenario_path}")

    # Extract model archive if SageMaker packaged it as model.tar.gz
    model_dir = SageMakerPaths.PROCESSING_MODEL
    extract_model_archive(model_dir)

    # Create environment
    logger.info("Creating CybORG environment...")
    env = create_cyborg_environment(
        scenario_path=str(scenario_path),
        mode=args.environment_mode,
        env_config=env_config,
        n_envs=1,
    )

    # Load model — SB3 appends .zip automatically if omitted
    model_path = Path(model_dir) / args.algorithm
    model = load_model(
        algorithm=args.algorithm,
        model_path=str(model_path),
        env=env,
        device=args.device,
    )

    # Run evaluation
    if args.environment_mode == EnvironmentModes.AWS_EMULATION:
        from evaluation.evaluators.aws_evaluator import evaluate
    else:
        from evaluation.evaluators.sim_evaluator import evaluate

    raw = evaluate(
        model=model,
        env=env,
        n_episodes=args.n_eval_episodes,
        deterministic=args.deterministic,
    )

    # Compute, emit, and persist metrics
    metrics = compute_metrics(raw['episode_rewards'], raw['episode_lengths'])
    metrics.update({
        'algorithm': args.algorithm,
        'scenario': args.scenario_name,
        'environment_mode': args.environment_mode,
        'deterministic': args.deterministic,
        'elapsed_seconds': raw['elapsed_seconds'],
    })

    print_metrics(metrics)
    save_metrics(metrics, SageMakerPaths.PROCESSING_OUTPUT)

    logger.info("=" * 80)
    logger.info("Evaluation complete!")
    logger.info(f"Mean reward: {metrics['mean_reward']:.4f} ± {metrics['std_reward']:.4f}")
    logger.info(f"Results: {SageMakerPaths.PROCESSING_OUTPUT}/results.json")
    logger.info("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        sys.exit(1)
