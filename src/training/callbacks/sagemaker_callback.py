"""SageMaker callback for CloudWatch metrics emission."""

import logging
from typing import Dict, Any
from stable_baselines3.common.callbacks import BaseCallback

logger = logging.getLogger(__name__)


class SageMakerCallback(BaseCallback):
    """Callback for SageMaker-specific functionality.

    This callback:
    - Emits metrics in CloudWatch-parseable format via print statements
    - Tracks episode statistics (rewards, lengths)
    - Monitors training progress
    - Handles graceful shutdown

    SageMaker parses stdout for metrics using regex patterns defined in
    the Terraform training job configuration.

    Example metric output format:
        episode_reward: 45.2
        episode_length: 125
        exploration_rate: 0.523
    """

    def __init__(self, verbose: int = 0):
        """Initialize SageMaker callback.

        Args:
            verbose: Verbosity level (0=none, 1=info, 2=debug)
        """
        super().__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []
        self.episode_count = 0

    def _on_training_start(self) -> bool:
        """Called before the first rollout.

        Returns:
            True to continue training
        """
        logger.info("SageMaker training callback initialized")
        logger.info(f"Total timesteps: {self.num_timesteps}")

        return True

    def _on_step(self) -> bool:
        """Called after each environment step.

        Emits metrics in format parseable by SageMaker metric regex.

        Returns:
            True to continue training, False to stop
        """
        # Check if episode finished
        dones = self.locals.get("dones", [False])
        if any(dones):
            # Get episode statistics from info dict
            infos = self.locals.get("infos", [{}])

            for i, (done, info) in enumerate(zip(dones, infos)):
                if done and "episode" in info:
                    ep_info = info["episode"]
                    reward = ep_info['r']
                    length = ep_info['l']

                    # Store statistics
                    self.episode_rewards.append(reward)
                    self.episode_lengths.append(length)
                    self.episode_count += 1

                    # Emit metrics for CloudWatch (parsed by regex in Terraform)
                    print(f"episode_reward: {reward}")
                    print(f"episode_length: {length}")
                    print(f"episode_number: {self.episode_count}")
                    print(f"total_timesteps: {self.num_timesteps}")

                    # Emit algorithm-specific metrics at end of episode only
                    self._emit_algorithm_metrics()

                    if self.verbose >= 1:
                        logger.info(
                            f"Episode {self.episode_count}: "
                            f"reward={reward:.2f}, length={length}"
                        )

        # Log progress periodically
        if self.num_timesteps % 10000 == 0 and self.verbose >= 1:
            self._log_progress()

        return True

    def _emit_algorithm_metrics(self) -> None:
        """Emit algorithm-specific metrics.

        Different algorithms have different metrics to track:
        - DQN/DRQN: exploration_rate, loss, mean_q_value, per_beta
        - PPO: policy_loss, value_loss, entropy_loss, approx_kl, clip_fraction

        These metrics are emitted to CloudWatch for tracking in SageMaker console.
        """
        # Exploration rate (for DQN/DRQN)
        if hasattr(self.model, 'exploration_rate'):
            print(f"exploration_rate: {self.model.exploration_rate}")

        # Training loss (from logger if available)
        if hasattr(self, 'logger') and self.logger is not None:
            name_to_value = getattr(self.logger, 'name_to_value', {})

            # DQN/DRQN metrics
            if 'train/loss' in name_to_value:
                print(f"loss: {name_to_value['train/loss']}")

            # PPO metrics
            if 'train/policy_loss' in name_to_value:
                print(f"policy_loss: {name_to_value['train/policy_loss']}")
            if 'train/value_loss' in name_to_value:
                print(f"value_loss: {name_to_value['train/value_loss']}")
            if 'train/entropy_loss' in name_to_value:
                print(f"entropy_loss: {name_to_value['train/entropy_loss']}")
            if 'train/approx_kl' in name_to_value:
                print(f"approx_kl: {name_to_value['train/approx_kl']}")
            if 'train/clip_fraction' in name_to_value:
                print(f"clip_fraction: {name_to_value['train/clip_fraction']}")

            # PER beta (for DRQN with prioritized replay)
            if 'replay_buffer/prioritized_replay_beta' in name_to_value:
                print(f"per_beta: {name_to_value['replay_buffer/prioritized_replay_beta']}")

    def _log_progress(self) -> None:
        """Log training progress."""
        if self.episode_rewards:
            recent_rewards = self.episode_rewards[-100:]  # Last 100 episodes
            mean_reward = sum(recent_rewards) / len(recent_rewards)
            logger.info(
                f"Step {self.num_timesteps}: "
                f"Episodes={self.episode_count}, "
                f"Mean Reward (last 100)={mean_reward:.2f}"
            )

    def _on_training_end(self) -> bool:
        """Called at the end of training.

        Returns:
            True to continue
        """
        if self.episode_rewards:
            logger.info("=" * 80)
            logger.info("Training Complete - Episode Statistics")
            logger.info("=" * 80)
            logger.info(f"Total Episodes: {self.episode_count}")
            logger.info(f"Total Timesteps: {self.num_timesteps}")

            mean_reward = sum(self.episode_rewards) / len(self.episode_rewards)
            mean_length = sum(self.episode_lengths) / len(self.episode_lengths)

            logger.info(f"Mean Episode Reward: {mean_reward:.2f}")
            logger.info(f"Mean Episode Length: {mean_length:.2f}")
            logger.info(f"Min Episode Reward: {min(self.episode_rewards):.2f}")
            logger.info(f"Max Episode Reward: {max(self.episode_rewards):.2f}")
            logger.info("=" * 80)

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get training statistics.

        Returns:
            Dictionary with episode statistics
        """
        if not self.episode_rewards:
            return {}

        return {
            'episode_count': self.episode_count,
            'total_timesteps': self.num_timesteps,
            'mean_reward': sum(self.episode_rewards) / len(self.episode_rewards),
            'mean_length': sum(self.episode_lengths) / len(self.episode_lengths),
            'min_reward': min(self.episode_rewards),
            'max_reward': max(self.episode_rewards),
            'all_rewards': self.episode_rewards,
            'all_lengths': self.episode_lengths
        }
