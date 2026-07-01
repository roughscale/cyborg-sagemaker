"""AWS emulation mode evaluator using Metasploit via CybORG."""

import logging
import time
from typing import Any, Dict

from stable_baselines3.common.evaluation import evaluate_policy

logger = logging.getLogger(__name__)


def evaluate(model: Any, env, n_episodes: int, deterministic: bool = True) -> Dict[str, Any]:
    """Evaluate a model in CybORG AWS emulation mode.

    Requires Metasploit RPC daemon (msfrpcd) to be running in the container
    and accessible to CybORG. The AWS emulation environment manages the
    Metasploit connection internally via pymetasploit3.

    Args:
        model: Loaded SB3 model
        env: Vectorized CybORG environment (aws mode, with Metasploit)
        n_episodes: Number of evaluation episodes
        deterministic: Use deterministic policy actions

    Returns:
        Dict with episode_rewards, episode_lengths, elapsed_seconds, mode
    """
    logger.info("=" * 80)
    logger.info(f"AWS emulation evaluation: {n_episodes} episodes, deterministic={deterministic}")
    logger.warning("Ensure msfrpcd is running and reachable before evaluation")
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
        'mode': 'aws',
    }
