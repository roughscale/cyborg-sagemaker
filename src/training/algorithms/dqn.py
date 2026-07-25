"""DQN training implementation for SageMaker."""

import logging
from typing import List, Any
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import BaseCallback

logger = logging.getLogger(__name__)


def train_dqn(env, args, callbacks: List[BaseCallback]) -> Any:
    """Train DQN agent.

    Args:
        env: Vectorized CybORG environment
        args: Parsed arguments with hyperparameters
        callbacks: List of training callbacks

    Returns:
        Trained DQN model

    Hyperparameters from args:
        - gamma: Discount factor
        - learning_rate: Learning rate
        - batch_size: Minibatch size for training
        - buffer_size: Replay buffer size (if None, defaults to total_steps/5)
        - initial_epsilon: Initial exploration rate
        - final_epsilon: Final exploration rate
        - exploration_fraction: Fraction of training for epsilon decay
        - total_steps: Total training timesteps
        - device: Device for training ('auto', 'cuda', 'cpu')
        - seed: Random seed (optional)
    """
    logger.info("=" * 80)
    logger.info("Initializing DQN Agent")
    logger.info("=" * 80)

    buffer_size = args.buffer_size if hasattr(args, 'buffer_size') and args.buffer_size else int(args.total_steps / 5)
    learning_starts = 1000

    input_size = env.observation_space.shape[0]
    net_arch = [input_size, input_size]

    logger.info(f"Model: DQN")
    logger.info(f"Policy: MlpPolicy")
    logger.info("")
    logger.info("Hyperparameters:")
    logger.info(f"  Total Steps: {args.total_steps}")
    logger.info(f"  Input Size: {input_size}")
    logger.info(f"  Net Architecture: {net_arch}")
    logger.info(f"  Gamma: {args.gamma}")
    logger.info(f"  Learning Rate: {args.learning_rate}")
    logger.info(f"  Batch Size: {args.batch_size}")
    logger.info(f"  Buffer Size: {buffer_size}")
    logger.info(f"  Learning Starts: {learning_starts}")
    logger.info(f"  Initial Epsilon: {args.initial_epsilon}")
    logger.info(f"  Final Epsilon: {args.final_epsilon}")
    logger.info(f"  Exploration Fraction: {args.exploration_fraction}")
    logger.info(f"  Device: {args.device}")
    if args.seed is not None:
        logger.info(f"  Seed: {args.seed}")
    logger.info("=" * 80)
    logger.info("")

    model = DQN(
        policy="MlpPolicy",
        env=env,
        learning_rate=args.learning_rate,
        buffer_size=buffer_size,
        learning_starts=learning_starts,
        batch_size=args.batch_size,
        tau=1.0,
        gamma=args.gamma,
        train_freq=4,
        gradient_steps=1,
        target_update_interval=1000,
        exploration_fraction=args.exploration_fraction,
        exploration_initial_eps=args.initial_epsilon,
        exploration_final_eps=args.final_epsilon,
        max_grad_norm=10,
        tensorboard_log="/opt/ml/output/tensorboard",
        policy_kwargs={"net_arch": net_arch},
        verbose=1,
        seed=args.seed,
        device=args.device,
    )

    logger.info("DQN model created successfully")
    logger.info("")
    logger.info(f"Starting training for {args.total_steps} timesteps...")
    logger.info("=" * 80)

    model.learn(
        total_timesteps=args.total_steps,
        log_interval=1,
        callback=callbacks,
    )

    logger.info("=" * 80)
    logger.info("Training complete!")
    logger.info("")

    return model


def get_dqn_default_hyperparameters() -> dict:
    return {
        'gamma': 0.99,
        'learning_rate': 0.0001,
        'batch_size': 32,
        'buffer_size': None,
        'initial_epsilon': 1.0,
        'final_epsilon': 0.05,
        'exploration_fraction': 0.5,
        'device': 'auto',
    }
