#!/usr/bin/env python3
"""
Launch a SageMaker training job for CybORG RL

This script uses boto3 to create and launch SageMaker training jobs with
proper configuration for different algorithms.

Usage:
    python launch_training.py --algorithm drqn --total-steps 500000
    python launch_training.py --algorithm ppo --total-steps 1000000 --instance-type ml.g4dn.2xlarge

Environment Variables:
    AWS_REGION      AWS region (default: from Terraform or us-east-1)
    AWS_PROFILE     AWS profile to use (optional)
"""

import argparse
import json
import os
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ============================================================================
# Constants
# ============================================================================

VALID_ALGORITHMS = ["drqn", "dqn", "ppo", "recurrent_ppo"]

INSTANCE_TYPES = {
    "ml.g4dn.xlarge": "4 vCPUs, 16GB RAM, 1x T4 GPU - ~$0.23/hr spot",
    "ml.g4dn.2xlarge": "8 vCPUs, 32GB RAM, 1x T4 GPU - ~$0.42/hr spot",
    "ml.g5.xlarge": "4 vCPUs, 16GB RAM, 1x A10G GPU - ~$0.44/hr spot",
}

# CloudWatch metric definitions by algorithm
METRIC_DEFINITIONS = {
    "drqn": [
        {"Name": "episode_reward", "Regex": r"episode_reward: ([0-9\.\-]+)"},
        {"Name": "episode_length", "Regex": r"episode_length: ([0-9]+)"},
        {"Name": "episode_number", "Regex": r"episode_number: ([0-9]+)"},
        {"Name": "total_timesteps", "Regex": r"total_timesteps: ([0-9]+)"},
        {"Name": "exploration_rate", "Regex": r"exploration_rate: ([0-9\.]+)"},
        {"Name": "loss", "Regex": r"loss: ([0-9\.]+)"},
        {"Name": "per_beta", "Regex": r"per_beta: ([0-9\.]+)"},
    ],
    "dqn": [
        {"Name": "episode_reward", "Regex": r"episode_reward: ([0-9\.\-]+)"},
        {"Name": "episode_length", "Regex": r"episode_length: ([0-9]+)"},
        {"Name": "exploration_rate", "Regex": r"exploration_rate: ([0-9\.]+)"},
        {"Name": "loss", "Regex": r"loss: ([0-9\.]+)"},
    ],
    "ppo": [
        {"Name": "episode_reward", "Regex": r"episode_reward: ([0-9\.\-]+)"},
        {"Name": "episode_length", "Regex": r"episode_length: ([0-9]+)"},
        {"Name": "policy_loss", "Regex": r"policy_loss: ([0-9\.\-]+)"},
        {"Name": "value_loss", "Regex": r"value_loss: ([0-9\.\-]+)"},
        {"Name": "entropy_loss", "Regex": r"entropy_loss: ([0-9\.\-]+)"},
        {"Name": "approx_kl", "Regex": r"approx_kl: ([0-9\.]+)"},
        {"Name": "clip_fraction", "Regex": r"clip_fraction: ([0-9\.]+)"},
    ],
    "recurrent_ppo": [
        {"Name": "episode_reward", "Regex": r"episode_reward: ([0-9\.\-]+)"},
        {"Name": "episode_length", "Regex": r"episode_length: ([0-9]+)"},
        {"Name": "policy_loss", "Regex": r"policy_loss: ([0-9\.\-]+)"},
        {"Name": "value_loss", "Regex": r"value_loss: ([0-9\.\-]+)"},
        {"Name": "entropy_loss", "Regex": r"entropy_loss: ([0-9\.\-]+)"},
        {"Name": "approx_kl", "Regex": r"approx_kl: ([0-9\.]+)"},
        {"Name": "clip_fraction", "Regex": r"clip_fraction: ([0-9\.]+)"},
    ],
}


# ============================================================================
# Utility Functions
# ============================================================================

class Colors:
    """ANSI color codes"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


def log_info(msg: str):
    print(f"{Colors.BLUE}INFO:{Colors.NC} {msg}")


def log_success(msg: str):
    print(f"{Colors.GREEN}SUCCESS:{Colors.NC} {msg}")


def log_warning(msg: str):
    print(f"{Colors.YELLOW}WARNING:{Colors.NC} {msg}")


def log_error(msg: str):
    print(f"{Colors.RED}ERROR:{Colors.NC} {msg}", file=sys.stderr)


def get_terraform_output(output_name: str, terraform_dir: Path) -> Optional[str]:
    """Get a Terraform output value"""
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", output_name],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        log_warning(f"Could not get Terraform output '{output_name}': {e}")
        return None


def check_s3_file_exists(s3_client, bucket: str, key: str) -> bool:
    """Check if a file exists in S3"""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


def load_algorithm_config(algorithm: str, configs_dir: Path) -> Dict[str, Any]:
    """Load algorithm configuration from YAML file"""
    config_path = configs_dir / "algorithms" / f"{algorithm}.yaml"

    if not config_path.exists():
        log_warning(f"Algorithm config not found locally: {config_path}")
        return {}

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('hyperparameters', {})
    except Exception as e:
        log_warning(f"Could not load algorithm config: {e}")
        return {}


def generate_job_name(algorithm: str, prefix: str) -> str:
    """Generate a unique job name with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{algorithm}-{timestamp}"


