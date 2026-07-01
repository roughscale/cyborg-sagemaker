#!/usr/bin/env python3
"""
Launch a SageMaker Processing Job to evaluate a trained CybORG RL agent.

Usage:
    # Evaluate using a specific training job's output
    python launch_evaluation.py --algorithm drqn --training-job-name cyborg-rl-drqn-20260101-120000

    # Evaluate using an explicit model S3 URI
    python launch_evaluation.py --algorithm drqn --model-s3-uri s3://bucket/models/drqn/job-name/output/

    # AWS emulation evaluation (requires VPC and Metasploit)
    python launch_evaluation.py --algorithm drqn --training-job-name <name> --environment-mode aws

Environment Variables:
    AWS_REGION      AWS region (default: from Terraform or ap-southeast-2)
    AWS_PROFILE     AWS profile to use (optional)
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ============================================================================
# Constants
# ============================================================================

VALID_ALGORITHMS = ["drqn", "dqn", "ppo", "recurrent_ppo"]

INSTANCE_TYPES = {
    "sim": "ml.m5.large",      # CPU sufficient for simulation
    "aws": "ml.c5.2xlarge",    # More CPU for AWS emulation workload
}

CLOUDWATCH_METRIC_DEFINITIONS = [
    {"Name": "eval_mean_reward",  "Regex": r"eval_mean_reward: ([0-9\.\-]+)"},
    {"Name": "eval_std_reward",   "Regex": r"eval_std_reward: ([0-9\.]+)"},
    {"Name": "eval_min_reward",   "Regex": r"eval_min_reward: ([0-9\.\-]+)"},
    {"Name": "eval_max_reward",   "Regex": r"eval_max_reward: ([0-9\.\-]+)"},
    {"Name": "eval_mean_length",  "Regex": r"eval_mean_length: ([0-9\.]+)"},
    {"Name": "eval_n_episodes",   "Regex": r"eval_n_episodes: ([0-9]+)"},
]


# ============================================================================
# Utilities
# ============================================================================

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


def log_info(msg):
    print(f"{Colors.BLUE}INFO:{Colors.NC} {msg}")


def log_success(msg):
    print(f"{Colors.GREEN}SUCCESS:{Colors.NC} {msg}")


def log_warning(msg):
    print(f"{Colors.YELLOW}WARNING:{Colors.NC} {msg}")


def log_error(msg):
    print(f"{Colors.RED}ERROR:{Colors.NC} {msg}", file=sys.stderr)


def get_terraform_output(output_name: str, terraform_dir: Path) -> Optional[str]:
    """Get a Terraform output value."""
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", output_name],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception as e:
        log_warning(f"Could not get Terraform output '{output_name}': {e}")
        return None


def generate_job_name(algorithm: str, prefix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-eval-{algorithm.replace('_', '-')}-{timestamp}"


# ============================================================================
# Launcher
# ============================================================================

class SageMakerEvaluationLauncher:

    def __init__(self, terraform_dir: Path, aws_region: Optional[str] = None):
        self.terraform_dir = terraform_dir
        self.aws_region = aws_region or os.environ.get('AWS_REGION') or 'ap-southeast-2'

        self.sagemaker = boto3.client('sagemaker', region_name=self.aws_region)
        self.s3 = boto3.client('s3', region_name=self.aws_region)

        self._load_infrastructure_info()

    def _load_infrastructure_info(self):
        log_info("Loading infrastructure information from Terraform...")

        self.bucket = get_terraform_output("artifacts_bucket", self.terraform_dir)
        self.role_arn = get_terraform_output("sagemaker_execution_role_arn", self.terraform_dir)
        self.evaluation_image = get_terraform_output("ecr_evaluation_repository", self.terraform_dir)

        if not (self.bucket and self.role_arn and self.evaluation_image):
            log_error("Could not load required Terraform outputs — run: terraform apply")
            sys.exit(1)

        log_success(f"Loaded infrastructure info (S3: {self.bucket})")

    def get_model_s3_uri(self, training_job_name: str) -> str:
        """Resolve the model output S3 prefix from a completed training job."""
        log_info(f"Resolving model URI for training job: {training_job_name}")
        try:
            response = self.sagemaker.describe_training_job(
                TrainingJobName=training_job_name
            )
            # ModelArtifacts points to model.tar.gz; we want the containing directory
            artifact_uri = response['ModelArtifacts']['S3ModelArtifacts']
            model_dir_uri = artifact_uri.rsplit('/', 1)[0] + '/'
            log_success(f"Model URI: {model_dir_uri}")
            return model_dir_uri
        except ClientError as e:
            log_error(f"Could not describe training job '{training_job_name}': {e}")
            sys.exit(1)

    def check_image_exists(self, image_tag: str):
        """Verify the evaluation Docker image is in ECR."""
        image_uri = f"{self.evaluation_image}:{image_tag}"
        try:
            ecr = boto3.client('ecr', region_name=self.aws_region)
            repo_name = '/'.join(self.evaluation_image.split('/')[1:])  # type: ignore[union-attr]
            ecr.describe_images(
                repositoryName=repo_name,
                imageIds=[{'imageTag': image_tag}],
            )
            log_success(f"Evaluation image found: {image_uri}")
        except ClientError:
            log_error(f"Evaluation image not found in ECR: {image_uri}")
            log_error("Build images with: cd ../terraform && ./scripts/build_images.sh --follow")
            sys.exit(1)

    def launch(
        self,
        job_name: str,
        algorithm: str,
        scenario: str,
        model_s3_uri: str,
        n_eval_episodes: int,
        deterministic: bool,
        environment_mode: str,
        image_tag: str,
        vpc_config: Optional[Dict] = None,
    ) -> str:
        image_uri = f"{self.evaluation_image}:{image_tag}"
        instance_type = INSTANCE_TYPES[environment_mode]

        processing_inputs = [
            {
                'InputName': 'model',
                'S3Input': {
                    'S3Uri': model_s3_uri,
                    'LocalPath': '/opt/ml/processing/model',
                    'S3DataType': 'S3Prefix',
                    'S3InputMode': 'File',
                },
            },
            {
                'InputName': 'config',
                'S3Input': {
                    'S3Uri': f's3://{self.bucket}/configs/algorithms/',
                    'LocalPath': '/opt/ml/processing/config',
                    'S3DataType': 'S3Prefix',
                    'S3InputMode': 'File',
                },
            },
            {
                'InputName': 'scenarios',
                'S3Input': {
                    'S3Uri': f's3://{self.bucket}/configs/environments/scenarios/',
                    'LocalPath': '/opt/ml/processing/scenarios',
                    'S3DataType': 'S3Prefix',
                    'S3InputMode': 'File',
                },
            },
        ]

        processing_outputs = [
            {
                'OutputName': 'results',
                'S3Output': {
                    'S3Uri': f's3://{self.bucket}/evaluation-results/{job_name}/',
                    'LocalPath': '/opt/ml/processing/output',
                    'S3UploadMode': 'EndOfJob',
                },
            },
        ]

        config = {
            'ProcessingJobName': job_name,
            'ProcessingResources': {
                'ClusterConfig': {
                    'InstanceCount': 1,
                    'InstanceType': instance_type,
                    'VolumeSizeInGB': 30,
                },
            },
            'AppSpecification': {
                'ImageUri': image_uri,
            },
            'ProcessingInputs': processing_inputs,
            'ProcessingOutputConfig': {
                'Outputs': processing_outputs,
            },
            'Environment': {
                'ALGORITHM': algorithm,
                'SCENARIO_NAME': scenario,
                'N_EVAL_EPISODES': str(n_eval_episodes),
                'DETERMINISTIC': str(deterministic).lower(),
                'ENVIRONMENT_MODE': environment_mode,
            },
            'RoleArn': self.role_arn,
            'StoppingCondition': {
                'MaxRuntimeInSeconds': 14400,  # 4 hours
            },
            'Tags': [
                {'Key': 'Algorithm', 'Value': algorithm},
                {'Key': 'Project', 'Value': 'CybORG-RL'},
                {'Key': 'JobType', 'Value': 'evaluation'},
                {'Key': 'Mode', 'Value': environment_mode},
            ],
        }

        if vpc_config:
            config['NetworkConfig'] = {
                'VpcConfig': vpc_config,
            }

        log_info(f"Launching evaluation job: {job_name}")
        try:
            response = self.sagemaker.create_processing_job(**config)
            log_success("Evaluation job launched successfully!")
            return response['ProcessingJobArn']
        except ClientError as e:
            log_error(f"Failed to launch evaluation job: {e}")
            sys.exit(1)

    def print_job_info(self, job_name: str, algorithm: str):
        results_uri = f"s3://{self.bucket}/evaluation-results/{job_name}/results.json"
        print("\n" + "=" * 80)
        print(f"Evaluation Job Launched: {job_name}")
        print("=" * 80)
        print(f"\nAlgorithm: {algorithm}")
        print(f"Region:    {self.aws_region}")
        print(f"\nMonitoring:")
        print(f"  Console: https://console.aws.amazon.com/sagemaker/home?region={self.aws_region}#/processing-jobs/{job_name}")
        print(f"  Logs: https://console.aws.amazon.com/cloudwatch/home?region={self.aws_region}#logsV2:log-groups/log-group/$252Faws$252Fsagemaker$252FProcessingJobs")
        print(f"\nCommands:")
        print(f"  Stream logs:")
        print(f"    aws logs tail /aws/sagemaker/ProcessingJobs --follow --filter-pattern {job_name}")
        print(f"\n  Check status:")
        print(f"    aws sagemaker describe-processing-job --processing-job-name {job_name} --query ProcessingJobStatus")
        print(f"\n  Download results (after job completes):")
        print(f"    aws s3 cp {results_uri} ./results.json")
        print("\n" + "=" * 80 + "\n")


# ============================================================================
# Main
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Launch a SageMaker Processing Job to evaluate a CybORG RL agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate from a training job name (recommended)
  python launch_evaluation.py --algorithm drqn --training-job-name cyborg-rl-drqn-20260101-120000

  # Evaluate from an explicit S3 model path
  python launch_evaluation.py --algorithm recurrent_ppo \\
      --model-s3-uri s3://my-bucket/models/recurrent_ppo/job-name/output/ \\
      --n-eval-episodes 50

  # AWS emulation evaluation
  python launch_evaluation.py --algorithm drqn \\
      --training-job-name <name> --environment-mode aws
        """,
    )

    model_group = parser.add_mutually_exclusive_group(required=True)
    model_group.add_argument(
        '--training-job-name',
        help="Name of the completed SageMaker training job (model URI resolved automatically)"
    )
    model_group.add_argument(
        '--model-s3-uri',
        help="Explicit S3 URI of the model directory (containing model.tar.gz)"
    )

    parser.add_argument('--algorithm', required=True, choices=VALID_ALGORITHMS)
    parser.add_argument('--scenario', help="Scenario YAML filename (default: <algorithm>_scenario.yaml)")
    parser.add_argument('--n-eval-episodes', type=int, default=100, help="Number of evaluation episodes (default: 100)")
    parser.add_argument('--deterministic', action='store_true', default=True, help="Use deterministic policy (default: true)")
    parser.add_argument('--no-deterministic', dest='deterministic', action='store_false')
    parser.add_argument('--environment-mode', choices=['sim', 'aws'], default='sim')
    parser.add_argument('--image-tag', default='latest')
    parser.add_argument('--job-name-prefix', help="Job name prefix (default: from Terraform project name)")

    return parser.parse_args()


