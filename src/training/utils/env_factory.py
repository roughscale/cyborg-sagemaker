"""Environment factory for creating CybORG environments with wrappers."""

import sys
import logging
from typing import Dict, Any
from pathlib import Path

# Add CybORG to path if running in SageMaker
sys.path.insert(0, '/opt/ml/code')

from CybORG import CybORG
from CybORG.Agents.Wrappers.EnumActionWrapper import EnumActionWrapper
from CybORG.Agents.Wrappers.FixedFlatWrapper import FixedFlatWrapper
from CybORG.Agents.Wrappers.OpenAIGymWrapper import OpenAIGymWrapper
from stable_baselines3.common.env_util import make_vec_env

logger = logging.getLogger(__name__)


def create_cyborg_environment(
    scenario_path: str,
    mode: str = 'sim',
    env_config: Dict[str, Any] = None,
    n_envs: int = 1,
    agent_name: str = "Red"
):
    """Create a vectorized CybORG environment with standard wrappers.

    This function creates a CybORG environment and applies the standard wrapper
    chain used for RL training:
    1. EnumActionWrapper - Converts action space to discrete integers
    2. FixedFlatWrapper - Flattens observations to fixed-size vectors
    3. OpenAIGymWrapper - Makes environment Gym/Gymnasium compatible
    4. VecEnv - Vectorizes for parallel training

    Args:
        scenario_path: Path to scenario YAML file
        mode: Environment mode ('sim' or 'aws')
        env_config: Environment configuration dict with 'fully_obs', 'max_params', etc.
        n_envs: Number of parallel environments
        agent_name: Name of agent to control (typically "Red")

    Returns:
        Vectorized environment ready for SB3 training

    Example:
        >>> env = create_cyborg_environment(
        ...     scenario_path="/opt/ml/input/data/scenarios/drqn_scenario.yaml",
        ...     mode='sim',
        ...     env_config={
        ...         "fully_obs": False,
        ...         "max_params": {
        ...             "MAX_HOSTS": 5,
        ...             "MAX_PROCESSES": 2,
        ...             ...
        ...         }
        ...     },
        ...     n_envs=1
        ... )
    """
    if env_config is None:
        env_config = _get_default_env_config()

    logger.info(f"Creating CybORG environment from scenario: {scenario_path}")
    logger.info(f"Mode: {mode}")
    logger.info(f"Number of parallel environments: {n_envs}")
    logger.info(f"Agent: {agent_name}")
    logger.info(f"Fully observable: {env_config.get('fully_obs', False)}")

    # Verify scenario file exists
    scenario_file = Path(scenario_path)
    if not scenario_file.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

    def _make_env():
        """Create a single CybORG environment with wrappers."""
        # Create base CybORG environment
        cyborg = CybORG(scenario_path, mode, env_config=env_config)

        # Apply wrapper chain
        # 1. EnumActionWrapper: Discrete action space
        enum_wrapped = EnumActionWrapper(cyborg)

        # 2. FixedFlatWrapper: Fixed-size observation vectors
        flat_wrapped = FixedFlatWrapper(
            enum_wrapped,
            max_params=env_config["max_params"]
        )

        # 3. OpenAIGymWrapper: Gym compatibility
        gym_wrapped = OpenAIGymWrapper(
            env=flat_wrapped,
            agent_name=agent_name
        )

        return gym_wrapped

    # Create vectorized environment
    vec_env = make_vec_env(_make_env, n_envs=n_envs)

    # Log environment info
    logger.info(f"Observation space: {vec_env.observation_space}")
    logger.info(f"Action space: {vec_env.action_space}")

    return vec_env


def _get_default_env_config() -> Dict[str, Any]:
    """Get default environment configuration.

    Returns:
        Default environment config dict
    """
    return {
        "fully_obs": False,
        "randomize_env": False,
        "max_params": {
            "MAX_HOSTS": 5,
            "MAX_PROCESSES": 2,
            "MAX_CONNECTIONS": 2,
            "MAX_VULNERABILITIES": 1,
            "MAX_INTERFACES": 2,
            "MAX_SESSIONS": 3,
            "MAX_USERS": 5,
            "MAX_FILES": 0,
            "MAX_GROUPS": 0,
            "MAX_PATCHES": 0
        }
    }


def get_observation_size(env_config: Dict[str, Any]) -> int:
    """Calculate observation size based on max_params.

    This is useful for determining network architecture sizes.

    Args:
        env_config: Environment configuration dict

    Returns:
        Total observation vector size
    """
    max_params = env_config.get("max_params", _get_default_env_config()["max_params"])

    # Calculate based on FixedFlatWrapper's observation construction
    # This is an approximation - actual size depends on wrapper implementation
    size = (
        max_params["MAX_HOSTS"] * (
            1 +  # Host ID
            max_params["MAX_PROCESSES"] * 4 +  # Processes
            max_params["MAX_CONNECTIONS"] * 3 +  # Connections
            max_params["MAX_VULNERABILITIES"] * 2 +  # Vulnerabilities
            max_params["MAX_INTERFACES"] * 4 +  # Interfaces
            max_params["MAX_SESSIONS"] * 3 +  # Sessions
            max_params["MAX_USERS"] * 2  # Users
        )
    )

    return size
