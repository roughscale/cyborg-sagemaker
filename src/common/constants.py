"""SageMaker path constants and configuration."""

import os


class SageMakerPaths:
    """Standard SageMaker paths."""

    # Input data paths
    INPUT_DATA = "/opt/ml/input/data"
    INPUT_CONFIG = "/opt/ml/input/data/config"
    INPUT_SCENARIOS = "/opt/ml/input/data/scenarios"

    # Output paths
    MODEL_DIR = "/opt/ml/model"
    OUTPUT_DATA_DIR = "/opt/ml/output/data"
    CHECKPOINT_DIR = "/opt/ml/checkpoints"
    TENSORBOARD_DIR = "/opt/ml/output/tensorboard"

    # Processing job paths
    PROCESSING_INPUT = "/opt/ml/processing"
    PROCESSING_MODEL = "/opt/ml/processing/model"
    PROCESSING_CONFIG = "/opt/ml/processing/config"
    PROCESSING_SCENARIOS = "/opt/ml/processing/scenarios"
    PROCESSING_EMULATION = "/opt/ml/processing/emulation"
    PROCESSING_OUTPUT = "/opt/ml/processing/output"

    # Code path
    CODE_DIR = "/opt/ml/code"


class EnvironmentConfig:
    """Environment variable keys."""

    # AWS
    AWS_REGION = "AWS_REGION"
    AWS_ACCOUNT_ID = "AWS_ACCOUNT_ID"
    S3_BUCKET = "S3_BUCKET"

    # SageMaker
    SM_MODEL_DIR = "SM_MODEL_DIR"
    SM_OUTPUT_DATA_DIR = "SM_OUTPUT_DATA_DIR"
    SM_CHANNEL_CONFIG = "SM_CHANNEL_CONFIG"
    SM_CHANNEL_SCENARIOS = "SM_CHANNEL_SCENARIOS"
    SM_HPS = "SM_HPS"

    # Training
    ALGORITHM = "ALGORITHM"
    ENVIRONMENT_MODE = "ENVIRONMENT_MODE"
    TOTAL_STEPS = "TOTAL_STEPS"

    # Evaluation
    N_EVAL_EPISODES = "N_EVAL_EPISODES"
    SCENARIO_NAME = "SCENARIO_NAME"
    DETERMINISTIC = "DETERMINISTIC"


class Algorithms:
    """Supported algorithms."""

    DRQN = "drqn"
    DQN = "dqn"
    PPO = "ppo"
    RECURRENT_PPO = "recurrent_ppo"

    ALL = [DRQN, DQN, PPO, RECURRENT_PPO]


class EnvironmentModes:
    """Environment modes."""

    SIMULATION = "sim"
    AWS_EMULATION = "aws"

    ALL = [SIMULATION, AWS_EMULATION]


def get_env(key: str, default: str = None) -> str:
    """Get environment variable with optional default.

    Args:
        key: Environment variable key
        default: Default value if not found

    Returns:
        Environment variable value or default
    """
    return os.environ.get(key, default)


def is_sagemaker_training() -> bool:
    """Check if running in SageMaker training environment.

    Returns:
        True if in SageMaker training environment
    """
    return os.path.exists(SageMakerPaths.MODEL_DIR)


def is_sagemaker_processing() -> bool:
    """Check if running in SageMaker processing environment.

    Returns:
        True if in SageMaker processing environment
    """
    return os.path.exists(SageMakerPaths.PROCESSING_OUTPUT)