# ============================================================================
# SageMaker Training Job Launcher
# ============================================================================

class SageMakerTrainingLauncher:
    """Launches SageMaker training jobs for CybORG RL"""

    def __init__(self, terraform_dir: Path, aws_region: Optional[str] = None):
        self.terraform_dir = terraform_dir
        self.aws_region = aws_region or os.environ.get('AWS_REGION') or 'ap-southeast-2'

        # Initialize boto3 clients
        self.sagemaker = boto3.client('sagemaker', region_name=self.aws_region)
        self.s3 = boto3.client('s3', region_name=self.aws_region)
        self.sts = boto3.client('sts', region_name=self.aws_region)

        # Get infrastructure info from Terraform
        self._load_infrastructure_info()

    def _load_infrastructure_info(self):
        """Load infrastructure information from Terraform outputs"""
        log_info("Loading infrastructure information from Terraform...")

        self.bucket = get_terraform_output("artifacts_bucket", self.terraform_dir)
        self.role_arn = get_terraform_output("sagemaker_execution_role_arn", self.terraform_dir)
        self.training_image = get_terraform_output("ecr_training_repository", self.terraform_dir)

        if not all([self.bucket, self.role_arn, self.training_image]):
            log_error("Could not load required Terraform outputs")
            log_error("Please ensure infrastructure is deployed: terraform apply")
            sys.exit(1)

        # Get account ID
        try:
            self.account_id = self.sts.get_caller_identity()['Account']
        except Exception as e:
            log_error(f"Could not get AWS account ID: {e}")
            sys.exit(1)

        log_success(f"Loaded infrastructure info (S3: {self.bucket}, Region: {self.aws_region})")

    def check_prerequisites(self, algorithm: str, scenario: str, image_tag: str):
        """Check that all prerequisites are met before launching job"""
        log_info("Checking prerequisites...")

        # Check Docker image exists in ECR
        image_uri = f"{self.training_image}:{image_tag}"
        try:
            ecr = boto3.client('ecr', region_name=self.aws_region)
            # Extract repo name from ECR URL: account.dkr.ecr.region.amazonaws.com/repo/name
            repo_name = '/'.join(self.training_image.split('/')[1:])
            ecr.describe_images(
                repositoryName=repo_name,
                imageIds=[{'imageTag': image_tag}]
            )
            log_success(f"Docker image found: {image_uri}")
        except ClientError:
            log_error(f"Docker image not found in ECR: {image_uri}")
            log_error("Please build and push Docker images: cd ../docker && ./build.sh --push")
            sys.exit(1)

        # Check algorithm config exists in S3
        config_key = f"configs/algorithms/{algorithm}.yaml"
        if not check_s3_file_exists(self.s3, self.bucket, config_key):
            log_error(f"Algorithm config not found in S3: s3://{self.bucket}/{config_key}")
            log_error("Please upload configs: ./scripts/upload_configs.sh")
            sys.exit(1)

        # Check scenario exists in S3
        scenario_key = f"configs/environments/scenarios/{scenario}"
        if not check_s3_file_exists(self.s3, self.bucket, scenario_key):
            log_error(f"Scenario not found in S3: s3://{self.bucket}/{scenario_key}")
            log_error("Please upload configs: ./scripts/upload_configs.sh")
            sys.exit(1)

        log_success("All prerequisites met")

    def build_training_job_config(
        self,
        job_name: str,
        algorithm: str,
        total_steps: int,
        scenario: str,
        instance_type: str,
        image_tag: str,
        enable_spot: bool,
        seed: Optional[int],
        hyperparameters: Dict[str, str],
        environment_mode: str,
        algorithm_config: Dict[str, Any],
        vpc_config: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """Build the SageMaker training job configuration"""

        image_uri = f"{self.training_image}:{image_tag}"

        # Build hyperparameters (all must be strings)
        # Note: scenario_name and environment_mode are passed as environment variables
        # to keep them out of the hyperparameters display (16 param console limit)
        job_hyperparameters = {
            "algorithm": algorithm,
            "total_steps": str(total_steps),
        }

        if seed is not None:
            job_hyperparameters["seed"] = str(seed)

        # Add algorithm hyperparameters from config (convert all to strings)
        for key, value in algorithm_config.items():
            if isinstance(value, bool):
                job_hyperparameters[key] = str(value).lower()
            elif value is not None:
                job_hyperparameters[key] = str(value)

        # Add custom hyperparameters (these override config defaults)
        job_hyperparameters.update(hyperparameters)

        # Build environment variables for job metadata
        environment_variables = {
            "SCENARIO_NAME": scenario,
            "ENVIRONMENT_MODE": environment_mode,
        }

        # Build training job configuration
        config = {
            "TrainingJobName": job_name,
            "RoleArn": self.role_arn,
            "AlgorithmSpecification": {
                "TrainingImage": image_uri,
                "TrainingInputMode": "File",
                "MetricDefinitions": METRIC_DEFINITIONS[algorithm],
            },
            "Environment": environment_variables,
            "ResourceConfig": {
                "InstanceType": instance_type,
                "InstanceCount": 1,
                "VolumeSizeInGB": 30,
            },
            "StoppingCondition": {
                "MaxRuntimeInSeconds": 86400,  # 24 hours
            },
            "InputDataConfig": [
                {
                    "ChannelName": "config",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            "S3Uri": f"s3://{self.bucket}/configs/algorithms/",
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    },
                },
                {
                    "ChannelName": "scenarios",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            "S3Uri": f"s3://{self.bucket}/configs/environments/scenarios/",
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    },
                },
            ],
            "OutputDataConfig": {
                "S3OutputPath": f"s3://{self.bucket}/models/{algorithm}/",
            },
            "HyperParameters": job_hyperparameters,
            "CheckpointConfig": {
                "S3Uri": f"s3://{self.bucket}/checkpoints/{job_name}/",
            },
            "Tags": [
                {"Key": "Algorithm", "Value": algorithm},
                {"Key": "Project", "Value": "CybORG-RL"},
                {"Key": "ManagedBy", "Value": "PythonScript"},
            ],
        }

        # Add spot training if enabled
        if enable_spot:
            config["EnableManagedSpotTraining"] = True
            config["StoppingCondition"]["MaxWaitTimeInSeconds"] = 172800  # 48 hours

        # Add VPC config if provided
        if vpc_config:
            config["VpcConfig"] = vpc_config

        return config

    def launch_training_job(self, config: Dict[str, Any]) -> str:
        """Launch the SageMaker training job"""
        job_name = config["TrainingJobName"]

        log_info(f"Launching SageMaker training job: {job_name}")

        try:
            response = self.sagemaker.create_training_job(**config)
            log_success(f"Training job launched successfully!")
            return response["TrainingJobArn"]
        except ClientError as e:
            log_error(f"Failed to launch training job: {e}")
            sys.exit(1)

    def print_job_info(self, job_name: str, algorithm: str):
        """Print job information and monitoring URLs"""
        print("\n" + "="*80)
        print(f"Training Job Launched: {job_name}")
        print("="*80)
        print(f"\nAlgorithm: {algorithm}")
        print(f"Region: {self.aws_region}")
        print(f"\nMonitoring URLs:")
        print(f"  Job Console: https://console.aws.amazon.com/sagemaker/home?region={self.aws_region}#/jobs/{job_name}")
        print(f"  CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region={self.aws_region}#logsV2:log-groups/log-group/$252Faws$252Fsagemaker$252FTrainingJobs")
        print(f"\nCommands:")
        print(f"  Stream logs:")
        print(f"    aws logs tail /aws/sagemaker/TrainingJobs --follow --filter-pattern {job_name}")
        print(f"\n  Check status:")
        print(f"    aws sagemaker describe-training-job --training-job-name {job_name} --query 'TrainingJobStatus'")
        print(f"\n  Download model:")
        print(f"    aws s3 sync s3://{self.bucket}/models/{algorithm}/{job_name}/output/ ./models/")
        print("\n" + "="*80 + "\n")


