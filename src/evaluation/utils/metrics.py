"""Metrics computation and persistence for evaluation results."""

import json
import logging
import statistics
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def compute_metrics(rewards: List[float], lengths: List[int]) -> Dict[str, Any]:
    """Compute summary statistics from per-episode rewards and lengths."""
    n = len(rewards)
    return {
        'n_episodes': n,
        'mean_reward': statistics.mean(rewards),
        'std_reward': statistics.stdev(rewards) if n > 1 else 0.0,
        'min_reward': min(rewards),
        'max_reward': max(rewards),
        'mean_length': statistics.mean(lengths),
        'std_length': statistics.stdev(lengths) if n > 1 else 0.0,
        'episode_rewards': rewards,
        'episode_lengths': lengths,
    }


def save_metrics(metrics: Dict[str, Any], output_dir: str, filename: str = 'results.json') -> str:
    """Save metrics dict to a JSON file."""
    output_path = Path(output_dir) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    logger.info(f"Results saved to: {output_path}")
    return str(output_path)


def print_metrics(metrics: Dict[str, Any]) -> None:
    """Emit metrics in CloudWatch-parseable format (key: value)."""
    print(f"eval_mean_reward: {metrics['mean_reward']:.4f}")
    print(f"eval_std_reward: {metrics['std_reward']:.4f}")
    print(f"eval_min_reward: {metrics['min_reward']:.4f}")
    print(f"eval_max_reward: {metrics['max_reward']:.4f}")
    print(f"eval_mean_length: {metrics['mean_length']:.1f}")
    print(f"eval_n_episodes: {metrics['n_episodes']}")
