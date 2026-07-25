"""Model loader for CybORG RL evaluation."""

import importlib
import logging
import tarfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Maps algorithm name → (module, class) for SB3 load()
_ALGORITHM_CLASSES = {
    'drqn': ('sb3_contrib.drqn.drqn', 'DoubleDRQN'),
    'dqn': ('sb3_contrib.ddqn.ddqn', 'DoubleDQN'),
    'recurrent_ppo': ('sb3_contrib.ppo_recurrent', 'RecurrentPPO'),
    'ppo': ('stable_baselines3', 'PPO'),
}


def extract_model_archive(model_dir: str) -> None:
    """Extract model.tar.gz if present (SageMaker training output format)."""
    tarball = Path(model_dir) / 'model.tar.gz'
    if tarball.exists():
        logger.info(f"Extracting {tarball}")
        with tarfile.open(tarball) as tf:
            tf.extractall(model_dir)
        logger.info("Extraction complete")


def load_model(algorithm: str, model_path: str, env=None, device: str = 'auto') -> Any:
    """Load a trained SB3 model by algorithm name.

    Args:
        algorithm: Algorithm name (drqn, recurrent_ppo, dqn, ppo)
        model_path: Path to model file (without .zip extension)
        env: Environment to bind to the model (sets obs/action space)
        device: Torch device ('auto', 'cuda', 'cpu')

    Returns:
        Loaded SB3 model
    """
    if algorithm not in _ALGORITHM_CLASSES:
        raise ValueError(
            f"Unknown algorithm '{algorithm}'. Supported: {list(_ALGORITHM_CLASSES)}"
        )

    module_name, class_name = _ALGORITHM_CLASSES[algorithm]
    module = importlib.import_module(module_name)
    ModelClass = getattr(module, class_name)

    logger.info(f"Loading {class_name} from: {model_path}")
    model = ModelClass.load(model_path, env=env, device=device)
    logger.info("Model loaded successfully")

    return model