# ============================================================================
# Main
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Launch a SageMaker training job for CybORG RL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_training.py --algorithm drqn --total-steps 500000
  python launch_training.py --algorithm ppo --total-steps 1000000 --instance-type ml.g4dn.2xlarge
  python launch_training.py --algorithm drqn --total-steps 200000 --no-spot --seed 42

Environment Variables:
  AWS_REGION      AWS region (default: from Terraform or us-east-1)
  AWS_PROFILE     AWS profile to use (optional)
        """
    )

    parser.add_argument(
        "--algorithm",
        required=True,
        choices=VALID_ALGORITHMS,
        help="Algorithm to train"
    )

    parser.add_argument(
        "--total-steps",
        type=int,
        required=True,
        help="Total training steps"
    )

    parser.add_argument(
        "--scenario",
        help="Scenario YAML filename (default: <algorithm>_scenario.yaml)"
    )

    parser.add_argument(
        "--instance-type",
        default="ml.g4dn.xlarge",
        choices=list(INSTANCE_TYPES.keys()),
        help="SageMaker instance type (default: ml.g4dn.xlarge)"
    )

    parser.add_argument(
        "--image-tag",
        default="latest",
        help="Docker image tag (default: latest)"
    )

    parser.add_argument(
        "--spot/--no-spot",
        dest="enable_spot",
        default=True,
        help="Enable spot training (default: enabled)"
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for training (default: random)"
    )

    parser.add_argument(
        "--environment-mode",
        choices=["sim", "aws"],
        default="sim",
        help="Environment mode (default: sim)"
    )

    parser.add_argument(
        "--job-name-prefix",
        help="Job name prefix (default: from Terraform project name)"
    )

    parser.add_argument(
        "--hyperparameter",
        action="append",
        metavar="KEY=VALUE",
        help="Additional hyperparameters (can be used multiple times)"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Get script directory
    script_dir = Path(__file__).parent
    terraform_dir = script_dir.parent
    configs_dir = terraform_dir.parent / "configs"

    # Set scenario default
    scenario = args.scenario or f"{args.algorithm}_scenario.yaml"

    # Load algorithm configuration
    algorithm_config = load_algorithm_config(args.algorithm, configs_dir)

    # Parse custom hyperparameters
    hyperparameters = {}
    if args.hyperparameter:
        for hp in args.hyperparameter:
            if '=' not in hp:
                log_error(f"Invalid hyperparameter format: {hp} (expected KEY=VALUE)")
                sys.exit(1)
            key, value = hp.split('=', 1)
            hyperparameters[key] = value

    # Print configuration
    print("\n" + "="*80)
    print("CybORG SageMaker Training Job Launcher")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Algorithm:      {args.algorithm}")
    print(f"  Total Steps:    {args.total_steps:,}")
    print(f"  Scenario:       {scenario}")
    print(f"  Instance Type:  {args.instance_type} ({INSTANCE_TYPES[args.instance_type]})")
    print(f"  Image Tag:      {args.image_tag}")
    print(f"  Spot Training:  {'Enabled' if args.enable_spot else 'Disabled'}")
    print(f"  Seed:           {args.seed if args.seed else 'Random'}")
    print(f"  Environment:    {args.environment_mode}")
    if hyperparameters:
        print(f"  Custom Params:  {hyperparameters}")
    print()

    # Initialize launcher
    try:
        launcher = SageMakerTrainingLauncher(terraform_dir)
    except NoCredentialsError:
        log_error("AWS credentials not found. Please configure AWS CLI.")
        sys.exit(1)

    # Check prerequisites
    launcher.check_prerequisites(args.algorithm, scenario, args.image_tag)

    # Get job name prefix
    job_prefix = args.job_name_prefix
    if not job_prefix:
        project_name = get_terraform_output("project_name", terraform_dir) or "cyborg-rl"
        environment = get_terraform_output("environment", terraform_dir) or "research"
        job_prefix = f"{project_name}-{environment}"

    # Generate job name
    job_name = generate_job_name(args.algorithm, job_prefix)

    # Get VPC config if AWS emulation mode
    vpc_config = None
    if args.environment_mode == "aws":
        subnets = get_terraform_output("private_subnet_ids", terraform_dir)
        security_group = get_terraform_output("security_group_id", terraform_dir)
        if subnets and security_group:
            vpc_config = {
                "Subnets": json.loads(subnets) if isinstance(subnets, str) else subnets,
                "SecurityGroupIds": [security_group]
            }
        else:
            log_error("AWS emulation mode requires VPC configuration")
            log_error("Set enable_aws_emulation = true in terraform.tfvars and run terraform apply")
            sys.exit(1)

    # Build training job config
    config = launcher.build_training_job_config(
        job_name=job_name,
        algorithm=args.algorithm,
        total_steps=args.total_steps,
        scenario=scenario,
        instance_type=args.instance_type,
        image_tag=args.image_tag,
        enable_spot=args.enable_spot,
        seed=args.seed,
        hyperparameters=hyperparameters,
        environment_mode=args.environment_mode,
        algorithm_config=algorithm_config,
        vpc_config=vpc_config,
    )

    # Launch job
    launcher.launch_training_job(config)

    # Print job info
    launcher.print_job_info(job_name, args.algorithm)


if __name__ == "__main__":
    main()
