"""Simulation mode evaluator using SB3 evaluate_policy."""

import logging
import time
from typing import Any, Dict

from stable_baselines3.common.evaluation import evaluate_policy

logger = logging.getLogger(__name__)


def evaluate(model: Any, env, n_episodes: int, deterministic: bool = True) -> Dict[str, Any]:
    """Evaluate a model in CybORG simulation mode.

    Args:
        model: Loaded SB3 model (supports recurrent and non-recurrent policies)
        env: Vectorized CybORG environment (sim mode)
        n_episodes: Number of evaluation episodes
        deterministic: Use deterministic policy actions

    Returns:
        Dict with episode_rewards, episode_lengths, elapsed_seconds, mode
    """
    logger.info("=" * 80)
    logger.info(f"Simulation evaluation: {n_episodes} episodes, deterministic={deterministic}")
    logger.info("=" * 80)

    start = time.time()

    rewards, lengths = evaluate_policy(
        model,
        env,
        n_eval_episodes=n_episodes,
        deterministic=deterministic,
        return_episode_rewards=True,
    )

    elapsed = time.time() - start
    logger.info(f"Evaluation complete in {elapsed:.1f}s")

    return {
        'episode_rewards': list(rewards),
        'episode_lengths': list(lengths),
        'elapsed_seconds': elapsed,
        'mode': 'sim',
    }
