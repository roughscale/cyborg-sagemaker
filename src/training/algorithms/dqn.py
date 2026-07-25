"""DQN training implementation for SageMaker."""

import logging
from typing import List, Any
from stable_baselines3.common.utils import constant_fn
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.prioritized_replay_buffer import PrioritizedReplayBuffer
from sb3_contrib.ddqn.ddqn import DoubleDQN
from sb3_contrib.dueling_dqn.policies import DuelingDQNPolicy

logger = logging.getLogger(__name__)


def train_dqn(env, args, callbacks: List[BaseCallback]) -> Any:
    """Train DQN agent (Double DQN with Dueling policy and Prioritized Replay).

    Args:
        env: Vectorized CybORG environment (fully observable)
        args: Parsed arguments with hyperparameters
        callbacks: List of training callbacks

    Returns:
        Trained DoubleDQN model

    Hyperparameters from args:
        - gamma: Discount factor
        - learning_rate: Learning rate (constant)
        - batch_size: Minibatch size for training
        - buffer_size: Replay buffer size (if None, defaults to total_steps/5)
        - initial_epsilon: Initial exploration rate
        - final_epsilon: Final exploration rate
        - exploration_fraction: Fraction of training for epsilon decay
        - prioritized_replay_alpha: PER alpha parameter
        - prioritized_replay_beta0: PER initial beta value
        - total_steps: Total training timesteps
        - device: Device for training ('auto', 'cuda', 'cpu')
        - seed: Random seed (optional)
    """
    logger.info("=" * 80)
    logger.info("Initializing DQN Agent")
    logger.info("=" * 80)

    buffer_size = args.buffer_size if hasattr(args, 'buffer_size') and args.buffer_size else int(args.total_steps / 5)
    learning_starts = int(args.total_steps / 100)
    target_update_interval = int(args.total_steps / 5000)

    input_size = env.observation_space.shape[0]
    net_arch = [input_size]

    lr_schedule = constant_fn(args.learning_rate)

    prioritized_replay_beta_iters = int(args.total_steps / 50)

    logger.info(f"Model: DoubleDQN")
    logger.info(f"Policy: DuelingDQNPolicy")
    logger.info("")
    logger.info("Hyperparameters:")
    logger.info(f"  Total Steps: {args.total_steps}")
    logger.info(f"  Input Size: {input_size}")
    logger.info(f"  Net Architecture: {net_arch}")
    logger.info(f"  Gamma: {args.gamma}")
    logger.info(f"  Learning Rate: {args.learning_rate} (constant)")
    logger.info(f"  Batch Size: {args.batch_size}")
    logger.info(f"  Buffer Size: {buffer_size}")
    logger.info(f"  Learning Starts: {learning_starts}")
    logger.info(f"  Target Update Interval: {target_update_interval}")
    logger.info(f"  Initial Epsilon: {args.initial_epsilon}")
    logger.info(f"  Final Epsilon: {args.final_epsilon}")
    logger.info(f"  Exploration Fraction: {args.exploration_fraction}")
    logger.info(f"  PER Alpha: {args.prioritized_replay_alpha}")
    logger.info(f"  PER Beta0: {args.prioritized_replay_beta0}")
    logger.info(f"  PER Beta Iters: {prioritized_replay_beta_iters}")
    logger.info(f"  Device: {args.device}")
    if args.seed is not None:
        logger.info(f"  Seed: {args.seed}")
    logger.info("=" * 80)
    logger.info("")

    per_buffer_args = {
        "alpha": args.prioritized_replay_alpha,
        "beta": args.prioritized_replay_beta0,
    }

    model = DoubleDQN(
        policy=DuelingDQNPolicy,
        env=env,
        learning_rate=lr_schedule,
        buffer_size=buffer_size,
        learning_starts=learning_starts,
        batch_size=args.batch_size,
        tau=1.0,
        gamma=args.gamma,
        train_freq=1,
        gradient_steps=1,
        replay_buffer_class=PrioritizedReplayBuffer,
        replay_buffer_kwargs=per_buffer_args,
        optimize_memory_usage=False,
        target_update_interval=target_update_interval,
        exploration_fraction=args.exploration_fraction,
        exploration_initial_eps=args.initial_epsilon,
        exploration_final_eps=args.final_epsilon,
        max_grad_norm=10,
        tensorboard_log="/opt/ml/output/tensorboard",
        policy_kwargs={"net_arch": net_arch},
        verbose=1,
        seed=args.seed,
        device=args.device,
        _init_setup_model=True,
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
        'final_epsilon': 0.02,
        'exploration_fraction': 0.9,
        'prioritized_replay_alpha': 0.9,
        'prioritized_replay_beta0': 0.4,
        'device': 'auto',
    }
