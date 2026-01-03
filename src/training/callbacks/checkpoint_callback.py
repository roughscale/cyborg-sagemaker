"""Checkpoint callback with S3 sync for model checkpointing."""

import os
import logging
from pathlib import Path
from typing import Optional
from stable_baselines3.common.callbacks import BaseCallback

logger = logging.getLogger(__name__)


class CheckpointCallback(BaseCallback):
    """Save model checkpoints at specified intervals and optionally sync to S3.

    SageMaker automatically syncs /opt/ml/checkpoints to S3, but this callback
    provides additional control and immediate syncing if needed.

    Args:
        checkpoint_dir: Directory to save checkpoints
        save_freq: Save checkpoint every N steps
        s3_bucket: S3 bucket for immediate upload (optional)
        s3_prefix: S3 prefix for checkpoints (optional)
        name_prefix: Prefix for checkpoint filenames (default: "checkpoint")
        verbose: Verbosity level
    """

    def __init__(
        self,
        checkpoint_dir: str,
        save_freq: int,
        s3_bucket: Optional[str] = None,
        s3_prefix: Optional[str] = None,
        name_prefix: str = "checkpoint",
        verbose: int = 0
    ):
        super().__init__(verbose)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.save_freq = save_freq
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.name_prefix = name_prefix
        self.checkpoints_saved = 0

        # Initialize S3 client if bucket provided
        self.s3_client = None
        if s3_bucket:
            try:
                import boto3
                self.s3_client = boto3.client('s3')
                logger.info(f"S3 sync enabled to s3://{s3_bucket}/{s3_prefix or ''}")
            except ImportError:
                logger.warning("boto3 not available, S3 sync disabled")
                self.s3_client = None

        logger.info(f"Checkpoint callback initialized")
        logger.info(f"  Directory: {self.checkpoint_dir}")
        logger.info(f"  Save frequency: every {self.save_freq} steps")

    def _on_step(self) -> bool:
        """Save checkpoint every save_freq steps.

        Returns:
            True to continue training
        """
        if self.n_calls % self.save_freq == 0:
            checkpoint_path = self._get_checkpoint_path()

            logger.info(f"Saving checkpoint at step {self.num_timesteps}")
            logger.info(f"  Path: {checkpoint_path}")

            # Save model
            self.model.save(str(checkpoint_path))
            self.checkpoints_saved += 1

            # Sync to S3 if configured
            if self.s3_client and self.s3_bucket:
                self._upload_to_s3(checkpoint_path)

            if self.verbose >= 1:
                logger.info(f"Checkpoint {self.checkpoints_saved} saved successfully")

        return True

    def _get_checkpoint_path(self) -> Path:
        """Generate checkpoint file path.

        Returns:
            Path object for checkpoint file
        """
        filename = f"{self.name_prefix}_{self.num_timesteps}.zip"
        return self.checkpoint_dir / filename

    def _upload_to_s3(self, checkpoint_path: Path) -> bool:
        """Upload checkpoint to S3.

        Args:
            checkpoint_path: Local path to checkpoint file

        Returns:
            True if upload succeeded, False otherwise
        """
        if not self.s3_client or not self.s3_bucket:
            return False

        try:
            # Construct S3 key
            s3_key = str(checkpoint_path.name)
            if self.s3_prefix:
                s3_key = f"{self.s3_prefix.rstrip('/')}/{s3_key}"

            logger.info(f"Uploading checkpoint to s3://{self.s3_bucket}/{s3_key}")

            self.s3_client.upload_file(
                str(checkpoint_path),
                self.s3_bucket,
                s3_key
            )

            logger.info(f"Successfully uploaded to S3")
            return True

        except Exception as e:
            logger.error(f"Failed to upload checkpoint to S3: {e}")
            return False

    def _on_training_end(self) -> bool:
        """Save final checkpoint at end of training.

        Returns:
            True to continue
        """
        # Save final checkpoint
        final_checkpoint_path = self.checkpoint_dir / f"{self.name_prefix}_final.zip"

        logger.info("Saving final checkpoint")
        logger.info(f"  Path: {final_checkpoint_path}")

        self.model.save(str(final_checkpoint_path))

        # Sync to S3 if configured
        if self.s3_client and self.s3_bucket:
            self._upload_to_s3(final_checkpoint_path)

        logger.info(f"Total checkpoints saved: {self.checkpoints_saved + 1}")

        return True


class LatestCheckpointCallback(BaseCallback):
    """Keep only the latest N checkpoints to save disk space.

    This callback automatically removes old checkpoints, keeping only
    the most recent N checkpoints.

    Args:
        checkpoint_dir: Directory containing checkpoints
        keep_last_n: Number of checkpoints to keep
        verbose: Verbosity level
    """

    def __init__(
        self,
        checkpoint_dir: str,
        keep_last_n: int = 5,
        verbose: int = 0
    ):
        super().__init__(verbose)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.keep_last_n = keep_last_n
        logger.info(f"LatestCheckpointCallback initialized (keep last {keep_last_n})")

    def _on_step(self) -> bool:
        """Clean up old checkpoints.

        Returns:
            True to continue training
        """
        # Only run cleanup periodically (e.g., every 100 calls)
        if self.n_calls % 100 == 0:
            self._cleanup_old_checkpoints()

        return True

    def _cleanup_old_checkpoints(self) -> None:
        """Remove old checkpoints, keeping only the latest N."""
        if not self.checkpoint_dir.exists():
            return

        # Find all checkpoint files
        checkpoints = sorted(
            self.checkpoint_dir.glob("checkpoint_*.zip"),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # Newest first
        )

        # Remove old checkpoints
        for checkpoint in checkpoints[self.keep_last_n:]:
            try:
                checkpoint.unlink()
                if self.verbose >= 2:
                    logger.debug(f"Removed old checkpoint: {checkpoint.name}")
            except Exception as e:
                logger.warning(f"Failed to remove checkpoint {checkpoint}: {e}")
