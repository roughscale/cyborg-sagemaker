"""PPO training implementation for SageMaker."""

import logging
from typing import List, Any
from stable_baselines3 import PPO
from stable_baselines3.ppo.policies import MlpPolicy
from stable_baselines3.common.utils import constant_fn
from stable_baselines3.common.callbacks import BaseCallback

logger = logging.getLogger(__name__)


def train_ppo(env, args, callbacks: List[BaseCallback]) -> Any:
    """Train PPO agent.

    Uses ObsHistoryWrapper (via env_factory) to accumulate partial observations
    into a full belief state.

    Args:
        env: Vectorized CybORG environment (wrapped with ObsHistoryWrapper)
        args: Parsed arguments with hyperparameters
        callbacks: List of training callbacks

    Returns:
        Trained PPO model

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
    logger.info("Initializing PPO Agent")
    logger.info("=" * 80)

    input_size = env.observation_space.shape[0]
    net_arch = [input_size, input_size]

    lr_schedule = constant_fn(args.learning_rate)

    logger.info(f"Model: PPO")
    logger.info(f"Policy: MlpPolicy")
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

    resume_checkpoint = getattr(args, 'resume_checkpoint_path', None)
    completed_timesteps = getattr(args, 'completed_timesteps', 0)
    remaining_steps = args.total_steps - completed_timesteps

    if resume_checkpoint:
        logger.info(f"Resuming from checkpoint: {resume_checkpoint}")
        model = PPO.load(
            resume_checkpoint,
            env=env,
            device=args.device,
            verbose=1,
        )
        model.tensorboard_log = "/opt/ml/output/tensorboard"
    else:
        logger.info("Creating PPO model...")
        model = PPO(
            policy=MlpPolicy,
            env=env,
            learning_rate=lr_schedule,
            n_steps=args.n_steps,
            batch_size=args.batch_size,
            n_epochs=args.n_epochs,
            gamma=args.gamma,
            gae_lambda=args.gae_lambda,
            clip_range=args.clip_range,
            normalize_advantage=args.normalize_advantage,
            ent_coef=args.ent_coef,
            vf_coef=args.vf_coef,
            max_grad_norm=0.5,
            target_kl=args.target_kl,
            tensorboard_log="/opt/ml/output/tensorboard",
            policy_kwargs={"net_arch": net_arch},
            verbose=1,
            seed=args.seed,
            device=args.device,
            _init_setup_model=True,
        )

    logger.info("PPO model ready")
    logger.info("")
    logger.info(f"Starting training for {remaining_steps} timesteps (completed: {completed_timesteps})...")
    logger.info("=" * 80)

    model.learn(
        total_timesteps=remaining_steps,
        log_interval=1,
        callback=callbacks,
    )

    logger.info("=" * 80)
    logger.info("Training complete!")
    logger.info("")

    return model


def get_ppo_default_hyperparameters() -> dict:
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
        'device': 'auto',
    }