def main():
    args = parse_args()

    script_dir = Path(__file__).parent
    terraform_dir = script_dir.parent

    scenario = args.scenario or f"{args.algorithm}_scenario.yaml"

    print("\n" + "=" * 80)
    print("CybORG SageMaker Evaluation Job Launcher")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Algorithm:     {args.algorithm}")
    print(f"  Scenario:      {scenario}")
    print(f"  Episodes:      {args.n_eval_episodes}")
    print(f"  Deterministic: {args.deterministic}")
    print(f"  Mode:          {args.environment_mode}")
    print(f"  Image Tag:     {args.image_tag}")
    print()

    try:
        launcher = SageMakerEvaluationLauncher(terraform_dir)
    except NoCredentialsError:
        log_error("AWS credentials not found — configure AWS CLI.")
        sys.exit(1)

    launcher.check_image_exists(args.image_tag)

    # Resolve model S3 URI
    if args.training_job_name:
        model_s3_uri = launcher.get_model_s3_uri(args.training_job_name)
    else:
        model_s3_uri = args.model_s3_uri
        if not model_s3_uri.endswith('/'):
            model_s3_uri += '/'

    # Job name prefix
    job_prefix = args.job_name_prefix
    if not job_prefix:
        project_name = get_terraform_output("project_name", terraform_dir) or "cyborg-rl"
        environment = get_terraform_output("environment", terraform_dir) or "research"
        job_prefix = f"{project_name}-{environment}"

    job_name = generate_job_name(args.algorithm, job_prefix)

    # VPC config for AWS emulation
    vpc_config = None
    if args.environment_mode == 'aws':
        subnets = get_terraform_output("private_subnet_ids", terraform_dir)
        sg = get_terraform_output("security_group_id", terraform_dir)
        if subnets and sg:
            vpc_config = {
                'Subnets': json.loads(subnets) if isinstance(subnets, str) and subnets.startswith('[') else [subnets],
                'SecurityGroupIds': [sg],
            }
        else:
            log_error("AWS mode requires VPC — set enable_aws_emulation=true and run terraform apply")
            sys.exit(1)

    launcher.launch(
        job_name=job_name,
        algorithm=args.algorithm,
        scenario=scenario,
        model_s3_uri=model_s3_uri,
        n_eval_episodes=args.n_eval_episodes,
        deterministic=args.deterministic,
        environment_mode=args.environment_mode,
        image_tag=args.image_tag,
        vpc_config=vpc_config,
    )

    launcher.print_job_info(job_name, args.algorithm)


if __name__ == "__main__":
    main()
