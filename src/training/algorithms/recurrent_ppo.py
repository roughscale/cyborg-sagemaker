"""Recurrent PPO training implementation for SageMaker."""

import logging
from typing import List, Any
from stable_baselines3.common.utils import constant_fn
from stable_baselines3.common.callbacks import BaseCallback
from sb3_contrib.ppo_recurrent import RecurrentPPO
from sb3_contrib.ppo_recurrent.policies import MlpLstmPolicy

logger = logging.getLogger(__name__)


def train_recurrent_ppo(env, args, callbacks: List[BaseCallback]) -> Any:
    """Train Recurrent PPO agent.

    This function initializes and trains a Recurrent Proximal Policy Optimization (PPO)
    agent with LSTM for handling partial observability.

    Args:
        env: Vectorized CybORG environment
        args: Parsed arguments with hyperparameters
        callbacks: List of training callbacks

    Returns:
        Trained RecurrentPPO model

    Hyperparameters from args:
        - gamma: Discount factor
        - learning_rate: Learning rate (constant)
        - n_steps: Number of steps per rollout
        - batch_size: Minibatch size for training
        - n_epochs: Number of epochs per update
        - clip_range: PPO clip range
        - gae_lambda: GAE lambda for advantage estimation
        - normalize_advantage: Whether to normalize advantages
        - ent_coef: Entropy coefficient
        - vf_coef: Value function coefficient
        - target_kl: Target KL divergence (early stopping)
        - total_steps: Total training timesteps
        - device: Device for training ('auto', 'cuda', 'cpu')
        - seed: Random seed (optional)
    """
    logger.info("=" * 80)
    logger.info("Initializing Recurrent PPO Agent")
    logger.info("=" * 80)

    # Network architecture (input size, output size)
    input_size = env.observation_space.shape[0]
    net_arch = [input_size, input_size]  # Two hidden layers same size as input

    # Learning rate schedule (constant)
    lr_schedule = constant_fn(args.learning_rate)

    # Log configuration
    logger.info(f"Model: RecurrentPPO")
    logger.info(f"Policy: MlpLstmPolicy")
    logger.info("")
    logger.info("Hyperparameters:")
    logger.info(f"  Total Steps: {args.total_steps}")
    logger.info(f"  Input Size: {input_size}")
    logger.info(f"  Net Architecture: {net_arch}")
    logger.info(f"  Gamma: {args.gamma}")
    logger.info(f"  Learning Rate: {args.learning_rate} (constant)")
    logger.info(f"  N Steps: {args.n_steps}")
    logger.info(f"  Batch Size: {args.batch_size}")
    logger.info(f"  N Epochs: {args.n_epochs}")
    logger.info(f"  Clip Range: {args.clip_range}")
    logger.info(f"  GAE Lambda: {args.gae_lambda}")
    logger.info(f"  Normalize Advantage: {args.normalize_advantage}")
    logger.info(f"  Entropy Coefficient: {args.ent_coef}")
    logger.info(f"  Value Function Coefficient: {args.vf_coef}")
    logger.info(f"  Target KL: {args.target_kl}")
    logger.info(f"  Device: {args.device}")
    if args.seed is not None:
        logger.info(f"  Seed: {args.seed}")
    logger.info("=" * 80)
    logger.info("")

    # Create RecurrentPPO model
    logger.info("Creating Recurrent PPO model...")
    model = RecurrentPPO(
        policy=MlpLstmPolicy,
        env=env,
        learning_rate=lr_schedule,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        n_epochs=args.n_epochs,
        gamma=args.gamma,
        clip_range=args.clip_range,
        gae_lambda=args.gae_lambda,
        normalize_advantage=args.normalize_advantage,
        ent_coef=args.ent_coef,
        vf_coef=args.vf_coef,
        target_kl=args.target_kl,
        max_grad_norm=0.5,  # Gradient clipping
        tensorboard_log="/opt/ml/output/tensorboard",
        policy_kwargs={"net_arch": net_arch},
        verbose=1,
        seed=args.seed,
        device=args.device,
        _init_setup_model=True
    )

    logger.info("Recurrent PPO model created successfully")
    logger.info("")

    # Train model
    logger.info(f"Starting training for {args.total_steps} timesteps...")
    logger.info("=" * 80)

    model.learn(
        total_timesteps=args.total_steps,
        log_interval=1,  # Log to TensorBoard every episode
        callback=callbacks
    )

    logger.info("=" * 80)
    logger.info("Training complete!")
    logger.info("")

    return model


def get_recurrent_ppo_default_hyperparameters() -> dict:
    """Get default hyperparameters for Recurrent PPO.

    Returns:
        Dictionary of default hyperparameters
    """
    return {
        'gamma': 0.99,
        'learning_rate': 0.0001,
        'n_steps': 1024,
        'batch_size': 1024,
        'n_epochs': 10,
        'clip_range': 0.1,
        'gae_lambda': 1.0,
        'normalize_advantage': False,
        'ent_coef': 0.0,
        'vf_coef': 1.0,
        'target_kl': 0.01,
        'device': 'auto'
    }
