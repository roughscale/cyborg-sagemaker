"""DRQN training implementation for SageMaker."""

import logging
from typing import List, Any
from stable_baselines3.common.utils import constant_fn
from stable_baselines3.common.callbacks import BaseCallback
from sb3_contrib.drqn.drqn import DeepRecurrentQNetwork, DoubleDRQN
from sb3_contrib.drqn.policies import DRQNPolicy
from sb3_contrib.drqn.dueling_policies import DuelingDRQNPolicy
from sb3_contrib.per.prioritized_replay_sequence_buffer import PrioritizedReplaySequenceBuffer

logger = logging.getLogger(__name__)


def train_drqn(env, args, callbacks: List[BaseCallback]) -> Any:
    """Train DRQN agent.

    This function initializes and trains a Deep Recurrent Q-Network (DRQN) agent
    with optional Double DQN and Dueling DQN enhancements.

    Args:
        env: Vectorized CybORG environment
        args: Parsed arguments with hyperparameters
        callbacks: List of training callbacks

    Returns:
        Trained DRQN model

    Hyperparameters from args:
        - gamma: Discount factor
        - learning_rate: Learning rate (constant)
        - batch_size: Minibatch size for training
        - num_prev_seq: Number of previous transitions in sequence
        - double: Use Double DQN algorithm
        - dueling: Use Dueling DQN architecture
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
    logger.info("Initializing DRQN Agent")
    logger.info("=" * 80)

    # Determine buffer size
    buffer_size = args.buffer_size if hasattr(args, 'buffer_size') and args.buffer_size else int(args.total_steps / 5)

    # Learning starts (when to start training after collecting initial experience)
    learning_starts = 30000  # Match existing implementation

    # Target network update frequency
    target_update_interval = 1000  # Match existing implementation

    # Network architecture (input size, output size)
    input_size = env.observation_space.shape[0]
    net_arch = [input_size, input_size]  # Two hidden layers same size as input

    # Learning rate schedule (constant)
    lr_schedule = constant_fn(args.learning_rate)

    # PER beta schedule
    prioritized_replay_beta_iters = int(args.total_steps / 50)

    # Select model and policy based on double and dueling parameters
    if args.double and args.dueling:
        ModelClass = DoubleDRQN
        PolicyClass = DuelingDRQNPolicy
    elif args.double and not args.dueling:
        ModelClass = DoubleDRQN
        PolicyClass = DRQNPolicy
    elif not args.double and args.dueling:
        ModelClass = DeepRecurrentQNetwork
        PolicyClass = DuelingDRQNPolicy
    else:
        ModelClass = DeepRecurrentQNetwork
        PolicyClass = DRQNPolicy

    # Log configuration
    logger.info(f"Model: {ModelClass.__name__}")
    logger.info(f"Policy: {PolicyClass.__name__}")
    logger.info(f"Double DQN: {args.double}")
    logger.info(f"Dueling DQN: {args.dueling}")
    logger.info("")
    logger.info("Hyperparameters:")
    logger.info(f"  Total Steps: {args.total_steps}")
    logger.info(f"  Input Size: {input_size}")
    logger.info(f"  Net Architecture: {net_arch}")
    logger.info(f"  Gamma: {args.gamma}")
    logger.info(f"  Learning Rate: {args.learning_rate} (constant)")
    logger.info(f"  Batch Size: {args.batch_size}")
    logger.info(f"  Num Prev Seq: {args.num_prev_seq}")
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

    # PER buffer arguments
    per_buffer_args = {
        "alpha": args.prioritized_replay_alpha,
        "beta": args.prioritized_replay_beta0,
        "lstm_num_layers": len(net_arch)
    }

    # Create DRQN model
    logger.info("Creating DRQN model...")
    model = ModelClass(
        policy=PolicyClass,
        env=env,
        learning_rate=lr_schedule,
        buffer_size=buffer_size,
        learning_starts=learning_starts,
        batch_size=args.batch_size,
        n_prev_seq=args.num_prev_seq,
        tau=1.0,  # Hard update for target network
        gamma=args.gamma,
        train_freq=1,  # Train after every step
        gradient_steps=1,  # One gradient step per training
        replay_buffer_class=PrioritizedReplaySequenceBuffer,
        replay_buffer_kwargs=per_buffer_args,
        optimize_memory_usage=False,
        target_update_interval=target_update_interval,
        exploration_fraction=args.exploration_fraction,
        exploration_initial_eps=args.initial_epsilon,
        exploration_final_eps=args.final_epsilon,
        max_grad_norm=10,  # Gradient clipping
        tensorboard_log="/opt/ml/output/tensorboard",
        policy_kwargs={"net_arch": net_arch},
        verbose=1,
        seed=args.seed,
        device=args.device,
        _init_setup_model=True
    )

    logger.info("DRQN model created successfully")
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


def get_drqn_default_hyperparameters() -> dict:
    """Get default hyperparameters for DRQN.

    Returns:
        Dictionary of default hyperparameters
    """
    return {
        'gamma': 0.99,
        'learning_rate': 0.0001,
        'batch_size': 32,
        'num_prev_seq': 20,
        'double': True,
        'dueling': True,
        'buffer_size': None,  # Will be calculated as total_steps/5
        'initial_epsilon': 1.0,
        'final_epsilon': 0.02,
        'exploration_fraction': 0.9,
        'prioritized_replay_alpha': 0.9,
        'prioritized_replay_beta0': 0.4,
        'device': 'auto'
    }
